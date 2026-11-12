package main

import (
	"fmt"
	"log"
	"os"
	"strings"
)

func generateMethods(functions []TLType, classes map[string]*TLClass) {
	var sb strings.Builder
	sb.WriteString(header)
	sb.WriteString("package gotdbot\n\n")

	for _, fn := range functions {
		methodName := toCamelCase(fn.Name)

		if methodName == "Close" {
			continue
		}
		structName := toCamelCase(fn.Name)

		hasOptional := false
		for _, p := range fn.Params {
			if p.IsOptional || p.Type == "Bool" {
				hasOptional = true
				break
			}
		}

		optsStructName := methodName + "Opts"

		isOk := fn.ResultType == "ok" || fn.ResultType == "Ok"
		resultType := toCamelCase(fn.ResultType)
		if isOk {
			resultType = "Ok"
		}

		retTypeStr := "*" + resultType
		if _, ok := classes[fn.ResultType]; ok {
			retTypeStr = toCamelCase(fn.ResultType)
		}

		fmt.Fprintf(&sb, "// %s %s\n", methodName, formatDesc(fn.Description))
		fmt.Fprintf(&sb, "func (c *Client) %s(", methodName)

		// Args
		var args []string
		for _, p := range fn.Params {
			if p.IsOptional || p.Type == "Bool" {
				continue
			}
			goType := toGoType(p.Type, classes)

			fieldName := toCamelCase(p.Name)
			argName := strings.ToLower(fieldName[:1]) + fieldName[1:]
			if argName == "type" {
				argName = "typeField"
			}
			if argName == "func" {
				argName = "funcArg"
			}

			args = append(args, fmt.Sprintf("%s %s", argName, goType))
		}

		if hasOptional {
			args = append(args, fmt.Sprintf("opts *%s", optsStructName))
		}

		fmt.Fprintf(&sb, "%s", strings.Join(args, ", "))

		if isOk {
			fmt.Fprintf(&sb, ") error {\n")
		} else {
			fmt.Fprintf(&sb, ") (%s, error) {\n", retTypeStr)
		}

		fmt.Fprintf(&sb, "\treq := &%s{\n", structName)
		for _, p := range fn.Params {
			if p.IsOptional || p.Type == "Bool" {
				continue
			}
			fieldName := toCamelCase(p.Name)
			argName := strings.ToLower(fieldName[:1]) + fieldName[1:]
			if argName == "type" {
				argName = "typeField"
			}
			if argName == "func" {
				argName = "funcArg"
			}

			fmt.Fprintf(&sb, "\t\t%s: %s,\n", fieldName, argName)
		}
		sb.WriteString("\t}\n")

		if hasOptional {
			sb.WriteString("\tif opts != nil {\n")
			for _, p := range fn.Params {
				if !p.IsOptional && p.Type != "Bool" {
					continue
				}
				fieldName := toCamelCase(p.Name)
				fmt.Fprintf(&sb, "\t\treq.%s = opts.%s\n", fieldName, fieldName)
			}
			sb.WriteString("\t}\n")
		}

		if isOk {
			sb.WriteString("\t_, err := c.Send(req)\n")
			sb.WriteString("\treturn err\n")
		} else {
			sb.WriteString("\tresp, err := c.Send(req)\n")
			sb.WriteString("\tif err != nil {\n\t\treturn nil, err\n\t}\n")

			if methodName == "SendMessage" || methodName == "SendEphemeralMessage" {
				sb.WriteString("\treturn c.waitMessage(resp.(*Message))\n")
			} else if methodName == "SendMessageAlbum" {
				sb.WriteString("\treturn c.waitMessages(resp.(*Messages))\n")
			} else {
				fmt.Fprintf(&sb, "\treturn resp.(%s), nil\n", retTypeStr)
			}
		}
		sb.WriteString("}\n\n")
	}

	if err := os.WriteFile("gen_methods.go", []byte(sb.String()), 0644); err != nil {
		log.Fatal(err)
	}
}
