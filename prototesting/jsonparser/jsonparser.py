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
        self.create_module(mod_name)

        if name:
            self.set_name(name)
        else:
            self.set_name(mod_name)

    def set_name(self, name):
        """ name of the module specified by "name" key"""
        self.name = name

    def create_module(self, mod_name):
        """ imports module spcified in "create" key"""
        self.mod = importlib.import_module(mod_name)


class TestObject:
    """ Container object which holds all modules imported using 'create' key """

    def create_module(self, mod_name, name):
        """ Imports module named 'mod_name' and adds a attibute to Test object with 'name'"""
        mod = Module(mod_name, name)
        setattr(self, name, mod)


def parse(json_text):
    """Parse test cases defined in json"""
    test_obj = TestObject()

    json_data = json.loads(json_text)
    for cmd in json_data:
        print(cmd)
        if "create" in cmd:
            test_obj.create_module(cmd["create"], cmd["name"])
        # if "config" in cmd:
        if "action" in cmd:
            action = cmd["action"].split(".")
            mod = getattr(test_obj, action[0]).mod
            print(dir(mod))
            getattr(mod, action[1])()


if __name__ == "__main__":
    pass
