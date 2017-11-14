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
        parallel_threads = []
        for cmds in cmdslist:
            if "name" in cmds[0]:
                name = cmds[0]["name"]
            else:
                name = "parallel"
            thread = threading.Thread(
                target=self.parser, kwargs=dict(cmds=cmds), name=name)
            logging.info("starting thread: " + name)
            thread.start()
            parallel_threads.append(thread)

        for thread in parallel_threads:
            logging.info("Joining on thread: " + str(thread.getName()))
            thread.join()
        logging.info("coming out of parallel")

    def handle_waitfor(self, index, cmd, cmds, waitfor_events):
        """
            Handle waitfor command
        """
        obj = getattr(self, cmd["event"].split(".")[0])
        event_name = cmd["event"].split(".")[1]
        timeout = int(cmd.get("timeout", 20))
        logging.info("timeout is " + str(timeout))
        registerforevent = getattr(obj, event_name)
        waitfor_event = (threading.Event(), timeout)
        registerforevent(waitfor_event[0], self, cmd["name"], cmd["data"])
        logging.debug("waitfor setting event, current thread:" +
                      str(threading.get_ident()))
        waitfor_events.append(waitfor_event)

        # check if next cmd is also waitfor
        cmd = cmds[index + 1]
        if "action" in cmd:
            if cmd["action"] == "waitfor":
                waitfor_events = self.handle_waitfor(
                    index + 1, cmd, cmds, waitfor_events)
        return waitfor_events

    def handle_execute(self, cmd):
        """Execute a string given in "execute", can use the objects defined in test """
        exec(cmd["execute"], self.__dict__)

    def handle_expectation(self, cmd):
        """
        Handle Expectations
        """
        args = []
        output = {"Description": cmd["Description"]}
        expect = cmd["value"].split(".")
        invalid_action_items = [
            "action", "value", "Description"]
        mod = getattr(self, expect[0])
        if len(expect) > 2:
            args.append(expect[2])
            logging.info(args)
            result = getattr(mod, expect[1])(*args)
            expectation = {"Description": cmd["Description"]}
            logging.info(output)
            if str(result) == str(cmd["expected"]):
                output["status"] = "passed"
            else:
                output["status"] = "failed"
                output["expected"] = str(cmd["expected"])
                output["got"] = str(result)

            self.expectations.append(output)
        else:
            for action_item in cmd:
                if action_item not in invalid_action_items:
                    args.append(cmd[action_item])
            args.append(output)
            expectation = getattr(mod, expect[1])(*args)
            logging.info(expectation)
            self.expectations.append(expectation)

    def parser(self, cmds):
        """
            Tests json parser
        """
        lock = threading.RLock()
        with lock:

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
                        logging.debug(
                            "waitfor action, current thread:" + str(threading.get_ident()))
                        waitfor_events = []
                        waitfor_events = self.handle_waitfor(
                            index, cmd, cmds, waitfor_events)
                        for event, timeout in waitfor_events:
                            logging.info("Waiting on event: " +
                                         cmd["name"] + "timeout: " + str(timeout))
                            success = event.wait(timeout)

                            if not success:
                                # Returning as something timed out
                                # :TODO(piyush) Add graceful error handling
                                return

                            logging.debug("Event received: " + cmd["name"])

                    elif cmd["action"] == "execute":
                        self.handle_execute(cmd)

                    elif cmd["action"] == "expect":
                        self.handle_expectation(cmd)

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
                        logging.debug(dir(mod))

                        # :TODO (Rakesh) Possibly call this function with parameter name and value
                        response = getattr(mod, action[1])(*args)

                        if action_response:
                            setattr(self, action_response, response)

    def parse(self, json_text):
        """Parse test cases defined in json"""
        try:
            json_data = json.loads(json_text)

        except ValueError:
            logging.error("Test cases are invalid")
            return

        self.parser(json_data)

        for thread in self.threads:
            thread.join()

    def print_output(self):
        """
            Print Test output
        """
        # print output
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
