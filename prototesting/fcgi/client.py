"""
Client for handling fcgi requests
"""
import logging
from urllib.parse import urlparse

from hyper import HTTPConnection

from Events import EventProcessor


class Response:
    """
    Response holds all data needed to verify the expectations of test
    """

    def __init__(self, event):
        self.type = event.__class__.__name__

        self.received_data = event.read()
        self.headers = event.headers
        self.headers[":status"] = str(event.status)

    def response_headers(self, field):
        logging.info(self.headers)
        logging.info(self.received_data)

        if field in self.headers:
            return self.headers[field][0].decode()

        return None

    def data(self):
        return self.received_data


class Client(EventProcessor):
    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.conn = None

    def request(self, url):
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        secure = True if "https" in parsed_url.scheme else False

        port = '80'
        if ':' in host:
            # host contains a port so we will use that port
            url_location = host.split(":")
            host = url_location[0]
            port = url_location[1]

        logging.info("host is {} and port is {}".format(host, port))

        self.conn = HTTPConnection(host, port, secure=secure)
        return self

    def get(self, url):
        parsed_url = urlparse(url)
        logging.info(parsed_url.path)
        self.conn.request('GET', parsed_url.path)
        resp = self.conn.get_response()
        logging.info(dir(resp))
        # :TODO(Piyush) Add event to signify reception of event
        return Response(resp)


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
