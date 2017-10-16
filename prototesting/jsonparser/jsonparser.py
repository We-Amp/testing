#!/usr/bin/python -tt

"""
    JSON Parser which creates the test objects and executes each step
"""
import json
import importlib


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

    def create_module(self, mod_name, name):
        """ Imports module named 'mod_name' and adds a attibute to Test object with 'name'"""
        mod = Module(mod_name, name)
        setattr(self, name, mod.instance)


def parse(json_text):
    """Parse test cases defined in json"""
    test_obj = TestUnit()

    json_data = json.loads(json_text)
    for cmd in json_data:
        print(cmd)
        if "create" in cmd:
            test_obj.create_module(cmd["create"], cmd["name"])
        # if "config" in cmd:
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
            print(dir(mod))
            response = getattr(mod, action[1])(*args)
            setattr(test_obj, action_response, response)
        if "expect" in cmd:
            args = []
            expect = cmd["expect"].split(".")
            for action_item in cmd:
                if action_item != "expect":
                    args.append(cmd[action_item])
            mod = getattr(test_obj, expect[0])
            getattr(mod, action[1])(*args)


if __name__ == "__main__":
    pass
