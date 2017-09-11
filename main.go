package main

import (
	"context"
	"encoding/json"
	"http2/client"
	"http2/server"
	"log"
	"os"
	"time"
)

//Configuration Takes configuration from json file
type Configuration struct {
	Server server.Config
	Client client.Config
}

// GetConfig from file
func GetConfig(filePath string) Configuration {
	file, err := os.Open(filePath)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	decoder := json.NewDecoder(file)
	if err != nil {
		log.Fatal(err)
	}

	config := Configuration{}
	err = decoder.Decode(&config)
	if err != nil {
		log.Fatal(err)
	}

	return config
}

// StartTest start the test
func StartTest(config Configuration) string {
	srv := server.StartServer(config.Server)
	output := client.LoadURLWithConfig(config.Client)
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	// gives out error, but not required to handle it
	srv.Shutdown(ctx)

	return output
}

func main() {
	// TODO(piyush): take config filepath as command line param
	log.SetFlags(log.Lshortfile)
	filePath := "config.json"
	config := GetConfig(filePath)
	output := StartTest(config)
	log.Println(output)
}
