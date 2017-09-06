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
	fmt.Printf("%+v\n", r)
	fmt.Fprintf(w, "Hello World\n")
}

// StartServer something
func StartServer(config Config) {
	var srv http.Server
	// add ":" in front of port no as Server requires it in that form
	srv.Addr = ":" + config.Address
	// http2.VerboseLogs = true

	http2.ConfigureServer(&srv, nil)

	http.HandleFunc("/", handleResponse)
	err := srv.ListenAndServeTLS(config.Cert, config.Key)
	if err != nil {
		panic(err)
	}
}
