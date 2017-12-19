#!/usr/bin/python -tt
""" Entry point
"""
import logging
import sys
from os import listdir
from os.path import dirname, isdir, isfile, join, realpath

from jsonparser import jsonparser

logging.basicConfig(
    level=logging.INFO,
    format='\n%(threadName)s:'
    '%(filename)s:'
    '%(lineno)d:'
    '%(levelname)s:'
    '%(funcName)s(): '
    '%(message)s\n')


def run_test(filepath):
    if filepath.lower().endswith('.json'):
        with open(filepath) as file:
            fdata = file.read()
            test_unit = jsonparser.TestUnit(fdata)
            return test_unit


def main():
    """
    Entry point function to start execution of tests
    """
    # :TODO (Rakesh)
    # 1. Pull this from file.
    # 2. Validate json
    # 3. Proper error handling
    # 4. Logging with configurable levels

    files = [join(dirname(realpath(__file__)), "../jsontests")]
    if len(sys.argv) > 1:
        files = sys.argv[1:]

    test_unit_list = []
    for testfilespath in files:
        if isdir(testfilespath):
            testfiles = [
                join(testfilespath, file) for file in listdir(testfilespath)
                if isfile(join(testfilespath, file))
            ]
            for file in testfiles:
                test_unit = run_test(file)
                test_unit_list.append(test_unit)
        else:
            test_unit = run_test(testfilespath)
            test_unit_list.append(test_unit)

    print("=" * 50)
    print(" " * 15, "Test Ouptut")
    print("=" * 50)
    for test_unit in test_unit_list:
        print("=" * 50)
        test_unit.print_output()
        print("=" * 50)

    print("=" * 50)
    print(" " * 15, "Test End")
    print("=" * 50)


if __name__ == "__main__":
    main()
