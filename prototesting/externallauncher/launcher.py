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

    def __init__(self,
                 name,
                 config=None,
                 path=None,
                 root_access=False,
                 password=None,
                 context=None):
        EventProcessor.__init__(self, context)
        self.output = None
        self.args_list = []
        self.root_access = root_access
        self.password = None

        # Create args list for subprocess run
        if self.root_access:
            self.password = password
            if "sudo" not in name:
                self.args_list.append("sudo")

        if path:
            self.name = join(path, name)
            logging.info(self.name)
        else:
            self.name = name

        self.args_list.append(self.name)

        # Config should be list of relvant switches and options
        if config:
            self.args_list += config

    def launch(self):
        """
        Launch the current command and store its output
        """
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


def launch(name,
           config=None,
           path=None,
           root_access=False,
           password=None,
           context=None):
    """
    Start the process with given configuration
    """
    launcher = Launcher(name, config, path, root_access, password, context)
    launcher.launch()

    return launcher
