package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
)

// LoadTDLibJSON reads the JSON file and returns the TDLibJSON structure.
func LoadTDLibJSON(url string) (*TDLibJSON, error) {
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch json: %s", resp.Status)
	}

	var data TDLibJSON
	decoder := json.NewDecoder(resp.Body)
	if err := decoder.Decode(&data); err != nil {
		return nil, err
	}

	return &data, nil
}

// ConvertJSONToGen converts the TDLibJSON structure into the format expected by the generators.
func ConvertJSONToGen(data *TDLibJSON) ([]TLType, []TLType, map[string]*TLClass, map[string]*OptionDef) {
	var types []TLType
	var functions []TLType
	classes := make(map[string]*TLClass)

	// Convert Classes
	for name, def := range data.Classes {
		classes[name] = &TLClass{
			Name:            name,
			Description:     def.Description,
			Implementations: def.Types,
		}
	}

	// Helper to convert TypeDef to TLType
	convert := func(name string, def *TypeDef, isFunction bool) TLType {
		var params []TLParam
		var argNames []string
		for k := range def.Args {
			argNames = append(argNames, k)
		}
		sort.Strings(argNames)

		for _, k := range argNames {
			arg := def.Args[k]
			params = append(params, TLParam{
				Name:        k,
				Type:        arg.Type,
				Description: arg.Description,
				IsOptional:  arg.IsOptional,
			})
		}

		return TLType{
			Name:        name,
			Description: def.Description,
			Params:      params,
			ResultType:  def.Type,
			IsFunction:  isFunction,
		}
	}

	// Convert Types
	for name, def := range data.Types {
		types = append(types, convert(name, def, false))
	}

	// Convert Updates
	for name, def := range data.Updates {
		types = append(types, convert(name, def, false))
	}

	// Convert Functions
	for name, def := range data.Functions {
		functions = append(functions, convert(name, def, true))
	}

	return types, functions, classes, data.Options
}
