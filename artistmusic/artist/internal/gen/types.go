package main

import (
	"fmt"
	"log"
	"os"
	"regexp"
	"sort"
	"strings"
	"unicode"
)

func generateClasses(classes map[string]*TLClass) {
	var sb strings.Builder
	sb.WriteString(header)
	sb.WriteString("package gotdbot\n\n")
	sb.WriteString("import \"encoding/json\"\n")
	sb.WriteString("import \"fmt\"\n\n")

	sb.WriteString("// TlObject is the interface that all TDLib types satisfy\n")
	sb.WriteString("type TlObject interface {\n")
	sb.WriteString("\tGetType() string\n")
	sb.WriteString("}\n\n")

	sb.WriteString("type tlFunction interface {\n")
	sb.WriteString("\tTlObject\n")
	sb.WriteString("\tsetExtra(extra string)\n")
	sb.WriteString("}\n\n")

	sortedNames := sortKeysAZ(classes)
	for _, name := range sortedNames {
		cls := classes[name]
		structName := toCamelCase(name)
		methodName := toLowerCamelCase(name)

		fmt.Fprintf(&sb, "// %s %s\n", structName, formatDesc(cls.Description))
		if len(cls.Implementations) > 0 {
			impls := append([]string(nil), cls.Implementations...)
			sort.Strings(impls)
			sb.WriteString("//   - ")
			for i, impl := range impls {
				if i > 0 {
					sb.WriteString("//   - ")
				}
				sb.WriteString(toCamelCase(impl))
				sb.WriteByte('\n')
			}
		}

		fmt.Fprintf(&sb, "type %s interface {\n", structName)
		sb.WriteString("\tTlObject\n")
		fmt.Fprintf(&sb, "\t%s()\n", methodName)
		sb.WriteString("}\n\n")

		// Unmarshal helper
		fmt.Fprintf(&sb, "// Unmarshal%s unmarshals the JSON into the correct concrete implementation of %s\n", structName, structName)
		fmt.Fprintf(&sb, "func Unmarshal%s(data []byte) (%s, error) {\n", structName, structName)
		sb.WriteString("\tvar typeObj struct { Type string `json:\"@type\"` }\n")
		sb.WriteString("\tif err := json.Unmarshal(data, &typeObj); err != nil { return nil, err }\n")
		sb.WriteString("\tswitch typeObj.Type {\n")
		for _, impl := range cls.Implementations {
			implStructName := toCamelCase(impl)
			fmt.Fprintf(&sb, "\tcase \"%s\":\n", impl)
			fmt.Fprintf(&sb, "\t\tvar obj %s\n", implStructName)
			sb.WriteString("\t\tif err := json.Unmarshal(data, &obj); err != nil { return nil, err }\n")
			sb.WriteString("\t\treturn &obj, nil\n")
		}
		sb.WriteString("\tdefault:\n")
		sb.WriteString("\t\treturn nil, fmt.Errorf(\"unknown type: %s\", typeObj.Type)\n")
		sb.WriteString("\t}\n")
		sb.WriteString("}\n\n")
	}

	if err := os.WriteFile("gen_classes.go", []byte(sb.String()), 0644); err != nil {
		log.Fatal(err)
	}
}

