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

func main() {
	// servConf := server.Config{Address: ":8443", Cert: "certs/localhost.cert", Key: "certs/localhost.key"}
	// clientConf := client.Config{URL: "https://localhost:8443"}

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

	fmt.Printf("%#v\n", config.Server)
	fmt.Printf("%#v\n", config.Client)
	srv := server.StartServer(config.Server)
	client.LoadURLWithConfig(config.Client)

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	// gives out error, but not required to handle it
	srv.Shutdown(ctx)
}
