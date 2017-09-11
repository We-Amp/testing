package server

import (
	"fmt"
	"log"
	"net"
	"net/http"

	"golang.org/x/net/http2"
)

// Config for starting server
type Config struct {
	Address string
	Cert    string
	Key     string
}

func handleResponse(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello World\n")
}

// StartServer starts a http2 server on port provided in config
// with certificate and key file locations
func StartServer(config Config) *http.Server {
	// add ":" in front of port no as Server requires it in that form
	srv := &http.Server{Addr: ":" + config.Address, ConnState: connState}
	// http2.VerboseLogs = true

	http2.ConfigureServer(srv, nil)

	http.HandleFunc("/", handleResponse)

	// create server in new go routine so that we can have gracefull shutdown
	go func() {
		if err := srv.ListenAndServeTLS(config.Cert, config.Key); err != nil {
			log.Println(err)
		}
	}()

	return srv
}

func connState(conn net.Conn, state http.ConnState) {
	log.Println("State is : ", state)
}