func generateObjects(types []TLType, classes map[string]*TLClass) {
	var sb strings.Builder
	sb.WriteString(header)
	sb.WriteString("package gotdbot\n\n")
	sb.WriteString("import \"encoding/json\"\n")
	sb.WriteString("import \"fmt\"\nimport \"strings\"\nimport \"strconv\"\n\n")

	for _, t := range types {
		structName := toCamelCase(t.Name)
		fmt.Fprintf(&sb, "// %s %s\n", structName, formatDesc(t.Description))
		fmt.Fprintf(&sb, "type %s struct {\n", structName)

		// Check for fields that are classes to determine if we need custom UnmarshalJSON
		var classFields []TLParam

		for _, p := range t.Params {
			goType := toGoType(p.Type, classes)
			fieldName := toCamelCase(p.Name)
			jsonTag := fmt.Sprintf("`json:\"%s\"`", p.Name)
			if p.Type == "int64" {
				jsonTag = fmt.Sprintf("`json:\"%s,string\"`", p.Name)
			}
			if p.IsOptional {
				if p.Type == "int64" {
					jsonTag = fmt.Sprintf("`json:\"%s,string,omitempty\"`", p.Name)
				} else {
					jsonTag = fmt.Sprintf("`json:\"%s,omitempty\"`", p.Name)
				}
			}
			fmt.Fprintf(&sb, "\t// %s\n", formatDesc(p.Description))
			fmt.Fprintf(&sb, "\t%s %s %s\n", fieldName, goType, jsonTag)

			// Check if type corresponds to a class
			isClass := false
			typeName := p.Type
			if strings.HasPrefix(typeName, "vector<") {
				typeName = strings.TrimSuffix(strings.TrimPrefix(typeName, "vector<"), ">")
			}
			if _, ok := classes[typeName]; ok {
				isClass = true
			}

			if isClass {
				classFields = append(classFields, p)
			}
		}
		sb.WriteString("}\n\n")

		fmt.Fprintf(&sb, "func (t %s) GetType() string {\n", structName)
		fmt.Fprintf(&sb, "\treturn \"%s\"\n", t.Name)
		sb.WriteString("}\n\n")

		if structName == "Error" {
			sb.WriteString("func (t Error) Error() string {\n")
			sb.WriteString("\treturn fmt.Sprintf(\"TDLib error %d: %s\", t.Code, t.Message)\n")
			sb.WriteString("}\n\n")
			sb.WriteString("// GetRetryAfter returns the retry after time in seconds if the error is a flood wait (429).\n")
			sb.WriteString("// It returns 0 if the error is not a flood wait or the time cannot be parsed.\n")
			sb.WriteString("func (t Error) GetRetryAfter() int {\n")
			sb.WriteString("\tif t.Code == 429 && strings.HasPrefix(t.Message, \"Too Many Requests: retry after \") {\n")
			sb.WriteString("\t\tretryStr := strings.TrimPrefix(t.Message, \"Too Many Requests: retry after \")\n")
			sb.WriteString("\t\tif retryAfter, err := strconv.Atoi(retryStr); err == nil {\n")
			sb.WriteString("\t\t\treturn retryAfter\n")
			sb.WriteString("\t\t}\n")
			sb.WriteString("\t}\n")
			sb.WriteString("\treturn 0\n")
			sb.WriteString("}\n\n")
		}

		// Implement interface dummy method if this type belongs to a class
		if cls, ok := classes[t.ResultType]; ok {
			methodName := toLowerCamelCase(cls.Name)
			fmt.Fprintf(&sb, "func (t %s) %s() {}\n\n", structName, methodName)
		}

		// MarshalJSON
		fmt.Fprintf(&sb, "func (t %s) MarshalJSON() ([]byte, error) {\n", structName)
		fmt.Fprintf(&sb, "\ttype Alias %s\n", structName)
		fmt.Fprintf(&sb, "\treturn json.Marshal(&struct{ TypeStr string `json:\"@type\"`; *Alias }{TypeStr: \"%s\", Alias: (*Alias)(&t)})\n", t.Name)
		sb.WriteString("}\n\n")

		// UnmarshalJSON if needed
		if len(classFields) > 0 {
			fmt.Fprintf(&sb, "func (t *%s) UnmarshalJSON(data []byte) error {\n", structName)
			fmt.Fprintf(&sb, "\ttype Alias %s\n", structName)
			sb.WriteString("\taux := &struct {\n")
			for _, p := range classFields {
				fieldName := toCamelCase(p.Name)
				if strings.HasPrefix(p.Type, "vector<") {
					fmt.Fprintf(&sb, "\t\t%s []json.RawMessage `json:\"%s\"`\n", fieldName, p.Name)
				} else {
					fmt.Fprintf(&sb, "\t\t%s json.RawMessage `json:\"%s\"`\n", fieldName, p.Name)
				}
			}
			sb.WriteString("\t\t*Alias\n")
			sb.WriteString("\t}{\n")
			sb.WriteString("\t\tAlias: (*Alias)(t),\n")
			sb.WriteString("\t}\n\n")
			sb.WriteString("\tif string(data) == \"null\" {\n")
			sb.WriteString("\t\treturn nil\n")
			sb.WriteString("\t}\n")
			sb.WriteString("\tif err := json.Unmarshal(data, aux); err != nil {\n")
			sb.WriteString("\t\treturn err\n")
			sb.WriteString("\t}\n\n")

			for _, p := range classFields {
				fieldName := toCamelCase(p.Name)

				typeName := p.Type
				isVector := false
				if strings.HasPrefix(typeName, "vector<") {
					typeName = strings.TrimSuffix(strings.TrimPrefix(typeName, "vector<"), ">")
					isVector = true
				}
				className := toCamelCase(typeName)

				if isVector {
					fmt.Fprintf(&sb, "\tif aux.%s != nil {\n", fieldName)
					fmt.Fprintf(&sb, "\t\tt.%s = make([]%s, len(aux.%s))\n", fieldName, className, fieldName)
					fmt.Fprintf(&sb, "\t\tfor i, raw := range aux.%s {\n", fieldName)
					fmt.Fprintf(&sb, "\t\t\tv, err := Unmarshal%s(raw)\n", className)
					sb.WriteString("\t\t\tif err != nil { return err }\n")
					fmt.Fprintf(&sb, "\t\t\tt.%s[i] = v\n", fieldName)
					sb.WriteString("\t\t}\n")
					sb.WriteString("\t}\n")
				} else {
					fmt.Fprintf(&sb, "\tif aux.%s != nil {\n", fieldName)
					fmt.Fprintf(&sb, "\t\tv, err := Unmarshal%s(aux.%s)\n", className, fieldName)
					sb.WriteString("\t\tif err != nil { return err }\n")
					fmt.Fprintf(&sb, "\t\tt.%s = v\n", fieldName)
					sb.WriteString("\t}\n")
				}
			}
			sb.WriteString("\treturn nil\n")
			sb.WriteString("}\n\n")
		}
	}

	// Unmarshal helper
	sb.WriteString("func Unmarshal(data []byte) (TlObject, string, error) {\n")
	sb.WriteString("\tobj, _, extra, err := UnmarshalWithClient(data)\n")
	sb.WriteString("\treturn obj, extra, err\n")
	sb.WriteString("}\n\n")

	sb.WriteString("// UnmarshalWithClient unmarshals the JSON and returns the object, the client identifier, and the @extra field.\n")
	sb.WriteString("func UnmarshalWithClient(data []byte) (TlObject, int, string, error) {\n")
	sb.WriteString("\tvar typeObj struct {\n")
	sb.WriteString("\t\tType     string `json:\"@type\"`\n")
	sb.WriteString("\t\tClientId int    `json:\"@client_id\"`\n")
	sb.WriteString("\t\tExtra    string `json:\"@extra\"`\n")
	sb.WriteString("\t}\n")
	sb.WriteString("\tif err := json.Unmarshal(data, &typeObj); err != nil { return nil, 0, \"\", err }\n")
	sb.WriteString("\tswitch typeObj.Type {\n")
	for _, t := range types {
		structName := toCamelCase(t.Name)
		fmt.Fprintf(&sb, "\tcase \"%s\":\n", t.Name)
		fmt.Fprintf(&sb, "\t\tvar obj %s\n", structName)
		sb.WriteString("\t\tif err := json.Unmarshal(data, &obj); err != nil { return nil, 0, \"\", err }\n")
		sb.WriteString("\t\treturn &obj, typeObj.ClientId, typeObj.Extra, nil\n")
	}
	sb.WriteString("\tdefault:\n")
	sb.WriteString("\t\treturn nil, 0, \"\", fmt.Errorf(\"unknown type: %s\", typeObj.Type)\n")
	sb.WriteString("\t}\n")
	sb.WriteString("}\n")

	if err := os.WriteFile("gen_types.go", []byte(sb.String()), 0644); err != nil {
		log.Fatal(err)
	}
}

