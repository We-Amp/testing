package client

import (
	"crypto/tls"
	"io/ioutil"
	"log"
	"net/http"

	"golang.org/x/net/http2"
)

// Config for client
type Config struct {
	URL string
}

// LoadURLWithConfig loads a url specified in config
func LoadURLWithConfig(config Config) string {
	tr := &http2.Transport{
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
