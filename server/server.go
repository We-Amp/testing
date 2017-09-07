package server

import (
	"fmt"
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
	srv := &http.Server{Addr: ":" + config.Address}
	// http2.VerboseLogs = true

	http2.ConfigureServer(srv, nil)

	http.HandleFunc("/", handleResponse)

	// create server in new go routine so that we can have gracefull shutdown
	go func() {
		if err := srv.ListenAndServeTLS(config.Cert, config.Key); err != nil {
			println(err.Error())
		}
	}()

	return srv
}
