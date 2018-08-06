"""A helper module for the polyglot-server test suite.

Although the module is written in Python, it interacts with the server only
through the standard sockets interface, and thus it can test a server written
in any language.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: August 2018
"""
import inspect
import socket
import sys
import time


def ASSERT(cond, msg, *args):
    try:
        assert cond
    except AssertionError:
        lineno = inspect.getframeinfo(inspect.stack()[-1][0]).lineno
        sys.stderr.write(('Error ({}:{}): ' + msg + '\r\n').format(
            __file__, lineno, *args))


def ASSERT_EMPTY(client):
    time.sleep(0.1)
    try:
        data = client.recv(1024, socket.MSG_DONTWAIT)
    except BlockingIOError:
        pass
    else:
        ASSERT(data == b'', 'expected nothing, got {!r}', data)


def A(client, request, *responses):
    client.send(to_bytes(request))
    for response in responses:
        response = to_bytes(response)
        data = client.recv(4096)
        ASSERT(equivalent(response, data), 'expected {!r}, got {!r}', response, data)


def new_client(credentials=None):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((socket.gethostbyname('localhost'), 8888))
    if credentials is not None:
        A(client, b'register ' + to_bytes(credentials), 'success')
    return client


def to_bytes(str_or_bytes):
    if isinstance(str_or_bytes, str):
        return str_or_bytes.encode('utf-8') + b'\r\n'
    else:
        return str_or_bytes


def equivalent(expected, got):
    index = expected.find(b'<timestamp>')
    if index != -1:
        next_space = got.find(b' ', index + 1)
        if next_space == -1:
            next_space = len(got)
        return expected[:index] == got[:index] \
            and equivalent(expected[index+11:], got[next_space:])
    else:
        return expected == got


# REGISTRATION AND LOG-IN
iafisher = new_client()
A(iafisher, 'register iafisher pwd', 'success')
A(iafisher, 'login alice pwd', 'error must not be logged in')
A(iafisher, 'register bob pwd123', 'error must not be logged in')
A(iafisher, 'logout', 'success')
A(iafisher, 'login iafisher not my password', 'error invalid username or password')
A(iafisher, 'login iafisher pwd', 'success')
A(iafisher, 'logout', 'success')
A(iafisher, 'register some_other_user A strong password: 2018', 'success')
A(iafisher, 'logout', 'success')
A(iafisher, 'login iafisher pwd', 'success')


# MESSAGING
alice = new_client('alice pwd')
bob = new_client('bob ajhnb375gjnajvna')
# Inboxes should be empty.
A(alice, 'recv', 'error inbox is empty')
A(iafisher, 'recv', 'error inbox is empty')
A(bob, 'recv', 'error inbox is empty')
# One direct message
A(alice, 'send bob Hello!', 'success')
# Everyone else's inboxes should still be empty.
A(alice, 'recv', 'error inbox is empty')
A(iafisher, 'recv', 'error inbox is empty')
A(bob, 'recv', 'message <timestamp> alice bob Hello!')
A(bob, 'recv', 'error inbox is empty')
# A broadcast message
A(iafisher, "send * What's up guys?", 'success')
A(alice, 'recv', "message <timestamp> iafisher * What's up guys?")
A(bob, 'recv', "message <timestamp> iafisher * What's up guys?")
A(iafisher, 'recv', "message <timestamp> iafisher * What's up guys?")
A(alice, 'recv', 'error inbox is empty')
A(bob, 'recv', 'error inbox is empty')
A(iafisher, 'recv', 'error inbox is empty')
# Multiple messages
A(iafisher, 'send alice Hi Alice!', 'success')
A(iafisher, 'send alice Are you there?', 'success')
A(iafisher, 'send * Logging off now', 'success')
# Make sure the order of retrieval is first-sent, first-received.
A(alice, 'recv', b"message <timestamp> iafisher alice Hi Alice!\r\nmessage <timestamp> iafisher alice Are you there?\r\nmessage <timestamp> iafisher * Logging off now\r\n")
A(alice, 'recv', 'error inbox is empty')
# Clear the last broadcast message.
A(iafisher, 'recv', 'message <timestamp> iafisher * Logging off now')
A(bob, 'recv', 'message <timestamp> iafisher * Logging off now')
# Whitespace is significant.
A(alice, 'send bob    leading whitespace', 'success')
A(bob, 'recv', 'message <timestamp> alice bob    leading whitespace')
# Some error cases
A(alice, 'send charlie This should not work.', 'error recipient does not exist')
A(alice, 'send bob ' + 'a'*257, 'error message too long')
A(alice, 'send bob ' + 'a'*256, 'success')
A(bob, 'recv', 'message <timestamp> alice bob ' + 'a'*256)


# SYNTAX
# Username cannot be longer than 30 characters.
syntax_user = new_client()
A(syntax_user, 'register ' + 'a'*31 + ' pwd', 'error username longer than 30 chars')
A(syntax_user, 'register ' + 'a'*30 + ' pwd', 'success')
A(syntax_user, 'logout', 'success')
# 30 characters, not bytes.
A(syntax_user, 'register дддддддддддддддддддддддддддддд pwd', 'success')
# TODO:
# - Passwords longer than 50 chars
# - Invalid UTF-8
# - Files longer than 1024 bytes


# UPLOAD AND DOWNLOAD
upload_user = new_client('upload_user pwd')
A(upload_user, 'listfiles', 'filelist')
A(upload_user, 'download hello.txt', 'error could not read from file')
A(upload_user, 'upload hello.txt 6 hello\n', 'success')
A(upload_user, 'download hello.txt', 'file hello.txt 6 hello\n')
# Cannot overwrite pre-existing file.
A(upload_user, 'upload hello.txt 7 goodbye', 'error file already exists')
A(alice, 'upload hello.txt 7 goodbye', 'error file already exists')
# Try uploading binary data.
A(upload_user, b'upload junk.bin 5 \xff\xff\xff\xff\xff\r\n', 'success')
A(iafisher, 'download junk.bin', b'file junk.bin 5 \xff\xff\xff\xff\xff\r\n')
A(upload_user, 'listfiles', 'filelist hello.txt junk.bin')


# AUTHENTICATION
auth_user = new_client()
A(auth_user, 'logout', 'error must be logged in')
A(auth_user, 'send alice Hello!', 'error must be logged in')
A(auth_user, 'recv alice', 'error must be logged in')
A(auth_user, 'upload hello.txt 5 hello', 'error must be logged in')
A(auth_user, 'download hello.txt', 'error must be logged in')
A(auth_user, 'listfiles', 'error must be logged in')


ASSERT_EMPTY(iafisher)
ASSERT_EMPTY(bob)
ASSERT_EMPTY(alice)
ASSERT_EMPTY(syntax_user)
ASSERT_EMPTY(upload_user)
ASSERT_EMPTY(auth_user)
