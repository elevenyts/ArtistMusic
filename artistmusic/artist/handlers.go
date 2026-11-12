package gotdbot

import (
	"sort"
	"strings"
)

// Handler is the interface for all update handlers.
type Handler interface {
	// CheckUpdate checks if the update should be handled by this handler.
	CheckUpdate(client *Client, update TlObject) bool
	// HandleUpdate handles the update.
	HandleUpdate(client *Client, update TlObject) error
}

// MatchingOptions contains options for matching updates.
type MatchingOptions struct {
	AllowOutgoing bool
	AllowIncoming bool
	AllowEdited   bool
	AllowChannel  bool
	AllowGroup    bool
	AllowPrivate  bool
}

// DefaultMatchingOptions returns the default matching options.
func DefaultMatchingOptions() MatchingOptions {
	return MatchingOptions{
		AllowIncoming: true,
		AllowEdited:   true,
		AllowChannel:  true,
		AllowGroup:    true,
		AllowPrivate:  true,
	}
}

// checkMessageOptions checks if the message matches the matching options.
func (o MatchingOptions) check(msg *Message) bool {
	if msg == nil {
		return false
	}

	if msg.IsOutgoing && !o.AllowOutgoing {
		return false
	}
	if !msg.IsOutgoing && !o.AllowIncoming {
		return false
	}
	if msg.EditDate > 0 && !o.AllowEdited {
		return false
	}

	if msg.IsChannel() && !o.AllowChannel {
		return false
	}
	if msg.IsGroup() && !o.AllowGroup {
		return false
	}
	if msg.IsPrivate() && !o.AllowPrivate {
		return false
	}

	return true
}

// CommandHandler handles bot commands.
type CommandHandler struct {
	Options  MatchingOptions
	Triggers []rune
	Command  string
	Handler  func(client *Client, message *Message) error
	Filter   func(msg *Message) bool
}

// NewCommandHandler creates a new CommandHandler.
func NewCommandHandler(command string, handler func(client *Client, message *Message) error) *CommandHandler {
	return &CommandHandler{
		Options:  DefaultMatchingOptions(),
		Triggers: []rune{'/'},
		Command:  strings.ToLower(command),
		Handler:  handler,
	}
}

// CheckUpdate checks if the update is a command that matches this handler.
func (h *CommandHandler) CheckUpdate(client *Client, update TlObject) bool {
	msg, msgOk := getMessageFromUpdate(update)
	if !msgOk || !h.Options.check(msg) {
		return false
	}

	u, ok := update.(*UpdateNewMessage)
	if !ok || u.Message == nil || u.Message.Content == nil {
		return false
	}

	msg = u.Message
	if h.Filter != nil && !h.Filter(msg) {
		return false
	}

	text := msg.GetText()

	if text == "" {
		return false
	}

	for _, trigger := range h.Triggers {
		prefix := string(trigger)
		if !strings.HasPrefix(text, prefix) {
			continue
		}

		parts := strings.Fields(text)
		if len(parts) == 0 {
			continue
		}

		cmdPart := parts[0][len(prefix):]

		var (
			cmdName      string
			mentionedBot string
		)

		if i := strings.Index(cmdPart, "@"); i != -1 {
			cmdName = cmdPart[:i]
			mentionedBot = cmdPart[i+1:]
		} else {
			cmdName = cmdPart
		}

		if strings.ToLower(cmdName) != h.Command {
			continue
		}

		if mentionedBot != "" {
			if client.Me == nil {
				return false
			}
			botUsername := ""
			if client.Me.Usernames != nil && len(client.Me.Usernames.ActiveUsernames) > 0 {
				botUsername = strings.ToLower(client.Me.Usernames.ActiveUsernames[0])
			}

			if botUsername == "" {
				return false
			}
			if strings.ToLower(mentionedBot) != botUsername {
				return false
			}
		}

		return true
	}

	return false
}

// HandleUpdate handles the command update.
func (h *CommandHandler) HandleUpdate(client *Client, update TlObject) error {
	u := update.(*UpdateNewMessage)
	return h.Handler(client, u.Message)
}

func getMessageFromUpdate(update TlObject) (*Message, bool) {
	switch u := update.(type) {
	case *UpdateNewMessage:
		return u.Message, true
	case *UpdateNewBusinessMessage:
		if u.Message != nil {
			return u.Message.Message, true
		}
	case *UpdateBusinessMessageEdited:
		if u.Message != nil {
			return u.Message.Message, true
		}
	}
	return nil, false
}

func getChatIDFromUpdate(update TlObject) int64 {
	if msg, ok := getMessageFromUpdate(update); ok && msg != nil {
		return msg.ChatId
	}
	switch u := update.(type) {
	case *UpdateNewCallbackQuery:
		return u.ChatId
	case *UpdateMessageEdited:
		return u.ChatId
	case *UpdateMessageContent:
		return u.ChatId
	case *UpdateMessageEphemeralContent:
		return u.ChatId
	case *UpdateMessageLiveLocationViewed:
		return u.ChatId
	case *UpdateMessageInteractionInfo:
		return u.ChatId
	case *UpdateMessageSendSucceeded:
		if u.Message != nil {
			return u.Message.ChatId
		}
	case *UpdateMessageSendFailed:
		if u.Message != nil {
			return u.Message.ChatId
		}
	}
	return 0
}

// AddHandler adds a handler with the default group (0).
func (c *Client) AddHandler(handler Handler) {
	c.AddHandlerGroup(handler, 0)
}

// AddHandlerGroup adds a handler with a specific group.
func (c *Client) AddHandlerGroup(handler Handler, group int) {
	c.hMu.Lock()
	defer c.hMu.Unlock()

	oldData := c.handlers.Load()
	newMap := make(map[int][]Handler, len(oldData.handlers))
	for k, v := range oldData.handlers {
		newMap[k] = v
	}

	handlers := make([]Handler, len(newMap[group]))
	copy(handlers, newMap[group])
	handlers = append(handlers, handler)

	newMap[group] = handlers

	groups := make([]int, 0, len(newMap))
	for k := range newMap {
		groups = append(groups, k)
	}
	sort.Ints(groups)

	c.handlers.Store(&handlersData{
		handlers: newMap,
		groups:   groups,
	})
}

// OnCommand registers a new command handler with the default group (0).
func (c *Client) OnCommand(command string, handler func(client *Client, message *Message) error) *CommandHandler {
	return c.OnCommandGroup(command, handler, 0)
}

// OnCommandGroup registers a new command handler with a specific group.
func (c *Client) OnCommandGroup(command string, handler func(client *Client, message *Message) error, group int) *CommandHandler {
	ch := NewCommandHandler(command, handler)
	c.AddHandlerGroup(ch, group)
	return ch
}
