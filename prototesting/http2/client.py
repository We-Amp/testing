# -*- coding: utf-8 -*-
"""
Client HTTPS Setup
~~~~~~~~~~~~~~~~~~

This example code fragment demonstrates how to set up a HTTP/2 client that
negotiates HTTP/2 using NPN and ALPN. For the sake of maximum explanatory value
this code uses the synchronous, low-level sockets API: however, if you're not
using sockets directly (e.g. because you're using asyncio), you should focus on
the set up required for the SSLContext object. For other concurrency libraries
you may need to use other setup (e.g. for Twisted you'll need to use
IProtocolNegotiationFactory).

This code requires Python 3.5 or later.
"""
import logging
import socket
import ssl
from urllib.parse import urlparse
import h2.connection
from http2 import h2utils

"""
    Client class to send client request.
"""


class Client():
    """
        This Client provides http2 client functionality.
    """

    def __init__(self):
        self.context = None
        self.connection = None
        self.tls_connection = None
        self.http2_connection = None

    def establish_tcp_connection(self, url, port):
        """
        This function establishes a client-side TCP connection.
        """
        return socket.create_connection((url, port))

    def request(self, url):
        # Step 1: Set up your TLS context.
        self.context = h2utils.get_http2_ssl_context(type="client")

        parsed_url = urlparse(url)
        url_location = parsed_url.netloc.split(":")

        # Step 2: Create a TCP connection.
        self.connection = self.establish_tcp_connection(
            url_location[0], url_location[1])

        # Step 3: Wrap the connection in TLS and validate that we negotiated HTTP/2
        self.tls_connection = h2utils.negotiate_tls(
            self.connection, self.context, type="client")

        # Step 4: Create a client-side H2 connection.
        self.http2_connection = h2.connection.H2Connection()

        # Step 5: Initiate the connection
        self.http2_connection.initiate_connection()
        self.tls_connection.sendall(self.http2_connection.data_to_send())

        # The TCP, TLS, and HTTP/2 handshakes are now complete. You can enter your
        # main loop now.

        stream_id = self.http2_connection.get_next_available_stream_id()
        logging.debug("stream_id: " + str(stream_id))

        self.http2_connection.send_headers(
            stream_id=stream_id,
            headers=[
                (':method', 'GET'),
                (':path', parsed_url.path),
                (':scheme', 'https'),
                (':authority', 'https://localhost'),
            ],
        )
        self.http2_connection.send_data(
            stream_id=stream_id,
            data=b"this is client",
        )

        data_to_send = self.http2_connection.data_to_send()
        if data_to_send:
            self.tls_connection.sendall(data_to_send)

        return self

    def receivecontent(self, expected_content, unused_timeout, test_output):
        logging.debug("waiting for server to send " + str(expected_content))
        expectation = test_output

        while True:
            data = self.tls_connection.recv(65535)
            logging.debug("\nReceived server raw data : " + str(data))
            if not data:
                logging.info("no response from server")
            events = self.http2_connection.receive_data(data)
            for event in events:
                logging.info("CLient Event fired: " + event.__class__.__name__)
                if isinstance(event, h2.events.DataReceived):
                    logging.info(event.data)
                    if event.stream_ended:
                        return
                if isinstance(event, h2.events.ResponseReceived):
                    for header in event.headers:
                        if expected_content in header[1]:
                            logging.debug(
                                "expectation" + str(expectation) + str(event.headers))
                            expectation.update({"status": "passed"})
                            return expectation


def create():
    """
    Create() => client
    Returns the Client object
    """
    return Client()


def main():
    """Standalone client instance"""
    client = Client()
    client.request("http://localhost:8080")


if __name__ == "__main__":
    main()
