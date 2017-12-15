# -*- coding: utf-8 -*-
"""
    http2 server
"""
import logging
import socket
import threading
from os.path import dirname, isfile, join, realpath

import h2.connection
import h2.events

from event import EventProcessor
from http2 import h2utils


class Response:
    """
    Response holds all data needed to verify the expectations of test
    """

    def __init__(self, server, event, address):
        self.server = server
        self.address = address
        try:
            self.received_data = event.data

        except AttributeError:
            pass

        try:
            self.headers = event.headers

        except AttributeError:
            pass

        try:
            self.stream_id = event.stream_id
        except AttributeError:
            pass

        self.type = event.__class__.__name__

    def request_headers(self, field):
        """
        Returns request header value of given field
        """
        for value in self.headers:
            if value[0] == field:
                return value[1]

    def data(self):
        """
        Return data contained in event
        """
        return self.received_data

    def send_response_headers(self, headers=None):
        """
        Sends response headers to client
        """
        logging.info("Sends response headers to client")
        headers_to_send = headers
        if headers:
            # :TODO(Piyush): parse and restructure headers here
            # Convert :status to string as h2 does not want to deal with int

            headers_to_send[':status'] = str(headers_to_send[':status'])
        else:
            # Create basic header
            headers_to_send = [
                (':status', '200'),
                ('server', 'basic-h2-server/1.0'),
                ('content-type', 'application/json'),
            ]
        logging.info(headers_to_send)

        self.server.send_headers(
            stream_id=self.stream_id,
            address=self.address,
            headers=headers_to_send)

    def send_response_body(self, data=None, end_stream=True):
        """
        Sends response body to client
        """
        logging.info("Sends response body to client")
        if data:
            self.server.send_body(
                stream_id=self.stream_id,
                data=data,
                address=self.address,
                end_stream=end_stream)
        else:
            file = "/"
            for header in self.headers:
                if header[0] == ':path':
                    file = header[1]
            self.server.send_body(
                stream_id=self.stream_id,
                data=self.read_file(file),
                address=self.address,
                end_stream=end_stream)

    def read_file(self, filename):
        """
        Read file from filesystem
        """
        # :TODO (Rakesh) Maybe origin folder can be configurable
        filepath = join(dirname(realpath(__file__)), "../../origin")
        filepath = filepath + filename

        if isfile(filepath):
            with open(filepath) as file:
                return file.read()
        else:
            # :TODO(Rakesh) error handling with response of 404
            return ""


