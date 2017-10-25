#!/usr/bin/python -tt

"""
    JSON Parser which creates the test objects and executes each step
"""
import importlib
import json
import logging
import threading

class Module:
    """
        Object corresponds to create statement in json
    """

    def __init__(self, mod_name, name):
        self.module = self.import_module(mod_name)
        self.instance = self.module.create()

        if name:
            self.name = name
        else:
            self.name = mod_name

    def set_name(self, name):
        """ name of the module specified by "name" key"""
        self.name = name

    def import_module(self, mod_name):
        """ imports module spcified in "create" key"""
        return importlib.import_module(mod_name)


class TestUnit:
    """ Container object which holds all modules imported using 'create' key """

    def __init__(self, json_text):
        self.name = None
        self.description = None
        self.expectations = []
        self.threads = []
        self.parse(json_text)

    def create_module(self, mod_name, name):
        """ Imports module named 'mod_name' and adds a attibute to Test object with 'name'"""
        mod = Module(mod_name, name)
        setattr(self, name, mod.instance)

    def handle_parallel(self, cmdslist):
        """
            Handles parallel execution of tests/cmds
        """
        for cmds in cmdslist:
            thread = threading.Thread(target=self.parser, kwargs=dict(cmds=cmds))
            thread.start()
            self.threads.append(thread)

    def handle_waitfor(self, index, cmd, cmds, waitfor_events):
        """
            Handle waitfor command
        """
        obj = getattr(self, cmd["event"].split(".")[0])
        event_name = cmd["event"].split(".")[1]
        registerforevent = getattr(obj, event_name)
        waitfor_event = threading.Event()
        registerforevent(waitfor_event, self, cmd["name"])
        logger = logging.getLogger(__name__)
        logger.debug("waitfor setting event, current thread:" + str(threading.get_ident()))
        waitfor_events.append(waitfor_event)

        # check if next cmd is also waitfor
        cmd = cmds[index + 1]
        if "action" in cmd:
            if cmd["action"] == "waitfor":
                waitfor_events = self.handle_waitfor(index, cmd, cmds, waitfor_events)
        return waitfor_events

    def parser(self, cmds):
        """
            Tests json parser
        """
        lock = threading.RLock()
        with lock:
            logger = logging.getLogger(__name__)

            for index, cmd in enumerate(cmds):
                print(cmd)
                if "TestName" in cmd:
                    self.name = cmd["TestName"]
                    self.description = cmd["Description"]

                if "create" in cmd:
                    self.create_module(cmd["create"], cmd["name"])
                    if "config" in cmd:
                        mod = getattr(self, cmd["name"])
                        getattr(mod, "config")(cmd["config"])

                if "action" in cmd:
                    if cmd["action"] == "parallel":
                        self.handle_parallel(cmd["list"])
                    elif cmd["action"] == "waitfor":
                        logger.debug("waitfor action, current thread:" + str(threading.get_ident()))
                        waitfor_events = []
                        waitfor_events = self.handle_waitfor(index, cmd, cmds, waitfor_events)
                        for event in waitfor_events:
                            logger.debug("Waiting on event: " + cmd["name"])
                            event.wait()
                            logger.debug("Event received: " + cmd["name"])
                    else:
                        action = None
                        action_response = None
                        args = []
                        for action_item in cmd:
                            if action_item == "action":
                                action = cmd["action"].split(".")
                            elif action_item == "name":
                                action_response = cmd["name"]
                            else:
                                args.append(cmd[action_item])

                        mod = getattr(self, action[0])
                        logger.debug(dir(mod))

                        response = getattr(mod, action[1])(*args)

                        if action_response:
                            setattr(self, action_response, response)

                if "expect" in cmd:
                    args = []
                    output = {"Description": cmd["Description"]}
                    expect = cmd["expect"].split(".")
                    for action_item in cmd:
                        if action_item != "expect" and action_item != "Description":
                            args.append(cmd[action_item])
                    args.append(output)
                    mod = getattr(self, expect[0])
                    expectation = getattr(mod, expect[1])(*args)
                    self.expectations.append(expectation)

    def parse(self, json_text):
        """Parse test cases defined in json"""

        json_data = json.loads(json_text)
        self.parser(json_data)

        for thread in self.threads:
            thread.join()

    def print_output(self):
        """
            Print Test output
        """
        # print output
        print("="*25)
        print("Test Ouptut")
        print("="*25)
        print("Test: ", self.name)
        print("Test Description:", self.description)
        print("Expectations:")
        for expectation in self.expectations:
            if expectation:
                for expect, output in expectation.items():
                    print("\t" + expect + ": " + output)
            else:
                print("Something went wrong")


if __name__ == "__main__":
    pass
