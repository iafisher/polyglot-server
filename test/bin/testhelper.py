"""A helper module for the polyglot-server test suite.

Although the module is written in Python, it interacts with the server only
through the standard sockets interface, and thus it can test a server written
in any language.

The test suite consists of a collection of test scripts in the test-scripts
directory. The test scripts are in the following format:

    >>> login alice pwd123
    success

which tells the test runner (this module) to send b'login alice pwd123\r\n'
to the server and expect the response b'success\r\n'. The requests and
responses must be in UTF-8. You can also write them in Python bytestring format
to encode arbitrary binary data:

    >>> b"upload sample.bin 20 Non UTF-8 byte: \xFF\r\n"

Blank lines and lines beginning with '#' are ignored. You can specify multiple
simultaneous connections by prefixing '>>>' with a name:

    alice >>> login alice pwd
    success

    bob >>> login bob pwd
    success

A timestamp can be matched with the literal string '<timestamp>', e.g.:

   alice >>> recv bob
   message <timestamp> bob alice Hello!

Each test script runs with a clean database and file directory.

To run the test suite, use the testclient script in the project's root
directory, which arranges for the server to be running with a test database and
file folder.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: July 2018
"""

import ast
import re
import socket
import sys
import time
from collections import defaultdict


def assert_recv(client, expected, fpath, lineno):
    loc = '{}:{}'.format(fpath, lineno)
    try:
        data = client.recv(1024)
    except BlockingIOError:
        sys.stderr.write('Error, {}: expected {!r}, got nothing\n'.format(
            loc, expected))
        return False
    else:
        if not equivalent(expected, data):
            sys.stderr.write('Error, {}: expected {!r}, got {!r}\n'.format(
                loc, expected, data))
            return False
    return True


line_regex = re.compile(r'([A-Za-z0-9_]*)\s*>>>\s*(.*)')
def do_test_script(fpath):
    clients = defaultdict(new_client)
    with open(fpath, 'r') as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            m = line_regex.match(line)
            if m:
                user, line = m.groups()
                if not user:
                    user = 'default'

                client = clients[user]
                line = line_to_bytes(line)
                client.send(line)
            else:
                if not assert_recv(client, line_to_bytes(line), fpath, lineno):
                    break

    time.sleep(0.1)
    for key, client in clients.items():
        try:
            data = client.recv(1024, socket.MSG_DONTWAIT)
        except BlockingIOError:
            pass
        else:
            sys.stderr.write("Error, {}: unread data on {}'s socket: {}'\n"
                .format(fpath, key, data))
        client.close()


def new_client():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((socket.gethostbyname('localhost'), 8888))
        return client
    except ConnectionError:
        sys.stderr.write('Error: could not connect to server\n')
        sys.exit(2)


def line_to_bytes(line):
    if line.startswith(("b'", 'b"')):
        return ast.literal_eval(line)
    else:
        return line.encode('utf-8') + b'\r\n'


timestamp_regex = re.compile(rb'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')
def equivalent(expected, got):
    """Return True if the two bytestrings are equivalent, except that the
    sequence b'<timestamp>' in `expected` matches an actul ISO 8601 timestamp
    in `got`.
    """
    index = expected.find(b'<timestamp>')
    if index != -1:
        next_space = got.find(b' ', index)
        if next_space == -1:
            return False
        if not timestamp_regex.match(got[index:next_space]):
            return False
        expected = expected[:index] + expected[index+11:]
        got = got[:index] + got[next_space:]
    return expected == got


if len(sys.argv) != 2:
    sys.stderr.write('Usage: python3 testhelper.py <path to test script>\n')
    sys.exit(1)
else:
    do_test_script(sys.argv[1])