class Server(EventProcessor):
    """Class Server stores all the information required for starting http2 server"""

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.sock = None
        self._should_serve = True

        self.port = 8080
        self.address = "0.0.0.0"
        self.httpconn = {}
        self.tcpsock = {}
        self.listen_thread = None

    def config(self, config):
        """
        Configure the port and address of server
        """
        self.port = config.port
        self.address = config.address

    def create_socket(self, listen_socket_event):
        """Create a socket which will be listening for incoming connection from client"""
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.address, self.port))
        logging.debug("Create Socket ")
        self.sock.listen(5)

        logging.debug("TCP socket:" + str(self.sock))

        while self._should_serve:
            logging.debug("Waiting for connection")

            # Signify the ServerStarted
            self.event_received("ServerStarted", self,
                                lambda event, data: True, None)

            listen_socket_event.set()
            try:
                tcpconn, address = self.sock.accept()
            except socket.error as err:
                if not self._should_serve:
                    logging.error("Server listening failed " + err.strerror)
                if self.sock:
                    self.sock.close()
                return

            logging.debug("Socket Connected to client at " + str(address))

            # Signify that Client is Connected
            self.event_received("ClientConnected", self,
                                lambda event, data: True, None)

            logging.debug("TCP connection:" + str(tcpconn))

            # Handle incoming requests on different thread so as to unblock main server thread
            thread = threading.Thread(
                target=self.handle,
                args=(
                    address,
                    tcpconn,
                ),
                name='ListenerThread')
            thread.start()

    def send_headers(self, stream_id=1, address=None, headers=None):
        """Send response headers to client"""

        if not address:
            logging.error("No address to send data to!")
            return

        httpconn = self.httpconn[address]
        tcpsock = self.tcpsock[address]

        httpconn.send_headers(
            stream_id=stream_id,
            headers=headers,
        )

        data_to_send = httpconn.data_to_send()
        if data_to_send:
            tcpsock.sendall(data_to_send)

    def send_body(self,
                  stream_id=1,
                  data="Hello World",
                  address=None,
                  end_stream=True):
        """Send response body to client"""

        if not address:
            logging.error("No address to send data to!")
            return

        httpconn = self.httpconn[address]
        tcpsock = self.tcpsock[address]

        httpconn.send_data(
            stream_id=stream_id, data=data.encode(), end_stream=end_stream)

        data_to_send = httpconn.data_to_send()
        if data_to_send:
            tcpsock.sendall(data_to_send)

    def handle(self, address, tcpconn):
        """handle h2 connection and receive data on given socket"""

        ssl_context = h2utils.get_http2_ssl_context(type="server")

        tcpsock = h2utils.negotiate_tls(tcpconn, ssl_context, type="server")
        logging.debug("TLS Connection: " + str(tcpsock))

        config = h2.config.H2Configuration(client_side=False)
        httpconn = h2.connection.H2Connection(config=config)
        httpconn.initiate_connection()
        tcpsock.sendall(httpconn.data_to_send())

        logging.debug("HTTP2 connection: " + str(httpconn))

        # Save tcpsock and httpconn
        self.httpconn[address] = httpconn
        self.tcpsock[address] = tcpsock
        while self._should_serve:
            data = tcpsock.recv(65535)
            logging.debug("\nTLS Data:")
            logging.debug(data)
            if not data:
                break
            events = httpconn.receive_data(data)
            for event in events:
                logging.debug(
                    "Server Event fired: " + event.__class__.__name__)
                logging.debug("Server Event data: " + str(event))

                self.handle_event(event, address)

    def handle_event(self, event, address):
        """
        handle_events processes each event and then stores them,
        so that they can be handled async when test specifies it
        """

        response = Response(self, event, address)

        compare_func = lambda event, data: True

        # Not sure if these all are needed, special handling can/should be added
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
            if __name__ == "__main__":
                logging.debug(event.headers)
                self.send_headers(address=address)
                self.send_body(address=address)
                return

            def func(event, data):
                """
                Compare func to executed when wait for is Request received
                This function will check whether the current request has same path
                as the request which is to be waited upon
                """
                path = ""
                for header in event.headers:
                    if header[0] == ':path':
                        path = header[1]
                logging.info("path:" + path + " data: " + data)
                if path in data:
                    return True

                return False

            compare_func = func

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

        event_name = event.__class__.__name__
        self.event_received(event_name, response, compare_func, event)
        return

    def kill(self):
        """Close the serving socket"""
        self._should_serve = False
        for address in self.tcpsock:
            self.tcpsock[address].shutdown(socket.SHUT_RDWR)
            self.tcpsock[address].close()

        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def start(self, config=None):
        """Entrypoint for starting the server"""
        if config:
            self.config(config)
        listen_socket_event = threading.Event()
        self.listen_thread = threading.Thread(
            target=self.create_socket,
            args=(listen_socket_event, ),
            name="ServerThread")
        self.listen_thread.start()
        listen_socket_event.wait()


def create(context):
    """
    Create() => server
    Returns the Server object
    """
    server = Server(context)
    return server


def main():
    """Standalone server instance"""
    server = Server()
    server.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:'
        '%(lineno)d:'
        '%(levelname)s:'
        '%(funcName)s():\t'
        '%(message)s')
    main()
