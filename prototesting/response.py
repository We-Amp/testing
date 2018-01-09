"""
Basic response object
"""
import re


class Response:
    """
  Response class does the handling of the expectations.
  Subclasses implements the handle_expectation method which will match
  expectation and return whether it matched or not
  Response to any event should be subclass of this class
  """

    def __init__(self, data=""):
        self.data = data

    def handle_expectation(self, value, expected, expectation):
        """
        Sublclasses will implement this function and match the expectations
        """
        try:
            got = getattr(self, value)
            self.match_expectation(expected, got, expectation)
        except Exception as err:
            # :TODO(Piyush): Move this to a function so that subclasses can handle this cleanly
            expectation["status"] = "failed"
            expectation["expected"] = str(expected)
            expectation["value"] = str(value)
            expectation["reason"] = "Got Exception " + str(err)

    def match_expectation(self, expected, got, expectation):
        """
        Match and Fill the expectation dict
        """
        match = re.search(str(expected), str(got))
        # :TODO(Piyush): return expectation object here
        if match:
            expectation["status"] = "passed"
        else:
            expectation["status"] = "failed"
            expectation["expected"] = str(expected)
            expectation["got"] = str(got)
