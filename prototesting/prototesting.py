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
            {"action":"h2c.main"}
        ]""")


if __name__ == "__main__":
    main()
