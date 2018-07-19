"""A test suite for polyglot-server implementations.

Although the test suite is written in Python, it interacts with the server only
through the standard sockets interface, and thus it can test a server written in
any language.

The test suite should be run against a server with a blank database and file
directory.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: July 2018
"""

import socket

def assert_success(client, msg):
    assert_response(client, msg, b'success\0')

def assert_error(client, msg):
    assert_response(client, msg, b'error\0')

def assert_response(client, msg, response):
    client.send(msg)
    data = client.recv(1024)
    assert data == response

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as alice, \
     socket.socket(socket.AF_INET, socket.SOCK_STREAM) as bob, \
     socket.socket(socket.AF_INET, socket.SOCK_STREAM) as charlotte:

    alice.connect( (socket.gethostbyname('localhost'), 8888) )
    bob.connect( (socket.gethostbyname('localhost'), 8888) )
    charlotte.connect( (socket.gethostbyname('localhost'), 8888) )

    # Register the three users.
    assert_success(alice, b'register alice pwd\0')
    assert_success(bob, b'register bob 012345\0')
    assert_success(charlotte, b'register charlotte DHJ414naQ@JNfa\0')

    # Make sure their inboxes are empty.
    assert_response(alice, b'checkinbox\0', b'inbox\0')
    assert_response(bob, b'checkinbox\0', b'inbox\0')
    assert_response(charlotte, b'checkinbox\0', b'inbox\0')

print('All tests passed!')
