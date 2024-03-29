#!/usr/bin/python -tt
"""
    JSON Parser which creates the test objects and executes each step
"""
import importlib
import json
import logging
import threading


class TestUnit:
    """ Container object which holds all modules imported using 'create' key """

    def __init__(self, file_path, json_text):
        self.name = None
        self.description = None
        self.file_path = file_path
        self.expectations = []
        self.threads = []
        self.registered_events = {}
        self.received_events = {}
        self.parse(json_text)

    def create_module(self, mod_name, name):
        """ Imports module named 'mod_name' and adds a attibute to Test object with 'name'"""
        module = importlib.import_module(mod_name)
        instance = module.create(self)
        setattr(self, name, instance)

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

    def handle_waitfor(self, cmd):
        """
            Handle waitfor command
        """
        event_name = cmd["event"].split(".")[1]
        timeout = int(cmd.get("timeout", 20))
        logging.debug("Setting timeout: " + str(timeout))
        waitfor_event = (threading.Event(), timeout)
        self.register_event(event_name, waitfor_event[0], cmd["name"],
                            cmd["data"])
        logging.debug("waitfor setting event, current thread:" +
                      str(threading.get_ident()))

        return waitfor_event

    def handle_execute(self, cmd):
        """Execute a string given in "execute", can use the objects defined in test """
        try:
            exec(cmd["execute"], self.__dict__)
        except Exception as err:
            output = {"Description": cmd["execute"]}
            output["status"] = "failed"
            output["reason"] = "Got Exception " + str(err)
            self.expectations.append(output)

    def handle_expectation(self, cmd):
        """
        Handle Expectations
        """
        output = {"Description": cmd["Description"]}
        expect = cmd["value"].split(".")
        mod = getattr(self, expect[0])
        mod.handle_expectation(expect[1:], cmd["expected"], output)
        self.expectations.append(output)

    def handle_timeout(self, name, timeout):
        """
        On timeout of any operation add entry in expectations to be printed on exit
        """
        output = {"Description": "Event timeout"}
        output["name"] = name
        output["time"] = str(timeout)
        output["status"] = "failed"
        self.expectations.append(output)

    def handle_failure(self, name, reason):
        """
        On failure of any operation add entry in expectations to be printed on exit
        """
        output = {"Description": "Event Failure"}
        output["name"] = name
        output["reason"] = str(reason)
        output["status"] = "failed"
        self.expectations.append(output)

    def parser(self, cmds):
        """
            Tests json parser
        """
        lock = threading.RLock()
        with lock:

            for unused_index, cmd in enumerate(cmds):
                print(cmd)
                if "TestName" in cmd:
                    self.name = cmd["TestName"]
                    self.description = cmd["Description"]

                if "create" in cmd:
                    self.create_module(cmd["create"], cmd["name"])
                    if "config" in cmd:
                        mod = getattr(self, cmd["name"])
                        getattr(mod, "config")(config=cmd["config"])

                if "action" in cmd:
                    if cmd["action"] == "parallel":
                        self.handle_parallel(cmd["list"])

                    elif cmd["action"] == "waitfor":
                        logging.debug("waitfor action, current thread:" +
                                      str(threading.get_ident()))
                        waitfor_event = self.handle_waitfor(cmd)
                        event, timeout = waitfor_event
                        logging.info("Waiting on event: " + cmd["name"] +
                                     ", will timeout in : " + str(timeout))
                        success = event.wait(timeout)

                        if not success:
                            logging.debug("Event timedout: " + cmd["name"])
                            self.handle_timeout(cmd["name"], timeout)
                        else:
                            logging.debug("Event received: " + cmd["name"])

                    elif cmd["action"] == "execute":
                        self.handle_execute(cmd)

                    elif cmd["action"] == "expect":
                        self.handle_expectation(cmd)

                    else:
                        action = None
                        action_response = None
                        args = {}
                        for action_item in cmd:
                            if action_item == "action":
                                action = cmd["action"].split(".")
                            elif action_item == "name":
                                action_response = cmd["name"]
                            else:
                                args[action_item] = cmd[action_item]

                        mod = getattr(self, action[0])
                        logging.debug(dir(mod))

                        # :TODO (Rakesh) Possibly call this function with parameter name and value
                        response = getattr(mod, action[1])(**args)

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

        default_timeout = 20

        for thread in self.threads:
            thread.join(default_timeout)

            if thread.is_alive():
                # thread is still alive after time out, add failure status for that thread
                self.handle_timeout(thread.name, default_timeout)

    def register_event(self, waitfor_event_name, wait_event, name, data):
        """
        Register event,mostly called within parser
        "waitfor_event_name" is the event name for eg. RequestReceived
        "wait_event" is the threading event
        "name" is name of the object returned with the event
        "data" is data used to match the event with actual object
        """

        if waitfor_event_name in self.received_events:
            for event_data in self.received_events[waitfor_event_name]:
                response, event, compare_func = event_data
                if compare_func(event, data):
                    setattr(self, name, response)
                    wait_event.set()
                    self.received_events[waitfor_event_name].remove(event_data)
                    return

        if waitfor_event_name not in self.registered_events:
            self.registered_events[waitfor_event_name] = []
        self.registered_events[waitfor_event_name].append((wait_event, name,
                                                           data))

    def event_received(self, event_name, response, compare_func, event):
        """
        Called from modules when event is received
        """
        if event_name in self.registered_events:
            for event_data in self.registered_events[event_name]:
                wait_event, name, data = event_data
                if compare_func(event, data):
                    setattr(self, name, response)
                    wait_event.set()
                    self.registered_events[event_name].remove(event_data)
                    return

        if event_name not in self.received_events:
            self.received_events[event_name] = []
        self.received_events[event_name].append((response, event,
                                                 compare_func))

    def print_output(self):
        """
            Print Test output
        """
        # print output
        print("File Name: ", self.file_path)
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
