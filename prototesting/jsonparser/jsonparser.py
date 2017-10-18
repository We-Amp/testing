#!/usr/bin/python -tt

"""
    JSON Parser which creates the test objects and executes each step
"""
import importlib
import json
import logging


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

    def __init__(self):
        self.name = None
        self.description = None
        self.expectations = []

    def create_module(self, mod_name, name):
        """ Imports module named 'mod_name' and adds a attibute to Test object with 'name'"""
        mod = Module(mod_name, name)
        setattr(self, name, mod.instance)


def parse(json_text):
    """Parse test cases defined in json"""
    logger = logging.getLogger(__name__)
    test_obj = TestUnit()

    json_data = json.loads(json_text)
    for cmd in json_data:
        logger.debug(cmd)
        if "TestName" in cmd:
            test_obj.name = cmd["TestName"]
            test_obj.description = cmd["Description"]

        if "create" in cmd:
            test_obj.create_module(cmd["create"], cmd["name"])
            if "config" in cmd:
                mod = getattr(test_obj, cmd["name"])
                getattr(mod, "config")(cmd["config"])

        if "action" in cmd:
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

            mod = getattr(test_obj, action[0])
            logger.debug(dir(mod))
            response = getattr(mod, action[1])(*args)

            if action_response:
                setattr(test_obj, action_response, response)

        if "expect" in cmd:
            args = []
            output = {"Description": cmd["Description"]}
            expect = cmd["expect"].split(".")
            for action_item in cmd:
                if action_item != "expect" and action_item != "Description":
                    args.append(cmd[action_item])
            args.append(output)
            mod = getattr(test_obj, expect[0])
            expectation = getattr(mod, expect[1])(*args)
            test_obj.expectations.append(expectation)

    print("="*25)
    print("Test Ouptut")
    print("="*25)
    print("Test: ", test_obj.name)
    print("Test Description:", test_obj.description)
    print("Expectations:")
    for expectation in test_obj.expectations:
        if expectation:
            for expect, output in expectation.items():
                print("\t" + expect + ": " + output)
        else:
            print("Something went wrong")


if __name__ == "__main__":
    pass
