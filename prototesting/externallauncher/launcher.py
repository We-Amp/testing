"""
Launch external process with configutation
"""

import io
import logging
import subprocess
import threading
from os.path import join

try:
    from event import EventProcessor
except ImportError:
    import os
    import sys
    # add prototesting folder to sys path to sort out import error
    # this is assuming that the script is called from base of git repo
    sys.path.append(os.path.join(os.getcwd(), "prototesting"))
    from event import EventProcessor


class Launcher(EventProcessor):
    """
    Launcher class launches external application with configuration and stores its output
    """

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.output = None
        self.buffer = io.StringIO()

    def launch(self, cmd, arguments=None, path=None, root_access=False):
        """
        Launch the current command and store its output
        """
        # Create args list for subprocess run
        args_list = []
        if root_access:
            if "sudo" not in cmd:
                args_list.append("sudo")

        if path:
            cmd = join(path, cmd)
            logging.debug(cmd)

        args_list.append(cmd)

        # Config should be list of relvant switches and options
        if arguments:
            args_list += arguments

        logging.debug(args_list)

        self.output = subprocess.Popen(
            args_list,
            close_fds=True,
            stdout=subprocess.PIPE,
        )
        self.get_output()
        # :TODO(Piyush) Handle wait for here based on output status and data
        self.event_received("ProcessStarted", self, lambda event, data: True,
                            None)

        return self

    def read_output(self, pipe, funcs):
        """
        Iterate over stdout
        """
        for line in iter(pipe.readline, b''):
            funcs(line.decode())
        pipe.close()

    def get_output(self):
        """
        Read Output stream as the output is generated on stdout
        """
        stdout_thread = threading.Thread(
            target=self.read_output,
            args=(self.output.stdout, self.buffer.write))

        # python process won't hang if the main thread is exited
        # thread dies with the program
        stdout_thread.daemon = True
        stdout_thread.start()

        self.output.wait()

        stdout_thread.join()

    def wait_for_keyword(self, keyword):
        """
        Check if required keyword is found in buffer
        """
        while True:
            if keyword in self.buffer.getvalue():
                logging.debug("found: " + keyword)
                self.buffer = io.StringIO()
                self.event_received("_ScanFor", keyword,
                                    lambda event, data: True, None)
                return

    def scan_for(self, keyword=None):
        """
        Scan command output for particular string
        """
        # Create a new event and pass it to a new thread to wait for required
        # output or wait for timeout

        # :TODO(Piyush): Move time out to global config
        timeout = 20
        wait_for_event = threading.Event()
        self.register_event("_ScanFor", wait_for_event, "_ScanFor", keyword)

        wait_for_thread = threading.Thread(
            target=self.wait_for_keyword, args=(keyword, ))

        wait_for_thread.start()
        success = wait_for_event.wait(timeout=timeout)
        if not success:
            logging.error("Event Timeout, Not found keyword : " + keyword)
            logging.error(self.buffer.getvalue())
            output = {"Description": "Event timeout"}
            output["name"] = "ScanFor: " + keyword
            output["status"] = "timedout"
            self.context.expectations.append(output)

    def kill(self):
        """
        Kill the open process
        """
        self.output.kill()
        self.buffer.close()


def create(context=None):
    """
    Create() => launcher
    Returns the Launcher object
    """
    return Launcher(context)