func generateFunctions(functions []TLType, classes map[string]*TLClass) {
	var sb strings.Builder
	sb.WriteString(header)
	sb.WriteString("package gotdbot\n\n")
	sb.WriteString("import \"encoding/json\"\n\n")

	for _, t := range functions {
		structName := toCamelCase(t.Name)
		fmt.Fprintf(&sb, "// %s %s\n", structName, formatDesc(t.Description))
		fmt.Fprintf(&sb, "type %s struct {\n", structName)
		sb.WriteString("\tExtra string `json:\"@extra,omitempty\"` // @extra field\n")

		for _, p := range t.Params {
			goType := toGoType(p.Type, classes)
			fieldName := toCamelCase(p.Name)
			jsonTag := fmt.Sprintf("`json:\"%s\"`", p.Name)
			if p.Type == "int64" {
				jsonTag = fmt.Sprintf("`json:\"%s,string\"`", p.Name)
			}
			if p.IsOptional {
				if p.Type == "int64" {
					jsonTag = fmt.Sprintf("`json:\"%s,string,omitempty\"`", p.Name)
				} else {
					jsonTag = fmt.Sprintf("`json:\"%s,omitempty\"`", p.Name)
				}
			}
			fmt.Fprintf(&sb, "\t// %s\n", formatDesc(p.Description))
			fmt.Fprintf(&sb, "\t%s %s %s\n", fieldName, goType, jsonTag)
		}
		sb.WriteString("}\n\n")

		fmt.Fprintf(&sb, "func (t *%s) setExtra(extra string) { t.Extra = extra }\n\n", structName)

		fmt.Fprintf(&sb, "func (t %s) GetType() string {\n", structName)
		fmt.Fprintf(&sb, "\treturn \"%s\"\n", t.Name)
		sb.WriteString("}\n\n")

		// MarshalJSON
		fmt.Fprintf(&sb, "func (t %s) MarshalJSON() ([]byte, error) {\n", structName)
		fmt.Fprintf(&sb, "\ttype Alias %s\n", structName)
		fmt.Fprintf(&sb, "\treturn json.Marshal(&struct{ TypeStr string `json:\"@type\"`; Extra string `json:\"@extra,omitempty\"`; *Alias }{TypeStr: \"%s\", Extra: t.Extra, Alias: (*Alias)(&t)})\n", t.Name)
		sb.WriteString("}\n\n")
	}

	if err := os.WriteFile("gen_functions.go", []byte(sb.String()), 0644); err != nil {
		log.Fatal(err)
	}
}

