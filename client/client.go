package client

import (
	"crypto/tls"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"net/http/httptrace"

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

	url := config.URL

	req, _ := http.NewRequest("GET", url, nil)
	trace := &httptrace.ClientTrace{
		GetConn: func(hostPort string) { log.Println("GetConn1") },

		GotConn: func(httptrace.GotConnInfo) { log.Println("GetConn2") },

		PutIdleConn: func(err error) { log.Println("PutIdleConn") },

		GotFirstResponseByte: func() { log.Println("GotFirstResponseByte") },

		Got100Continue: func() { log.Println("Got100Continue") },

		DNSStart: func(httptrace.DNSStartInfo) { log.Println("DNSStart") },

		DNSDone: func(httptrace.DNSDoneInfo) { log.Println("DNSDone") },

		ConnectStart: func(network, addr string) { log.Println("ConnectStart") },

		ConnectDone: func(network, addr string, err error) { log.Println("ConnectDone") },

		TLSHandshakeStart: func() { log.Println("TLSHandshakeStart") },

		TLSHandshakeDone: func(tls.ConnectionState, error) { log.Println("TLSHandshakeDone") },

		WroteHeaders: func() { log.Println("WroteHeaders") },

		Wait100Continue: func() { log.Println("Wait100Continue") },

		WroteRequest: func(httptrace.WroteRequestInfo) { log.Println("WroteRequest") },
	}
	req = req.WithContext(httptrace.WithClientTrace(req.Context(), trace))
	client := &http.Client{Transport: tr}

	resp, err := client.Do(req)
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

	if err != nil {
		log.Fatal("failed to connect: " + err.Error())
	}
	return tconn, err
}
