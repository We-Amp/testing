package main

import (
	"fmt"
	"http2/client"
	"http2/server"
)

func main() {
	servConf := server.Config{Address: ":8443", Cert: "certs/localhost.cert", Key: "certs/localhost.key"}
	clientConf := client.Config{URL: "https://localhost:8443"}

	fmt.Printf("%#v\n", servConf)
	fmt.Printf("%#v\n", clientConf)
	go server.StartServer(servConf)
	client.LoadURLWithConfig(clientConf)
}
