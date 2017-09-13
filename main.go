package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"time"

	"testing/client"
	"testing/server"
)

//Configuration Takes configuration from json file
type Configuration struct {
	TrafficServer string
	Server        server.Config
	Client        client.Config
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
	checkConnState()
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	// gives out error, but not required to handle it
	srv.Shutdown(ctx)

	return output
}

// StartServer used to start the traffic server
func startServer(atsPath string) {
	cmd := exec.Command(atsPath, "start")
	ch := make(chan []byte)
	go func() {
		cmdout, err := cmd.Output()
		if err != nil {
			fmt.Println("Error: ", err)
		}
		ch <- cmdout
	}()

	output := <-ch

	s := string(output[:])

	log.Printf("Launched server: %s", s)
}

func stopServer(atsPath string) {
	cmd := exec.Command(atsPath, "stop")
	ch := make(chan []byte)
	go func() {
		cmdout, err := cmd.Output()
		if err != nil {
			fmt.Println("Error: ", err)
		}
		ch <- cmdout
	}()

	output := <-ch
	s := string(output[:])

	log.Printf("Stopped server: %s", s)
}

func checkConnState() {
	log.Println(client.Tlsconn.RemoteAddr())
}

func main() {
	// TODO(piyush): take config filepath as command line param
	log.SetFlags(log.Lshortfile)

	filePath := "config.json"
	config := GetConfig(filePath)

	if config.TrafficServer != "" {
		startServer(config.TrafficServer)
	} else {
		log.Println("ATS path is empty")
	}

	output := StartTest(config)
	log.Println(output)

	if config.TrafficServer != "" {
		stopServer(config.TrafficServer)
	}
}
