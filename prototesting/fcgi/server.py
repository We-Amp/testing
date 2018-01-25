"""
FCGI Server
"""

import logging
import socket
import struct
import threading

import flup.server.fcgi_base as fcgi

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


class FCGIResponse(Response):
    """
    Response holds all data needed to verify the expectations of test
    """

    def __init__(self, server, address, data):
        Response.__init__(self, data)
        self.server = server
        self.address = address

    def send_record(self,
                    request_id=1,
                    type="FCGI_END_REQUEST",
                    data="",
                    content_length=0,
                    padding_length=0,
                    version=1):
        """
        Send a FCGI record to client
        """
        self.server.send_record(self.address, request_id, type, data,
                                content_length, padding_length, version)


class Server(EventProcessor):
    """
    Simple FCGI Server
    """

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.sock = None
        self._should_serve = True

        self.port = 60000
        self.address = "0.0.0.0"
        self.listen_thread = None
        self.tcpsock = {}
        self.keepconn = False

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
        self.sock.listen(5)

        while self._should_serve:
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
            self.tcpsock[address] = tcpconn

            # Signify that Client is Connected
            self.event_received("ClientConnected", self,
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
        """handle fcgi connection and receive data on given socket"""

        while self._should_serve:
            try:
                data = tcpconn.recv(65535)
            except socket.error as err:
                # tcpconn is closed handle it gracefully
                logging.error("Server listening failed " + err.strerror)
                return

            self.handle_events(address, data)

    def handle_events(self, address, data):
        length = len(data)
        position = 0
        while position < length:
            logging.info(str(position))
            fcgi_header = data[position:position + fcgi.FCGI_HEADER_LEN]
            version, fcgi_type, request_id, content_length, padding_length = struct.unpack(
                fcgi.FCGI_Header, fcgi_header)

            position += fcgi.FCGI_HEADER_LEN
            content_data = data[position:position + content_length]

            if fcgi_type == fcgi.FCGI_GET_VALUES:
                self.event_received("FCGI_GET_VALUES",
                                    FCGIResponse(self, address, content_data),
                                    lambda event, data: True, None)
                logging.info("FCGI_GET_VALUES")
            elif fcgi_type == fcgi.FCGI_BEGIN_REQUEST:

                self.event_received("FCGI_BEGIN_REQUEST",
                                    FCGIResponse(self, address, content_data),
                                    lambda event, data: True, None)
                unused_role, flags = struct.unpack(fcgi.FCGI_BeginRequestBody,
                                                   content_data)

                if flags & 1:
                    self.keepconn = True

                logging.info("FCGI_BEGIN_REQUEST")
            elif fcgi_type == fcgi.FCGI_ABORT_REQUEST:
                self.event_received("FCGI_ABORT_REQUEST",
                                    FCGIResponse(self, address, content_data),
                                    lambda event, data: True, None)
                logging.info("FCGI_ABORT_REQUEST")
            elif fcgi_type == fcgi.FCGI_PARAMS:
                logging.info("FCGI_PARAMS")
                pos = 0
                decoded_data = {}
                while pos < len(content_data):
                    pos, (name, value) = fcgi.decode_pair(content_data, pos)
                    decoded_data[name.decode()] = value.decode()

                logging.info(decoded_data)
                self.event_received("FCGI_PARAMS",
                                    FCGIResponse(self, address, decoded_data),
                                    lambda event, data: True, None)

            elif fcgi_type == fcgi.FCGI_STDIN:
                logging.info("FCGI_STDIN")
                logging.info("Data: " + content_data.decode())
                self.event_received("FCGI_STDIN",
                                    FCGIResponse(self, address, content_data),
                                    lambda event, data: True, None)

                if __name__ == "__main__":
                    if not content_data:
                        self.send_record(
                            address,
                            type="FCGI_STDOUT",
                            data="Content-type: text/html\r\n\r\nYeello1\r\n")
                        self.send_record(
                            address, type="FCGI_STDOUT", data="Yeello2\r\n")
                        self.send_record(
                            address, type="FCGI_STDOUT", data="Yeello3\r\n")

                        self.send_record(
                            address, type="FCGI_STDOUT", data="\r\n\r\n")
                        self.send_record(address)

            elif fcgi_type == fcgi.FCGI_DATA:
                self.event_received("FCGI_DATA",
                                    FCGIResponse(self, address, content_data),
                                    lambda event, data: True, None)
                logging.info("FCGI_DATA")
            elif request_id == fcgi.FCGI_NULL_REQUEST_ID:
                logging.info("FCGI_NULL_REQUEST_ID")
            else:
                # Need to complain about this.
                pass

            position += content_length

    def send_headers(self,
                     headers=[('Content-Type', 'text/html')],
                     status='200 OK'):
        pass

    def send_body(self, data=""):
        pass

    def send_record(self,
                    address,
                    request_id=1,
                    type=fcgi.FCGI_END_REQUEST,
                    data="",
                    content_length=0,
                    padding_length=0,
                    version=1):

        tcpconn = self.tcpsock[address]

        if type == "FCGI_STDOUT":
            type = fcgi.FCGI_STDOUT

        else:
            type = fcgi.FCGI_END_REQUEST

        if type == fcgi.FCGI_END_REQUEST:
            data = struct.pack(fcgi.FCGI_EndRequestBody, 0, 0)
            content_length = fcgi.FCGI_EndRequestBody_LEN

        if data and not content_length:
            content_length = len(data)

        version = int(version)
        content_length = int(content_length)

        # logging.info("Data: " + data)
        # logging.info("contentLength: " + str(content_length))

        header = struct.pack(fcgi.FCGI_Header, version, type, request_id,
                             content_length, padding_length)

        logging.info("Sending Record " + str(type) + " " + str(content_length))
        tcpconn.sendall(header)

        if hasattr(data, "encode"):
            data = data.encode()

        if content_length:
            tcpconn.sendall(data)

        if padding_length:
            tcpconn.sendall(b'\x00' * padding_length)

        if type == fcgi.FCGI_END_REQUEST and not self.keepconn:
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
