# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='protocol-testing',
    version='0.1.0',
    description='Protocol testing framework',
    long_description=readme,
    url='https://github.com/We-Amp/testing',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
