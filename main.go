package main

import (
	"context"
	"encoding/json"
	"fmt"
	"http2/client"
	"http2/server"
	"log"
	"os"
	"time"
)

type configuration struct {
	Server server.Config
	Client client.Config
}

// StartTest start the test
func StartTest() string {
	file, err := os.Open("config.json")
	if err != nil {
		panic(err)
	}

	decoder := json.NewDecoder(file)
	if err != nil {
		log.Fatal(err)
	}

	config := configuration{}
	err = decoder.Decode(&config)
	if err != nil {
		fmt.Println("error:", err)
	}

	srv := server.StartServer(config.Server)
	output := client.LoadURLWithConfig(config.Client)

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	// gives out error, but not required to handle it
	srv.Shutdown(ctx)

	return output
}

func main() {
	output := StartTest()
	println(output)
}