func generateOptions(functions []TLType, classes map[string]*TLClass) {
	var sb strings.Builder
	sb.WriteString(header)
	sb.WriteString("package gotdbot\n\n")

	for _, fn := range functions {
		methodName := toCamelCase(fn.Name)
		hasOptional := false
		for _, p := range fn.Params {
			if p.IsOptional || p.Type == "Bool" {
				hasOptional = true
				break
			}
		}

		if hasOptional {
			optsStructName := methodName + "Opts"
			fmt.Fprintf(&sb, "// %s contains optional parameters for %s\n", optsStructName, methodName)
			fmt.Fprintf(&sb, "type %s struct {\n", optsStructName)
			for _, p := range fn.Params {
				if p.IsOptional || p.Type == "Bool" {
					fmt.Fprintf(&sb, "\t// %s\n", formatDesc(p.Description))
					goType := toGoType(p.Type, classes)
					fieldName := toCamelCase(p.Name)
					fmt.Fprintf(&sb, "\t%s %s\n", fieldName, goType)
				}
			}
			sb.WriteString("}\n\n")
		}
	}

	if err := os.WriteFile("gen_options.go", []byte(sb.String()), 0644); err != nil {
		log.Fatal(err)
	}
}

func toLowerCamelCase(s string) string {
	if s == "" {
		return ""
	}
	camel := toCamelCase(s)
	runes := []rune(camel)
	runes[0] = unicode.ToLower(runes[0])
	return string(runes)
}

