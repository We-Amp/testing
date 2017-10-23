#!/usr/bin/python -tt

""" Entry point
"""
import logging

from os import listdir
from os.path import dirname, isfile, join, realpath
from jsonparser import jsonparser

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s\n')


def main():
    """
    Entry point function to start execution of tests
    """
    # :TODO (Rakesh)
    # 1. Pull this from file.
    # 2. Validate json
    # 3. Proper error handling
    # 4. Enable disable printing of data

    testfilespath = join(dirname(realpath(__file__)), "../jsontests")

    testfiles = [join(testfilespath, f) for f in listdir(
        testfilespath) if isfile(join(testfilespath, f))]

    for file in testfiles:
        if file.lower().endswith('.json'):
            with open(file) as f:
                fdata = f.read()
                jsonparser.parse(fdata)


if __name__ == "__main__":
    main()
