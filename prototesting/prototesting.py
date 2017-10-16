#!/usr/bin/python -tt

""" Entry point
"""
from jsonparser import jsonparser


def main():
    """
    Entry point function to start execution of tests
    """
    # :TODO:(Rakesh)
    # 1. Pull this from file.
    # 2. Validate json
    # 3. Proper error handling

    jsonparser.parse(
        """[
            {"TestName":"Client - Server", "Description": "This test creates an client and server"},
            {"create":"http2.server","name":"h2s"},
            {"action":"h2s.start"},
            {"create":"http2.client","name":"h2c"},
            {"action":"h2c.request", "url":"https://localhost:8080/test1.html", "name": "request1"},
            {"expect":"request1.receivecontent","expected":"200","timeout":100, "Description": "Received Headers"},
            {"action":"h2s.kill"}
        ]""")


if __name__ == "__main__":
    main()
