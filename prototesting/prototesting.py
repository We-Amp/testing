#!/usr/bin/python -tt

""" Entry point
"""
import logging
from os import listdir
from os.path import dirname, isfile, join, realpath, isdir
import sys

from jsonparser import jsonparser

logging.basicConfig(level=logging.INFO,
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
            test_unit.print_output()


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

    for testfilespath in files:
        if isdir(testfilespath):
            testfiles = [join(testfilespath, file) for file in listdir(
                testfilespath) if isfile(join(testfilespath, file))]
            for file in testfiles:
                run_test(file)
        else:
            run_test(testfilespath)

if __name__ == "__main__":
    main()
