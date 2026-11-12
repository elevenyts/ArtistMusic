package main

import (
	"fmt"
	"log"
	"os"
	"strings"
)

func generateHelpers(types []TLType, functions []TLType, classes map[string]*TLClass) []string {
	var sb strings.Builder
	sb.WriteString(header)
	sb.WriteString("package gotdbot\n\n")

	generatedFiles := []string{"gen_helpers.go"}

	allowedTypes := map[string]bool{
		"File":       true,
		"RemoteFile": true,
		"Message":    true,
		"Chat":       true,
		"User":       true,
	}

	manualMethods := map[string]bool{
		"Message.EditText":    true,
		"Message.EditCaption": true,
		"Message.GetLink":     true,
	}

	generatedMethods := make(map[string]bool)

	for _, t := range types {
		if !allowedTypes[toCamelCase(t.Name)] {
			continue
		}

		typeFields := make(map[string]TLParam)
		for _, p := range t.Params {
			typeFields[p.Name] = p
		}

		for _, fn := range functions {
			matches := make(map[string]string)

			matchedCount := 0

			for _, param := range fn.Params {
				if param.IsOptional || param.Type == "Bool" {
					continue
				}

				if field, ok := typeFields[param.Name]; ok {
					if field.Type == param.Type {
						matches[param.Name] = toCamelCase(field.Name)
						matchedCount++
						continue
					}
				}

				typeNameSnake := toSnakeCase(t.Name)
				if param.Name == typeNameSnake+"_id" {
					if field, ok := typeFields["id"]; ok {
						if field.Type == param.Type {
							matches[param.Name] = "Id"
							matchedCount++
							continue
						}
					}
				}

				if param.Name == "id" {
					if field, ok := typeFields["id"]; ok {
						if field.Type == param.Type {
							matches[param.Name] = "Id"
							matchedCount++
							continue
						}
					}
				}
			}

			if matchedCount == 0 {
				continue
			}

			if _, hasId := typeFields["id"]; hasId {
				usedId := false
				for _, matchVal := range matches {
					if matchVal == "Id" {
						usedId = true
						break
					}
				}
				if !usedId {
					continue
				}
			}

			methodName := toCamelCase(fn.Name)
			helperName := methodName

			typeCamel := toCamelCase(t.Name)
			if strings.Contains(methodName, typeCamel) {
				helperName = strings.Replace(methodName, typeCamel, "", 1)
			}

			if helperName == "" {
				helperName = methodName
			}

			fullHelperName := toCamelCase(t.Name) + "." + helperName

			if manualMethods[fullHelperName] || generatedMethods[fullHelperName] {
				continue
			}

			generatedMethods[fullHelperName] = true
			generateHelperMethod(&sb, t, fn, matches, helperName, classes)
		}
	}

	if err := os.WriteFile("gen_helpers.go", []byte(sb.String()), 0644); err != nil {
		log.Fatal(err)
	}

	return generatedFiles
}

func generateHelperMethod(sb *strings.Builder, t TLType, fn TLType, matches map[string]string, helperName string, classes map[string]*TLClass) {
	clientMethodName := toCamelCase(fn.Name)
	structName := toCamelCase(t.Name)

	for _, p := range t.Params {
		if toCamelCase(p.Name) == helperName {
			helperName = helperName + "Action"
		}
	}

	var funcArgs []string
	var callArgs []string

	for _, p := range fn.Params {
		if p.IsOptional || p.Type == "Bool" {
			continue
		}

		if receiverField, ok := matches[p.Name]; ok {
			callArgs = append(callArgs, fmt.Sprintf("%s.%s", strings.ToLower(structName[:1]), receiverField))
		} else {
			goType := toGoType(p.Type, classes)
			fieldName := toCamelCase(p.Name)
			argName := strings.ToLower(fieldName[:1]) + fieldName[1:]
			if argName == "type" {
				argName = "typeField"
			}
			if argName == "func" {
				argName = "funcArg"
			}
			funcArgs = append(funcArgs, fmt.Sprintf("%s %s", argName, goType))
			callArgs = append(callArgs, argName)
		}
	}

	hasOptional := false
	for _, p := range fn.Params {
		if p.IsOptional || p.Type == "Bool" {
			hasOptional = true
			break
		}
	}

	optsStructName := clientMethodName + "Opts"
	if hasOptional {
		funcArgs = append(funcArgs, fmt.Sprintf("opts *%s", optsStructName))
		callArgs = append(callArgs, "opts")
	}

	isOk := fn.ResultType == "ok" || fn.ResultType == "Ok"
	resultType := toCamelCase(fn.ResultType)
	if isOk {
		resultType = "Ok"
	}
	retTypeStr := "*" + resultType
	if _, ok := classes[fn.ResultType]; ok {
		retTypeStr = toCamelCase(fn.ResultType)
	}

	receiverVar := strings.ToLower(structName[:1])

	fmt.Fprintf(sb, "// %s %s\n", helperName, formatDesc(fn.Description))
	fmt.Fprintf(sb, "// It is a helper method for Client.%s\n", clientMethodName)

	if isOk {
		fmt.Fprintf(sb, "func (%s *%s) %s(client *Client, %s) error {\n",
			receiverVar, structName, helperName, strings.Join(funcArgs, ", "))
	} else {
		fmt.Fprintf(sb, "func (%s *%s) %s(client *Client, %s) (%s, error) {\n",
			receiverVar, structName, helperName, strings.Join(funcArgs, ", "), retTypeStr)
	}

	fmt.Fprintf(sb, "\treturn client.%s(%s)\n", clientMethodName, strings.Join(callArgs, ", "))
	sb.WriteString("}\n\n")
}

func toSnakeCase(s string) string {
	var res strings.Builder
	for i, r := range s {
		if i > 0 && r >= 'A' && r <= 'Z' {
			res.WriteRune('_')
		}
		res.WriteRune(r)
	}
	return strings.ToLower(res.String())
}
