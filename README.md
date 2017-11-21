# testing
network testing tooling

Steps for Installation
----------------------
- Install Python 3.6
  - Steps for ubuntu < 16.10
    - `sudo add-apt-repository ppa:deadsnakes/ppa`
    - `sudo apt-get update`

  - `sudo apt-get install python3.6`

- Install pip3.6
  - `curl https://bootstrap.pypa.io/get-pip.py | sudo python3.6`

- Install required dependencies
  - `sudo pip3.6 install -r requirements.txt`

- Note :- Openssl version > 1.0.2g required


Steps for running
------------------
  - Run single test
    - `python3.6 prototesting/prototesting.py jsontests/test1.json`

  - Run multiple test
    - `python3.6 prototesting/prototesting.py jsontests/`
