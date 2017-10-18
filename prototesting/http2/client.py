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

"""
    Client class to send client request.
"""


class Client():

    def __init__(self):
        self.context = None
        self.connection = None
        self.tls_connection = None
        self.http2_connection = None
        self.logger = logging.getLogger(__name__)

    def establish_tcp_connection(self, url, port):
        """
        This function establishes a client-side TCP connection.
        """
        return socket.create_connection((url, port))

    def get_http2_ssl_context(self):
        """
        This function creates an SSLContext object that is suitably configured for
        HTTP/2. If you're working with Python TLS directly, you'll want to do the
        exact same setup as this function does.
        """
        # Get the basic context from the standard library.
        ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        # RFC 7540 Section 9.2: Implementations of HTTP/2 MUST use TLS version 1.2
        # or higher. Disable TLS 1.1 and lower.
        ctx.options |= (
            ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        )

        # RFC 7540 Section 9.2.1: A deployment of HTTP/2 over TLS 1.2 MUST disable
        # compression.
        ctx.options |= ssl.OP_NO_COMPRESSION

        # RFC 7540 Section 9.2.2: "deployments of HTTP/2 that use TLS 1.2 MUST
        # support TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256". In practice, the
        # blacklist defined in this section allows only the AES GCM and ChaCha20
        # cipher suites with ephemeral key negotiation.
        ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")

        # We want to negotiate using NPN and ALPN. ALPN is mandatory, but NPN may
        # be absent, so allow that. This setup allows for negotiation of HTTP/1.1.
        ctx.set_alpn_protocols(["h2", "http/1.1"])

        try:
            ctx.set_npn_protocols(["h2", "http/1.1"])
        except NotImplementedError:
            pass

        # Disable checking of certificates on client side
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        return ctx

    def negotiate_tls(self, tcp_conn, context):
        """
        Given an established TCP connection and a HTTP/2-appropriate TLS context,
        this function:

        1. wraps TLS around the TCP connection.
        2. confirms that HTTP/2 was negotiated and, if it was not, throws an error.
        """
        # Note that SNI is mandatory for HTTP/2, so you *must* pass the
        # server_hostname argument.
        tls_conn = context.wrap_socket(tcp_conn, server_hostname='localhost')

        # Always prefer the result from ALPN to that from NPN.
        # You can only check what protocol was negotiated once the handshake is
        # complete.
        negotiated_protocol = tls_conn.selected_alpn_protocol()
        if negotiated_protocol is None:
            negotiated_protocol = tls_conn.selected_npn_protocol()

        if negotiated_protocol != "h2":
            raise RuntimeError("Didn't negotiate HTTP/2!")

        return tls_conn

    def request(self, url):
        # Step 1: Set up your TLS context.
        self.context = self.get_http2_ssl_context()

        parsed_url = urlparse(url)
        url_location = parsed_url.netloc.split(":")

        # Step 2: Create a TCP connection.
        self.connection = self.establish_tcp_connection(
            url_location[0], url_location[1])

        # Step 3: Wrap the connection in TLS and validate that we negotiated HTTP/2
        self.tls_connection = self.negotiate_tls(self.connection, self.context)

        # Step 4: Create a client-side H2 connection.
        self.http2_connection = h2.connection.H2Connection()

        # Step 5: Initiate the connection
        self.http2_connection.initiate_connection()
        self.tls_connection.sendall(self.http2_connection.data_to_send())

        # The TCP, TLS, and HTTP/2 handshakes are now complete. You can enter your
        # main loop now.

        stream_id = self.http2_connection.get_next_available_stream_id()
        self.logger.debug("stream_id: " + str(stream_id))

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
        self.logger.debug("waiting for server to send " + str(expected_content))
        expectation = test_output

        while True:
            data = self.tls_connection.recv(65535)
            self.logger.debug("\nReceived server raw data : " + str(data))
            if not data:
                self.logger.info("no response from server")
            events = self.http2_connection.receive_data(data)
            for event in events:
                self.logger.info("CLient Event fired: " + str(event))
                if isinstance(event, h2.events.DataReceived):
                    self.logger.info(event.data)
                    if event.stream_ended:
                        return
                if isinstance(event, h2.events.ResponseReceived):
                    for header in event.headers:
                        if expected_content in header[1]:
                            self.logger.debug("expectation", expectation, event.headers)
                            expectation.update({"status":"passed"})
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
