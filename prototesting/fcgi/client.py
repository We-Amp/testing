"""
Client for handling fcgi requests
"""
import logging
import socket
from urllib.parse import urlparse

import requests

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

    def __init__(self, event):
        Response.__init__(self)

        self.type = event.__class__.__name__

        self.data = event.text
        self.headers = event.headers
        self.headers[":status"] = str(event.status_code)

    def handle_expectation(self, value, expected, expectation):
        if "headers" in value[0]:
            # type is header
            try:
                got = self.headers[value[1]]

                if len(value) > 2:
                    #extra operation needs to be performed on the value of headers
                    got = getattr(got, value[2])

                super().match_expectation(expected, got, expectation)
            except Exception as err:
                expectation["status"] = "failed"
                expectation["expected"] = str(expected)
                expectation["reason"] = "Got Exception " + str(err)

        else:
            # call parent function
            super().handle_expectation(value[0], expected, expectation)


class Client(EventProcessor):
    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.conn = None

    def request(self, url):
        # :TODO(Piyush) Remove this if not required
        return self

    def get(self, url, headers=None):
        try:
            # :TODO(Piyush) Set a reasonable timeout value
            resp = requests.get(url, headers=headers, timeout=5)
            # :TODO(Piyush) Add event to signify reception of event
            return FCGIResponse(resp)
        except requests.exceptions.ConnectionError as err:
            self.context.handle_failure("Get " + url,
                                        "Got Exception " + str(err))
            return Response(str(err))

    def post(self, url, headers=None, data=""):
        try:
            # :TODO(Piyush) Set a reasonable timeout value
            resp = requests.post(url, headers=headers, data=data, timeout=5)
            # :TODO(Piyush) Add event to signify reception of event
            return FCGIResponse(resp)
        except requests.exceptions.ConnectionError as err:
            self.context.handle_failure("Post " + url,
                                        "Got Exception " + str(err))
            return Response(str(err))


def create(context):
    """
    Create() => client
    Returns the Client object
    """
    return Client(context)


def main():
    """Standalone client instance"""
    client = Client()
    client.request("http://localhost:9080/abc.php")


if __name__ == "__main__":
    main()
