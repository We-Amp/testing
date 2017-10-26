# -*- coding: utf-8 -*-
"""
    http2 server
"""
import logging
import socket
import threading

import h2.connection
import h2.events
from http2 import h2utils


class Server:
    """Class Server stores all the information required for starting http2 server"""

    def __init__(self):
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

            try:
                tcpconn, address = self.sock.accept()
            except socket.error:
                if self.sock:
                    self.sock.close()
                return

            logging.info("Socket Created at " + str(address))
            # :TODO(Piyush): Move everything from here to different thread
            # Create a new object for storing connections
            logging.debug("TCP connection:" + str(tcpconn))

            # Handle incoming requests on different thread so as to unblock main server thread
            thread = threading.Thread(
                target=self.handle, args=(address, tcpconn,), name='ListenerThread')
            thread.start()

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

    def handle(self, address, tcpconn):
        """handle something something"""

        context = h2utils.get_http2_ssl_context(type="server")

        tcpsock = h2utils.negotiate_tls(tcpconn, context, type="server")
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
                logging.info("Server Event fired: " +
                             event.__class__.__name__)
                self.handle_event(event, address)

    def handle_event(self, event, address):
        """
        handle_events processes each event and then stores them,
        so that they can be handled async when test specifies it
        """
        class_name = event.__class__.__name__

        if class_name in self.events:
            response_data = self.events[class_name]
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
        for address in self.tcpsock:
            self.tcpsock[address].shutdown(socket.SHUT_RDWR)
            self.tcpsock[address].close()

        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def start(self, config=None):
        """Entrypoint for starting the server"""
        if config:
            self.config(config)
        thread = threading.Thread(
            target=self.create_socket, name="ServerThread")
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
