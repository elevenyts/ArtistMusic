package main

import (
	"fmt"
	"log"
	"os"
	"strings"
)

func generateEvents(types []TLType, classes map[string]*TLClass) {
	var updates []TLType
	for _, t := range types {
		if strings.HasPrefix(t.Name, "update") {
			updates = append(updates, t)
		}
	}
	sortTLTypesByName(updates)

	var fsb strings.Builder
	fsb.WriteString(header)
	fsb.WriteString("package filters\n\n")
	fsb.WriteString("import \"github.com/Kanha/Meow\"\n\n")
	fsb.WriteString("type (\n")
	for _, t := range updates {
		structName := toCamelCase(t.Name)
		fmt.Fprintf(&fsb, "\t// %s %s\n", structName, formatDesc(t.Description))
		fmt.Fprintf(&fsb, "\t%s func(u *gotdbot.%s) bool\n", structName, structName)
	}
	fsb.WriteString("\t// Message is a filter for Message type\n")
	fsb.WriteString("\tMessage func(msg *gotdbot.Message) bool\n")
	fsb.WriteString(")\n")

	if err := os.MkdirAll("filters", 0755); err != nil {
		log.Fatal(err)
	}
	if err := os.WriteFile("filters/gen_filters.go", []byte(fsb.String()), 0644); err != nil {
		log.Fatal(err)
	}

	var sb strings.Builder
	sb.WriteString(header)
	sb.WriteString("package gotdbot\n\n")

	// Handler types
	for _, t := range updates {
		structName := toCamelCase(t.Name)
		name := structName
		unexportedHandlerName := strings.ToLower(name[:1]) + name[1:] + "Handler"

		handlerFunc := "func(client *Client, update *" + structName + ") error"
		filterType := "func(u *" + structName + ") bool"

		fmt.Fprintf(&sb, "// %s handles %s updates\n", unexportedHandlerName, structName)
		fmt.Fprintf(&sb, "type %s struct {\n", unexportedHandlerName)
		sb.WriteString("\tfilter   " + filterType + "\n")
		sb.WriteString("\tresponse " + handlerFunc + "\n")
		sb.WriteString("}\n\n")

		fmt.Fprintf(&sb, "func (h *%s) CheckUpdate(client *Client, update TlObject) bool {\n", unexportedHandlerName)
		fmt.Fprintf(&sb, "\tu, ok := update.(*%s)\n", structName)
		sb.WriteString("\tif !ok {\n\t\treturn false\n\t}\n")
		sb.WriteString("\tif h.filter != nil && !h.filter(u) {\n\t\treturn false\n\t}\n")
		sb.WriteString("\treturn true\n")
		sb.WriteString("}\n\n")

		fmt.Fprintf(&sb, "func (h *%s) HandleUpdate(client *Client, update TlObject) error {\n", unexportedHandlerName)
		fmt.Fprintf(&sb, "\treturn h.response(client, update.(*%s))\n", structName)
		sb.WriteString("}\n\n")

		fmt.Fprintf(&sb, "// On%s registers a handler for %s updates with default group (0)\n", name, structName)
		fmt.Fprintf(&sb, "func (c *Client) On%s(handler %s, filter %s) {\n", name, handlerFunc, filterType)
		fmt.Fprintf(&sb, "\tc.Add%sHandlerGroup(handler, filter, 0)\n", name)
		sb.WriteString("}\n\n")

		fmt.Fprintf(&sb, "// Add%sHandlerGroup registers a handler for %s updates with a specific group\n", name, structName)
		fmt.Fprintf(&sb, "func (c *Client) Add%sHandlerGroup(handler %s, filter %s, group int) {\n", name, handlerFunc, filterType)
		fmt.Fprintf(&sb, "\tc.AddHandlerGroup(&%s{filter: filter, response: handler}, group)\n", unexportedHandlerName)
		sb.WriteString("}\n\n")
	}

	msgHandlerFunc := "func(client *Client, message *Message) error"
	msgFilterType := "func(msg *Message) bool"

	sb.WriteString("// MessageHandler handles Message updates\n")
	sb.WriteString(fmt.Sprintf("type MessageHandler struct {\n\tOptions  MatchingOptions\n\tFilter   %s\n\tResponse %s\n}\n\n", msgFilterType, msgHandlerFunc))

	sb.WriteString("// NewMessageHandler creates a new MessageHandler\n")
	sb.WriteString(fmt.Sprintf("func NewMessageHandler(response %s, filter %s) *MessageHandler {\n", msgHandlerFunc, msgFilterType))
	sb.WriteString("\treturn &MessageHandler{\n\t\tOptions:  DefaultMatchingOptions(),\n\t\tFilter:   filter,\n\t\tResponse: response,\n\t}\n}\n\n")

	sb.WriteString("func (h *MessageHandler) CheckUpdate(client *Client, update TlObject) bool {\n")
	sb.WriteString("\tu, ok := update.(*UpdateNewMessage)\n")
	sb.WriteString("\tif !ok || u.Message == nil {\n\t\treturn false\n\t}\n")
	sb.WriteString("\tif !h.Options.check(u.Message) {\n\t\treturn false\n\t}\n")
	sb.WriteString("\tif h.Filter != nil && !h.Filter(u.Message) {\n\t\treturn false\n\t}\n")
	sb.WriteString("\treturn true\n}\n\n")

	sb.WriteString("func (h *MessageHandler) HandleUpdate(client *Client, update TlObject) error {\n")
	sb.WriteString("\treturn h.Response(client, update.(*UpdateNewMessage).Message)\n}\n\n")

	sb.WriteString("func (h *MessageHandler) SetOptions(options MatchingOptions) *MessageHandler {\n")
	sb.WriteString("\th.Options = options\n\treturn h\n}\n\n")

	sb.WriteString("// OnMessage registers a handler for NewMessage updates with default group (0)\n")
	sb.WriteString(fmt.Sprintf("func (c *Client) OnMessage(handler %s, filter %s) *MessageHandler {\n", msgHandlerFunc, msgFilterType))
	sb.WriteString("\treturn c.OnMessageGroup(handler, filter, 0)\n}\n\n")

	sb.WriteString("// OnMessageGroup registers a handler for NewMessage updates with a specific group\n")
	sb.WriteString(fmt.Sprintf("func (c *Client) OnMessageGroup(handler %s, filter %s, group int) *MessageHandler {\n", msgHandlerFunc, msgFilterType))
	sb.WriteString("\th := NewMessageHandler(handler, filter)\n")
	sb.WriteString("\tc.AddHandlerGroup(h, group)\n")
	sb.WriteString("\treturn h\n}\n\n")

	sb.WriteString("// NewUpdateNewMessageFilter creates an UpdateNewMessage filter from a Message filter\n")
	sb.WriteString("func NewUpdateNewMessageFilter(filter func(msg *Message) bool) func(u *UpdateNewMessage) bool {\n")
	sb.WriteString("\treturn func(u *UpdateNewMessage) bool {\n\t\tif u.Message == nil {\n\t\t\treturn false\n\t\t}\n\t\treturn filter(u.Message)\n\t}\n}\n")

	if err := os.WriteFile("gen_events.go", []byte(sb.String()), 0644); err != nil {
		log.Fatal(err)
	}
}
