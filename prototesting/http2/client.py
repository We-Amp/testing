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
import threading
from urllib.parse import urlparse

import h2.connection

from event import EventProcessor
from http2 import h2utils
"""
    Client class to send client request.
"""


class Response:
    """
    Response holds all data needed to verify the expectations of test
    """

    def __init__(self, event):
        self.type = event.__class__.__name__

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

    def response_headers(self, field):
        for value in self.headers:
            if value[0] == field:
                return value[1]

    def data(self):
        return self.received_data


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
        This Client provides http2 client functionality.
    """

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.sslcontext = None
        self.connection = None
        self.tls_connection = None
        self.http2_connection = None
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

    def request(self, url):
        """
        TODO(Piyush): Add description
        """
        # Step 1: Set up your TLS context.
        self.sslcontext = h2utils.get_http2_ssl_context(type="client")

        parsed_url = urlparse(url)
        host = parsed_url.netloc
        port = '443'
        if ':' in host:
            # host contains a port so we will use that port
            url_location = host.split(":")
            host = url_location[0]
            port = url_location[1]

        # Step 2: Create a TCP connection.
        self.connection = self.establish_tcp_connection(host, port)

        # Step 3: Wrap the connection in TLS and validate that we negotiated HTTP/2
        self.tls_connection = h2utils.negotiate_tls(
            self.connection, self.sslcontext, type="client")

        # Step 4: Create a client-side H2 connection.
        self.http2_connection = h2.connection.H2Connection()

        # Step 5: Initiate the connection
        self.http2_connection.initiate_connection()
        self.tls_connection.sendall(self.http2_connection.data_to_send())

        # The TCP, TLS, and HTTP/2 handshakes are now complete. You can enter your
        # main loop now.

        return self

    def send_on_stream(self, url):
        stream_id = self.http2_connection.get_next_available_stream_id()
        logging.debug("stream_id: " + str(stream_id))

        parsed_url = urlparse(url)

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

        if self.thread:
            pass
        else:
            self.thread = threading.Thread(
                target=self.receive_content, name="ClientThread")
            self.thread.start()

        request = Request(self.context, stream_id)
        self.requests[stream_id] = request
        return request

    # def receivecontent(self, expected_content, unused_timeout, test_output):
    def receive_content(self):
        """
        TODO(Piyush): Add description
        """

        while True:
            data = None
            try:
                data = self.tls_connection.recv(65535)
                logging.debug("\nReceived server raw data : " + str(data))
            except socket.error as err:
                logging.info(err)
                return
            if not data:
                logging.info("no response from server")
                # Client conn is closed
                return
            events = self.http2_connection.receive_data(data)
            for event in events:
                logging.info("CLient Event fired: " + event.__class__.__name__)
                self.handle_event(event)
                # if isinstance(event, h2.events.StreamEnded):
                #     return

    def handle_event(self, event):
        """
        handle_events processes each event and then stores them,
        so that they can be handled async when test specifies it
        """
        request = None
        response = Response(event)
        try:
            stream_id = event.stream_id

            if stream_id in self.requests:
                request = self.requests[stream_id]

        except AttributeError:
            # No stream id indicates event not related to particular stream
            # event_list = self.events
            request = None

        if request:
            request.add_received_events(response, event)
        else:
            event_name = event.__class__.__name__
            self.event_received(event_name, response, lambda event, data: True,
                                event)

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
            pass
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

    def stop(self):
        """
        Stop/Kill client
        """
        self.http2_connection.close_connection()
        self.tls_connection.close()
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
    client.request("http://localhost:8080")


if __name__ == "__main__":
    main()
