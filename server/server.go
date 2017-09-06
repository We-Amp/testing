package main

import (
	"fmt"
	"net/http"

	"golang.org/x/net/http2"
)

type serverConfig struct {
	Address string
}

func handleResponse(w http.ResponseWriter, r *http.Request) {
	fmt.Printf("%+v\n", r)
	fmt.Fprintf(w, "Hello World\n")
}

func startServer(config serverConfig) {
	var srv http.Server
	srv.Addr = config.Address
	// http2.VerboseLogs = true

	http2.ConfigureServer(&srv, nil)

	http.HandleFunc("/", handleResponse)
	err := srv.ListenAndServeTLS("certs/localhost.cert", "certs/localhost.key")
	if err != nil {
		panic(err)
	}
}

func main() {
	config :=
		serverConfig{Address: ":8443"}

	startServer(config)
}
