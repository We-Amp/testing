"""
    JSON Parser which creates the test objects and executes each step
"""

#!/usr/bin/python -tt

TEST_JSON = """[
  {"create":"ats_server","name":"ats","config":""},
  {"create":"http2server","name":"h2s","listen":8080},
  {"create":"http2client","name":"h2c"},
  {
    "parallel":[
        [
            {"action":"h2c.request", "url":"https://localhost:8080/test1.html","name":"request1"},
            {"expect":"request1.receivecontent","expected":"<headers>","timeout":100},
            {"expect":"request1.nocontent","timeout":900},
            {"expect":"request1.receivecontent","expected":"<content>","timeout":100}
        ],
        [
            {"expect":"h2s.request", "request":"/test1.htm","name":"request1"},
            {"action":"request1.sendcontent","value":"<headers>"},
            {"action":"sleep","timeout":1000},
            {"action":"request1.sendcontent","value":"<content>"}
        ]
    ]
  }
]"""

import json
import importlib
import sys
import os

class Module:
    def __init__(self, modName, name):
        # actual module
        self.create_module(modName)
        self.mod = None
        # module with alias name
        if name:
            self.set_name(name)
        else:
            self.mod = self._mod

    def set_name(self, name):
        if self._mod:
            self.mod = {name: self._mod}[name]

    def create_module(self, modName):
        self._mod = importlib.import_module(modName)
        print(self._mod)


class TestObject:
    def create_module(self, modName, name):
        mod = Module(modName, name)
        setattr(self, name, mod)

def parse(json_text):
    test_obj = TestObject()
    json_data = json.loads(json_text)
    for cmd in json_data:
        print(cmd)
        if "create" in cmd:
            test_obj.create_module(cmd["create"], cmd["name"])
        #if "config" in cmd:
        if "action" in cmd:
            action = cmd["action"]
            mod = getattr(test_obj, action.split(".")[0]).mod
            getattr(mod,action.split(".")[1])()

if __name__ == "__main__":
    # adding path manually here, need to do it at better place

    sys.path.append('./prototesting/h2c')

    print(sys.path)

    parse("""[
                {"create":"h2c","name":"h2client"},
                {"action":"h2client.main"}
            ]""")
