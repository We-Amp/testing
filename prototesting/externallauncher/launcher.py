"""
Launch external process with configutation
"""

import logging
import subprocess
from os.path import join

from Events import EventProcessor


class Launcher(EventProcessor):
    """
    Launcher class launches external application with configuration and stores its output
    """

    def __init__(self, context=None):
        EventProcessor.__init__(self, context)
        self.output = None
        self.args_list = []
        self.root_access = False
        self.password = None
        self.cmd = None

    def launch(self,
               cmd,
               arguments=None,
               path=None,
               root_access=False,
               password=None):
        """
        Launch the current command and store its output
        """
        # Create args list for subprocess run
        self.root_access = root_access
        if self.root_access:
            self.password = password
            if "sudo" not in cmd:
                self.args_list.append("sudo")

        if path:
            self.cmd = join(path, cmd)
            logging.info(self.cmd)
        else:
            self.cmd = cmd

        self.args_list.append(self.cmd)

        # Config should be list of relvant switches and options
        if arguments:
            self.args_list += arguments

        logging.info(self.args_list)

        if self.password:
            self.output = subprocess.Popen(
                self.args_list, stdout=subprocess.PIPE, stdin=subprocess.PIPE)

        else:
            self.output = subprocess.Popen(
                self.args_list, stdout=subprocess.PIPE)

        if self.root_access and self.password:
            self.output.communicate(self.password.encode())

        # :TODO(Piyush) Handle wait for here based on output status and data
        self.event_received("ProcessStarted", self, lambda event, data: True,
                            None)

        return self

    def get_output(self):
        """
        Returns the output stored for given command
        """
        out, unused_err = self.output.communicate(timeout=1)
        print(out.decode())

    def kill(self):
        """
        Kill the open process
        """
        self.output.kill()


def create(context=None):
    """
    Create() => launcher
    Returns the Launcher object
    """
    return Launcher(context)
