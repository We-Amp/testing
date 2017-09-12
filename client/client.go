package client

import (
	"crypto/tls"
	"io/ioutil"
	"log"
	"net"
	"net/http"

	"golang.org/x/net/http2"
)

// Config for client
type Config struct {
	URL string
}

var (
	// Newconn is pointer to net.Conn interface
	Newconn *net.Conn
	// Tlsconn is pointer to tls.Conn struct
	Tlsconn *tls.Conn
)

// LoadURLWithConfig loads a url specified in config
func LoadURLWithConfig(config Config) string {
	tr := &http2.Transport{
		DialTLS:         dialTLS,
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{Transport: tr}

	url := config.URL
	resp, err := client.Get(url)
	if err != nil {
		log.Fatal(err)
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Fatal(err)
	}

	return string(body)
}

func dialTLS(network, addr string, cfg *tls.Config) (net.Conn, error) {
	cfg.InsecureSkipVerify = true
	newconn, err := net.Dial("tcp", addr)
	if err != nil {
		log.Fatal(err)
	}

	log.Println(newconn.LocalAddr())
	tconn := tls.Client(newconn, cfg)
	Tlsconn = tconn
	log.Printf("State is: %#v", Tlsconn.ConnectionState())

	if err != nil {
		log.Fatal("failed to connect: " + err.Error())
	}
	return tconn, err
}
