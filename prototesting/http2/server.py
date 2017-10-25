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
        self.httpconn = {}
        self.tcpsock = {}
        self.events = {}
        self.__create_class_methods()

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

        logging.debug("TCP socket:" + str(self.sock))

        while self._should_serve:
            logging.debug("Waiting for connection")

            tcpconn, address = self.sock.accept()
            logging.info(address)
            # :TODO(Piyush): Move everything from here to different thread
            # Create a new object for storing connections
            logging.debug("TCP connection:" + str(tcpconn))

            context = self.get_http2_ssl_context()

            tcpsock = self.negotiate_tls(tcpconn, context)
            logging.debug("TLS Connection: " + str(tcpsock))

            config = h2.config.H2Configuration(client_side=False)
            httpconn = h2.connection.H2Connection(config=config)
            httpconn.initiate_connection()
            tcpsock.sendall(httpconn.data_to_send())

            logging.debug("HTTP2 connection: " + str(httpconn))

            # Save tcpsock and httpconn
            self.httpconn[address] = httpconn
            self.tcpsock[address] = tcpsock
            # Handle incoming requests on different thread so as to unblock main server thread
            thread = threading.Thread(target=self.handle, args=(address,))
            thread.start()

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
        logging.debug(ctx.get_ciphers())

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

    def sendresponseheaders(self, address=None, unused_headers=None):
        """Send response headers to client"""
        stream_id = 1
        #:TODO(Piyush) TEMPORARY HACK!
        # Remove ASAP

        if not address:
            httpconn = self.httpconn[next(iter(self.httpconn))]
            tcpsock = self.tcpsock[next(iter(self.tcpsock))]
        else:
            httpconn = self.httpconn[address]
            tcpsock = self.tcpsock[address]

        httpconn.send_headers(
            stream_id=stream_id,
            headers=[
                (':status', '200'),
                ('server', 'basic-h2-server/1.0'),
                ('content-type', 'application/json'),
            ],
        )

        data_to_send = httpconn.data_to_send()
        if data_to_send:
            tcpsock.sendall(data_to_send)

    def sendresponsebody(self, data="Hello World", address=None, end_stream=True):
        """Send response body to client"""
        stream_id = 1
        #:TODO(Piyush) TEMPORARY HACK!
        # Remove ASAP

        if not address:
            httpconn = self.httpconn[next(iter(self.httpconn))]
            tcpsock = self.tcpsock[next(iter(self.tcpsock))]
        else:
            httpconn = self.httpconn[address]
            tcpsock = self.tcpsock[address]

        httpconn.send_data(
            stream_id=stream_id,
            data=data.encode(),
            end_stream=end_stream
        )

        data_to_send = httpconn.data_to_send()
        if data_to_send:
            tcpsock.sendall(data_to_send)

    def handle(self, address):
        """handle something something"""
        while self._should_serve:
            tcpsock = self.tcpsock[address]
            httpconn = self.httpconn[address]
            data = tcpsock.recv(65535)
            logging.debug("\nTLS Data:")
            logging.debug(data)
            if not data:
                break
            events = httpconn.receive_data(data)
            for event in events:
                logging.info("\nServer Event fired: " + str(event))
                self.handle_event(event, address)

    def handle_event(self, event, address):
        """
        handle_events processes each event and then stores them,
        so that they can be handled async when test specifies it
        """
        class_name = event.__class__.__name__

        if class_name in self.events:
            response_data = self.events[class_name]
            logging.info(str(response_data))
            threading_event, test_unit, name = response_data

            #:TODO(Piyush): send response object instead of event here
            setattr(test_unit, name, event)
            threading_event.set()

        # Not sure if these all are needed, special handlin can/should be added
        # on need to basis

        if isinstance(event, h2.events.AlternativeServiceAvailable):
            pass
        elif isinstance(event, h2.events.ChangedSetting):
            pass
        elif isinstance(event, h2.events.ConnectionTerminated):
            pass
        elif isinstance(event, h2.events.DataReceived):
            pass
        elif isinstance(event, h2.events.InformationalResponseReceived):
            pass
        elif isinstance(event, h2.events.PingAcknowledged):
            pass
        elif isinstance(event, h2.events.PriorityUpdated):
            pass
        elif isinstance(event, h2.events.PushedStreamReceived):
            pass
        elif isinstance(event, h2.events.RemoteSettingsChanged):
            pass
        elif isinstance(event, h2.events.RequestReceived):
            logging.info(dir(self))
            if __name__ == "__main__":
                logging.debug(event.headers)
                self.sendresponseheaders(address=address)
                self.sendresponsebody(address=address)

        elif isinstance(event, h2.events.ResponseReceived):
            pass
        elif isinstance(event, h2.events.SettingsAcknowledged):
            pass
        elif isinstance(event, h2.events.StreamEnded):
            pass
        elif isinstance(event, h2.events.StreamReset):
            pass
        elif isinstance(event, h2.events.TrailersReceived):
            pass
        elif isinstance(event, h2.events.WindowUpdated):
            pass

    def __create_class_methods(self):
        """
            Create functions from list of events such that it sets itself in
            events list
        """
        events_list = ['AlternativeServiceAvailable', 'ChangedSetting', 'ConnectionTerminated',
                       'DataReceived', 'InformationalResponseReceived', 'PingAcknowledged',
                       'PriorityUpdated', 'PushedStreamReceived', 'RemoteSettingsChanged',
                       'RequestReceived', 'ResponseReceived', 'SettingsAcknowledged',
                       'StreamEnded', 'StreamReset', 'TrailersReceived', 'WindowUpdated']

        for event_name in events_list:
            self.__add_method(event_name)

    def __add_method(self, event_name):
        """
        Add a method with name event_name to class
        """

        def fn(event, test_unit, name):
            """This function sets events list will required value"""
            self.events[event_name] = (event, test_unit, name)
        setattr(self, event_name, fn)

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
    logging.basicConfig(level=logging.INFO,
                        format='%(filename)s:'
                        '%(lineno)d:'
                        '%(levelname)s:'
                        '%(funcName)s():\t'
                        '%(message)s')
    main()
