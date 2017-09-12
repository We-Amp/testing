# testing
network testing tooling

Steps
-----
- Install [go](https://golang.org/doc/install)
- Install all required libs
    - `go get golang.org/x/net/http2`
    - `go get github.com/franela/goblin`

- Clone this repo in `$GOPATH/src`

- ATS config 
    * Add these to records.config
      - `CONFIG proxy.config.http.server_ports STRING 80,443:proto=http2;http:ssl`

    * Add certificates in records.config
      - `CONFIG proxy.config.ssl.server.cert.path STRING "$PATH_TO_CODE/http2/certs/localhost.cert"`
      - `CONFIG proxy.config.ssl.server.private_key.path STRING "$PATH_TO_CODE/http2/certs/localhost.key"`

    * Add certificates in ssl_multicerts.config 
      - `dest_ip=* ssl_cert_name=$PATH_TO_CODE/http2/certs/localhost.cert ssl_key_name=$PATH_TO_CODE/http2/certs/localhost.key`

    * Update remap.config
      - `map https://localhost:443 https://localhost:8443`

* Update `config.json` with ATS path, server and client config

* Run the program with 
  - `go run main.go`
* Run the tests with go test in http2 folder
  - `go test`
