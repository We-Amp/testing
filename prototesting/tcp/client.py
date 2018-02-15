"""Simple tcp client"""

import logging
import socket
import threading
from urllib.parse import urlparse

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


class Request(EventProcessor):
    """ Class to handle requests in client"""

    def __init__(self, context, stream_id):
        EventProcessor.__init__(self, context)

        self.stream_id = stream_id

    def add_received_events(self, response, event):
        """
        Cache received events
        """
        logging.info("Cache received events:" + response.type)

        event_name = event.__class__.__name__
        self.event_received(event_name, response, lambda event, data: True,
                            event)


class Client(EventProcessor):
    """
        This Client provides TCP client functionality.
    """

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.connection = None
        self.thread = None
        self.requests = {}
        self.context = context

    def establish_tcp_connection(self, url, port):
        """
        This function establishes a client-side TCP connection.
        """
        logging.info(url)
        logging.info(port)
        return socket.create_connection((url, port))

    def connect(self, host, port):
        """
        TODO(Piyush): Add description
        """
        # :TODO(Piyush): Check if it should accept a url or port

        # parsed_url = urlparse(url)
        # host = parsed_url.netloc
        # port = '443'
        # if ':' in host:
        #     # host contains a port so we will use that port
        #     url_location = host.split(":")
        #     host = url_location[0]
        #     port = url_location[1]

        # Step 2: Create a TCP connection.
        self.connection = self.establish_tcp_connection(host, port)
        self.thread = threading.Thread(
            target=self.receive, name="ClientThread")
        self.thread.start()
        return self

    def send_data(self, data=""):
        """
        Send data to server
        """
        if hasattr(data, "encode"):
            data = data.encode()
        self.connection.send(data)

    def receive(self):
        """
        Waits for data sent by server to be received on client
        """
        while True:
            data = None
            try:
                data = self.connection.recv(65535)
                logging.debug("\nReceived server raw data : " + str(data))
            except socket.error as err:
                logging.warn(err)
                return

            if hasattr(data, "decode"):
                data = data.decode()
            self.event_received("OnDataReceived", Response(data),
                                lambda event, data: True, None)

    def stop(self):
        """
        Stop/Kill client
        """
        self.connection.close()


def create(context):
    """
    Create() => client
    Returns the Client object
    """
    return Client(context)


def main():
    """Standalone client instance"""
    client = Client()
    client.connect("localhost", "8080")


if __name__ == "__main__":
    main()