func generateTDLibOptions(options map[string]*OptionDef) {
	// Filter writable options and sort them
	var writableOptions []string
	for name, def := range options {
		if def.Writable {
			writableOptions = append(writableOptions, name)
		}
	}
	sort.Strings(writableOptions)

	contentBytes, err := os.ReadFile("client_opts.go")
	if err != nil {
		log.Fatal(err)
	}
	content := string(contentBytes)

	structRegex := regexp.MustCompile(`(?s)(// TDLibOptions.*?\n)?type TDLibOptions struct\s*\{`)
	forEachRegex := regexp.MustCompile(`(?s)(// forEachSet.*?\n)?func\s*\(o\s*\*TDLibOptions\)\s*forEachSet\s*\(fn func\(name string, value interface\{\}\)\)\s*\{`)

	var structSb, forEachSb strings.Builder
	structSb.WriteString("// TDLibOptions contains TDLib options that can be set\ntype TDLibOptions struct {\n")
	for _, name := range writableOptions {
		def := options[name]
		fieldName := toCamelCase(name)
		var goType string
		switch def.Type {
		case "Bool":
			goType = "bool"
		case "int64":
			goType = "int64"
		case "string":
			goType = "string"
		default:
			goType = "interface{}"
		}
		fmt.Fprintf(&structSb, "\t// %s\n", formatDesc(def.Description))
		fmt.Fprintf(&structSb, "\t%s %s `json:\"%s,omitempty\"`\n", fieldName, goType, name)
	}
	structSb.WriteString("}")

	forEachSb.WriteString("// forEachSet calls fn for each non-default TDLib option.\nfunc (o *TDLibOptions) forEachSet(fn func(name string, value interface{})) {\n\tif o == nil || fn == nil { return }\n")
	for _, name := range writableOptions {
		fieldName := toCamelCase(name)
		switch options[name].Type {
		case "Bool":
			fmt.Fprintf(&forEachSb, "\tif o.%s { fn(\"%s\", o.%s) }\n", fieldName, name, fieldName)
		case "int64":
			fmt.Fprintf(&forEachSb, "\tif o.%s != 0 { fn(\"%s\", o.%s) }\n", fieldName, name, fieldName)
		case "string":
			fmt.Fprintf(&forEachSb, "\tif o.%s != \"\" { fn(\"%s\", o.%s) }\n", fieldName, name, fieldName)
		default:
			fmt.Fprintf(&forEachSb, "\tif o.%s != nil { fn(\"%s\", o.%s) }\n", fieldName, name, fieldName)
		}
	}
	forEachSb.WriteString("}")

	newContent := content
	if loc := structRegex.FindStringIndex(newContent); loc != nil {
		end := findBalancedBrace(newContent, loc[1]-1)
		if end != -1 {
			for end+1 < len(newContent) && (newContent[end+1] == '\n' || newContent[end+1] == '\r') {
				end++
			}
			newContent = newContent[:loc[0]] + structSb.String() + "\n\n" + newContent[end+1:]
		}
	}

	if loc := forEachRegex.FindStringIndex(newContent); loc != nil {
		end := findBalancedBrace(newContent, loc[1]-1)
		if end != -1 {
			for end+1 < len(newContent) && (newContent[end+1] == '\n' || newContent[end+1] == '\r') {
				end++
			}
			newContent = newContent[:loc[0]] + forEachSb.String() + "\n\n" + newContent[end+1:]
		}
	} else if structLoc := structRegex.FindStringIndex(newContent); structLoc != nil {
		structEnd := findBalancedBrace(newContent, structLoc[1]-1)
		if structEnd != -1 {
			insertAt := structEnd + 1
			newContent = newContent[:insertAt] + "\n\n" + forEachSb.String() + newContent[insertAt:]
		}
	}

	if err := os.WriteFile("client_opts.go", []byte(newContent), 0644); err != nil {
		log.Fatal(err)
	}
}
