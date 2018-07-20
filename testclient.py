#!/usr/bin/env python3
"""A test suite for polyglot-server implementations.

Although the test suite is written in Python, it interacts with the server only
through the standard sockets interface, and thus it can test a server written
in any language.

The test suite should be run against a server with a blank database and file
directory.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: July 2018
"""

import datetime
import socket


def assert_success(client, msg):
    assert_response(client, msg, b'success\0')


def assert_error(client, msg):
    assert_response(client, msg, b'error\0')


def assert_response(client, msg, response):
    client.send(msg)
    data = client.recv(1024)
    assert data == response


def assert_recvd_message(client, from_, to, msg):
    client.send(b'recv ' + from_ + b'\0')
    data = client.recv(1024)
    fields = data.split(b' ', maxsplit=4)
    assert len(fields) == 4
    now = datetime.datetime.utcnow()
    assert fields[0] == b'message'
    then = datetime.datetime.strptime(fields[1], '%Y-%m-%dT%H:%M:%SZ')
    assert abs((now - then).seconds) < 30
    assert fields[1] == from_
    assert fields[2] == to
    assert fields[3] == msg


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as alice, \
     socket.socket(socket.AF_INET, socket.SOCK_STREAM) as bob, \
     socket.socket(socket.AF_INET, socket.SOCK_STREAM) as charlotte:

    alice.connect((socket.gethostbyname('localhost'), 8888))
    bob.connect((socket.gethostbyname('localhost'), 8888))
    charlotte.connect((socket.gethostbyname('localhost'), 8888))

    # Register the three users.
    assert_success(alice, b'register alice pwd\0')
    assert_success(bob, b'register bob 012345\0')
    assert_success(charlotte, b'register charlotte DHJ414naQ@JNfa\0')

    # Make sure their inboxes are empty.
    assert_response(alice, b'checkinbox\0', b'inbox\0')
    assert_response(bob, b'checkinbox\0', b'inbox\0')
    assert_response(charlotte, b'checkinbox\0', b'inbox\0')

    # Make sure there are no files.
    assert_response(alice, b'getfilelist\0', 'filelist\0')

    # Send a message from Alice to Bob.
    now = iso8601()
    assert_success(alice, b'send %s bob Hello!\0' % now)

    # Make sure everyone's inbox is still empty except Bob's.
    assert_response(alice, b'checkinbox\0', b'inbox\0')
    assert_response(bob, b'checkinbox\0', b'inbox alice 1\0')
    assert_response(charlotte, b'checkinbox\0', b'inbox\0')

    # Retrieve the message.
    assert_response(bob, b'recv alice\0', b'message %s alice bob Hello!' % now)
    assert_response(bob, b'checkinbox\0', b'inbox\0')

    # Send a broadcast message and a direct message.
    assert_success(charlotte, b'send * Hi guys!\0')
    assert_success(charlotte, b'send alice Where are you?\0')
    assert_response(alice, b'checkinbox\0', b'inbox charlotte 2\0')
    assert_response(bob, b'checkinbox\0', b'inbox charlotte 1\0')
    assert_response(charlotte, b'checkinbox\0', b'inbox\0')

    # Make sure the oldest message is returned first.
    assert_recvd_message(alice, b'charlotte', b'*', b'Hi guys\0')
    assert_response(alice, b'checkinbox\0', b'inbox charlotte 1\0')
    response = b'message %s charlotte alice Where are you?\0'
    assert_recvd_message(alice, b'charlotte', b'alice', b'Where are you?\0')
    assert_response(alice, b'checkinbox\0', b'inbox\0')

print('All tests passed!')
