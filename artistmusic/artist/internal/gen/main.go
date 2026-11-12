package main

import (
	"log"
	"sort"
)

func main() {
	data, err := LoadTDLibJSON("https://raw.githubusercontent.com/FallenProjects/tdlib-build/refs/heads/master/tdlib.json")
	if err != nil {
		log.Fatalf("Failed to load JSON: %v", err)
	}

	log.Printf("Loaded TDLib-%s with %d types, %d functions, and %d classes", data.Version, len(data.Types), len(data.Functions), len(data.Classes))

	types, functions, classes, options := ConvertJSONToGen(data)

	sortTLTypesByName(types)
	sortTLTypesByName(functions)
	for _, cls := range classes {
		sort.Strings(cls.Implementations)
	}

	log.Println("Generating Go code...")
	generateClasses(classes)
	generateObjects(types, classes)
	generateFunctions(functions, classes)
	generateOptions(functions, classes)
	generateTDLibOptions(options)
	generateMethods(functions, classes)

	helperFiles := generateHelpers(types, functions, classes)

	log.Println("Generating Events...")
	generateEvents(types, classes)

	filesToFmt := append([]string{"gen_classes.go", "gen_types.go", "gen_functions.go", "gen_options.go", "gen_methods.go", "client_opts.go", "gen_events.go"}, helperFiles...)
	gofmt(filesToFmt...)
	log.Println("Done.")
}
