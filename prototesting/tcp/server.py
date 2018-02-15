"""
TCP Server
"""

import logging
import socket
import struct
import threading

try:
    from event import EventProcessor
    from response import Response
except ImportError:
    import os
    import sys
    # add prototesting folder to sys path to sort out import error
    # this is assuming that the script is called from base of git repo
    sys.path.append(os.path.join(os.getcwd(), "prototesting"))
    from event import EventProcessor
    from response import Response


class TCPResponse(Response):
    """
    Response holds all data needed to verify the expectations of test
    """

    def __init__(self, server, address, data):
        Response.__init__(self, data)
        self.server = server
        self.address = address

    def send_data(self, data=""):
        """
        Send TCP data to client
        """
        self.server.send_data(self.address, data)

    def close_conn(self):
        """
        Close client connection
        """
        self.server.close_conn(self.address)


class Server(EventProcessor):
    """
    Simple TCP Server
    """

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.sock = None
        self._should_serve = True

        self.port = 60000
        self.address = "0.0.0.0"
        self.listen_thread = None
        self.tcpsock = {}

    def config(self, port=60000, host="0.0.0.0"):
        """
        Configure the port and address of server
        """
        if isinstance(port, str):
            port = int(port)
        self.port = port
        self.address = host

    def create_socket(self, listen_socket_event):
        """Create a socket which will be listening for incoming connection from client"""
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.address, self.port))
        self.sock.listen(5)

        while self._should_serve:
            # Signify the ServerStarted
            self.event_received("OnServerStarted", self,
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
            self.tcpsock[address] = tcpconn

            # Signify that Client is Connected
            self.event_received("OnClientConnected",
                                TCPResponse(self, address, ""),
                                lambda event, data: True, None)

            # :TODO(Piyush): Create a new object for storing connections
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

    def handle(self, address, tcpconn):
        """handle tcp connection and receive data on given socket"""

        while self._should_serve:
            try:
                data = tcpconn.recv(65535)
            except socket.error as err:
                # tcpconn is closed handle it gracefully
                logging.error("Server listening failed " + err.strerror)
                return

            if hasattr(data, "decode"):
                data = data.decode()

            logging.info(data)
            self.event_received("OnDataReceived",
                                TCPResponse(self, address, data),
                                lambda event, data: True, None)

    def send_data(self, address, data):
        tcpconn = self.tcpsock[address]
        if hasattr(data, "encode"):
            data = data.encode()
        tcpconn.sendall(data)

    def close_conn(self, address):
        tcpconn = self.tcpsock[address]
        logging.info("Closing tcp conn")
        tcpconn.shutdown(socket.SHUT_RDWR)
        tcpconn.close()

    def kill(self):
        """Close the serving socket"""
        self._should_serve = False

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


def create(contex=None):
    return Server(contex)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:'
        '%(lineno)d:'
        '%(levelname)s:'
        '%(funcName)s():\t'
        '%(message)s')
    logging.info("Before starting")

    class TestContext:
        def __init__(self):
            pass

        def event_received(self, *arg):
            logging.info("Event received called" + str(arg))

    server = create(TestContext())
    server.start()
