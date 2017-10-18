# -*- coding: utf-8 -*-
"""
    http2 server
"""
import logging
import socket
import ssl
import threading

import h2.connection
import h2.events


class Server:
    """Class Server stores all the information required for starting http2 server"""

    def __init__(self, config=None):
        self.sock = None
        self._should_serve = True

        self.port = 8080
        self.address = "0.0.0.0"
        self.events = []
        self.httpconn = None
        self.tcpsock = None
        self.logger = logging.getLogger(__name__)

    def config(self, config):
        """
        Configure the port and address of server
        """
        self.port = config.port
        self.address = config.address

    def create_socket(self):
        """Create a socket which will be listening for incoming connection from client"""
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.address, self.port))
        self.sock.listen(5)

        self.logger.debug("TCP socket:" + str(self.sock))

        while self._should_serve:
            self.logger.debug("Waiting for connection")

            tcpconn, unused_address = self.sock.accept()
            self.logger.debug("TCP connection:" + str(tcpconn))

            context = self.get_http2_ssl_context()

            self.tcpsock = self.negotiate_tls(tcpconn, context)
            self.logger.debug("TLS Connection: " + str(self.tcpsock))

            config = h2.config.H2Configuration(client_side=False)
            self.httpconn = h2.connection.H2Connection(config=config)
            self.httpconn.initiate_connection()
            self.tcpsock.sendall(self.httpconn.data_to_send())

            self.logger.debug("HTTP2 connection: " + str(self.httpconn))

            self.handle()

    def get_http2_ssl_context(self):
        """
        This function creates an SSLContext object that is suitably configured for
        HTTP/2. If you're working with Python TLS directly, you'll want to do the
        exact same setup as this function does.
        """
        # Get the basic context from the standard library.
        ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)

        # RFC 7540 Section 9.2: Implementations of HTTP/2 MUST use TLS version 1.2
        # or higher. Disable TLS 1.1 and lower.
        ctx.options |= (
            ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        )

        # RFC 7540 Section 9.2.1: A deployment of HTTP/2 over TLS 1.2 MUST disable
        # compression.
        ctx.options |= ssl.OP_NO_COMPRESSION

        # RFC 7540 Section 9.2.2: "deployments of HTTP/2 that       use TLS 1.2 MUST
        # support TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256". In practice, the
        # blacklist defined in this section allows only the AES GCM and ChaCha20
        # cipher suites with ephemeral key negotiation.
        ctx.set_ciphers("ECDHE-RSA-AES256-GCM-SHA384")
        self.logger.debug(ctx.get_ciphers())

        ctx.load_cert_chain(certfile="certs/server.crt",
                            keyfile="certs/server.key")

        # We want to negotiate using NPN and ALPN. ALPN is mandatory, but NPN may
        # be absent, so allow that. This setup allows for negotiation of HTTP/1.1.
        ctx.set_alpn_protocols(["h2", "http/1.1"])

        try:
            ctx.set_npn_protocols(["h2", "http/1.1"])
        except NotImplementedError:
            pass

        return ctx

    def negotiate_tls(self, tcp_conn, context):
        """
        Given an established TCP connection and a HTTP/2-appropriate TLS context,
        this function:

        1. wraps TLS around the TCP connection.
        2. confirms that HTTP/2 was negotiated and, if it was not, throws an error.
        """
        tls_conn = context.wrap_socket(tcp_conn, server_side=True)

        # Always prefer the result from ALPN to that from NPN.
        # You can only check what protocol was negotiated once the handshake is
        # complete.
        negotiated_protocol = tls_conn.selected_alpn_protocol()
        if negotiated_protocol is None:
            negotiated_protocol = tls_conn.selected_npn_protocol()

        if negotiated_protocol != "h2":
            raise RuntimeError("Didn't negotiate HTTP/2!")

        return tls_conn

    def sendresponseheaders(self, unused_headers=None):
        """Send response headers to client"""
        self.logger.info("Inside sendresponse$$$$$$$$$$$$$$")
        stream_id = None
        for event in self.events:
            self.logger.info("\nServer Event fired: ", str(event))
            if isinstance(event, h2.events.RequestReceived):
                self.logger.info(event.headers)
                stream_id = event.stream_id
        # response_data = json.dumps(dict(event.headers)).encode('utf-8')

        self.httpconn.send_headers(
            stream_id=stream_id,
            headers=[
                (':status', '200'),
                ('server', 'basic-h2-server/1.0'),
                ('content-type', 'application/json'),
            ],
        )

        data_to_send = self.httpconn.data_to_send()
        if data_to_send:
            self.tcpsock.sendall(data_to_send)

    def sendresponsebody(self, data="Hello World", end_stream=True):
        """Send response body to client"""
        stream_id = None
        for event in self.events:
            self.logger.info("\nServer Event fired: ", str(event))
            if isinstance(event, h2.events.RequestReceived):
                self.logger.info(event.headers)
                stream_id = event.stream_id
        # response_data = json.dumps(dict(event.headers)).encode('utf-8')

        self.httpconn.send_data(
            stream_id=stream_id,
            data=b"{data}",
            end_stream=end_stream
        )

        data_to_send = self.httpconn.data_to_send()
        if data_to_send:
            self.tcpsock.sendall(data_to_send)

    def handle(self):
        """handle something something"""
        while self._should_serve:
            data = self.tcpsock.recv(65535)
            self.logger.debug("\nTLS Data:")
            self.logger.debug(data)
            if not data:
                break
            self.events = self.httpconn.receive_data(data)
            # for event in events:
            #     self.logger.info("\nServer Event fired: ", str(event))
            #     if isinstance(event, h2.events.RequestReceived):
            # self.logger.debug(event.headers)
            # self.sendresponseheaders(httpconn, event)
            # self.sendresponsebody(httpconn, event)

            data_to_send = self.httpconn.data_to_send()
            if data_to_send:
                self.tcpsock.sendall(data_to_send)

    def kill(self):
        """Close the serving socket"""
        self._should_serve = False
        self.sock.close()

    def start(self, config=None):
        """Entrypoint for starting the server"""
        if config:
            self.config(config)
        thread = threading.Thread(target=self.create_socket)
        thread.start()


def create():
    """
    Create() => server
    Returns the Server object
    """
    server = Server()
    return server


def main():
    """Standalone server instance"""
    server = Server()
    server.start()


if __name__ == "__main__":
    main()
