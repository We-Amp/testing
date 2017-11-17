"""TODO(Piyush)"""
import asyncio
import logging
from os.path import dirname, isfile, join, realpath

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import (ConnectionTerminated, DataReceived, RequestReceived,
                       StreamEnded)
from h2.exceptions import ProtocolError

from http2 import h2utils
from jsonparser.jsonparser import EventProcessor


class Response:
    """
    Response holds all data needed to verify the expectations of test
    """

    def __init__(self, conn, event):
        self.conn = conn
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

        self.conn.send_headers(self.stream_id, headers=headers_to_send)

    def send_response_body(self, data=None, end_stream=True):
        """
        Sends response body to client
        """
        logging.info("Sends response body to client")
        if data:
            self.conn.send_body(self.stream_id, data=data,
                                end_stream=end_stream)
        else:
            file = "/"
            for header in self.headers:
                if header[0] == ':path':
                    file = header[1]
            self.conn.send_body(self.stream_id,
                                data=self.read_file(file), end_stream=end_stream)

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


class H2Protocol(asyncio.Protocol, EventProcessor):
    """
    TODO:(Piyush)
    """

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        config = H2Configuration(client_side=False, header_encoding='utf-8')
        self.conn = H2Connection(config=config)
        self.transport = None
        logging.info("Class is created")
        logging.info(context)
        self.stream_data = {}

    def connection_made(self, transport: asyncio.Transport):
        logging.info("connection made")
        logging.info(transport)
        self.transport = transport
        self.conn.initiate_connection()
        data = self.conn.data_to_send()
        self.transport.write(data)

    def data_received(self, data: bytes):
        try:
            events = self.conn.receive_data(data)
        except ProtocolError as e:
            self.transport.write(self.conn.data_to_send())
            self.transport.close()
        else:
            self.transport.write(self.conn.data_to_send())
            for event in events:
                def compare_func(event, data): return True

                if isinstance(event, RequestReceived):
                    compare_func = self.request_received(event)
                # elif isinstance(event, DataReceived):
                #     self.receive_data(event)
                # elif isinstance(event, StreamEnded):
                #     self.stream_complete(event.stream_id)
                # elif isinstance(event, ConnectionTerminated):
                #     self.transport.close()
                response = Response(self, event)
                event_name = event.__class__.__name__
                self.event_received(event_name, response, compare_func, event)

    def send_headers(self, stream_id, headers):
        """Send response headers to client"""

        self.conn.send_headers(
            stream_id=stream_id,
            headers=headers,
        )

        self.transport.write(self.conn.data_to_send())

    def send_body(self, stream_id, data="Hello World", end_stream=True):
        """Send response body to client"""

        self.conn.send_data(
            stream_id=stream_id,
            data=data.encode("utf8"),
            end_stream=end_stream
        )

        self.transport.write(self.conn.data_to_send())

    def request_received(self, event):
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

        return func


class AsyncServer(EventProcessor):
    """
    TODO(Piyush):
    """

    def __init__(self, context=None):
        self.context = context
        self.port = 8080
        self.address = "0.0.0.0"
        self.server = None
        self.loop = None

    def start(self):
        context = h2utils.get_http2_ssl_context(type="server")
        self.loop = asyncio.new_event_loop()

        logging.info("Before starting server")
        # Each client connection will create a new protocol instance
        logging.info(self.context)

        def H2ProtocolFactory():
            """Creates a factory that will return the H2protocol object with context"""
            return H2Protocol(self.context)

        coro = self.loop.create_server(
            H2ProtocolFactory, self.address, self.port, ssl=context)

        logging.info(coro)
        self.server = self.loop.run_until_complete(coro)
        logging.info(self.server)

    def kill(self):
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()


def create(context=None):
    """
    Create() => server
    Returns the Server object
    """
    context = "Hello"
    async_server = AsyncServer(context)
    return async_server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(filename)s:'
                        '%(lineno)d:'
                        '%(levelname)s:'
                        '%(funcName)s():\t'
                        '%(message)s')
    async_server = create()
    async_server.start()

    loop = asyncio.get_event_loop()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    async_server.kill()
