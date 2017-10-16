#!/usr/bin/python -tt

""" Entry point
"""
from jsonparser import jsonparser


def main():
    """
    Entry point function to start execution of tests
    """
    jsonparser.parse(
        """[
            {"create":"http2.server","name":"h2s"},
            {"action":"h2s.main"},
            {"create":"http2.client","name":"h2c"},
            {"action":"h2c.main"},
            {"action":"h2c.request", "url":"https://localhost:8080/test1.html", "name": "request1"},
            {"expect":"request1.receivecontent","expected":"<headers>","timeout":100},
            {"action":"h2s.kill"},
        ]""")


if __name__ == "__main__":
    main()
