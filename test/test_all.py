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


# Time to wait, in seconds, before receiving the response to a request. If you
# get spurious "expected b'...', got nothing" errors, try adjusting this value
# upwards.
TIME_TO_WAIT = 0.1


def ASSERT(cond, msg, *args):
    try:
        assert cond
    except AssertionError:
        lineno = inspect.getframeinfo(inspect.stack()[-1][0]).lineno
        sys.stderr.write(('Error ({}:{}): ' + msg + '\r\n').format(
            __file__, lineno, *args))


def ASSERT_EMPTY(client):
    time.sleep(TIME_TO_WAIT)
    try:
        data = client.recv(1024, socket.MSG_DONTWAIT)
    except BlockingIOError:
        pass
    else:
        ASSERT(data == b'', 'expected nothing, got {!r}', data)


def A(client, request, response):
    response = to_bytes(response)
    client.send(to_bytes(request))
    time.sleep(TIME_TO_WAIT)
    try:
        data = client.recv(4096, socket.MSG_DONTWAIT)
    except BlockingIOError:
        ASSERT(False, 'expected {!r}, got nothing', response)
    else:
        ASSERT(equivalent(response, data), 'expected {!r}, got {!r}',
            response, data)


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
A(syntax_user, 'logout', 'success')
# Password cannot be longer than 50 characters.
A(syntax_user, 'register jekvnkje ' + 'a'*51, 'error password longer than 50 chars')
A(syntax_user, 'register jekvnkje ' + 'a'*50, 'success')
A(syntax_user, 'logout', 'success')


# UPLOAD AND DOWNLOAD
upload_user = new_client('upload_user pwd')
A(upload_user, 'listfiles', 'filelist')
# Try downloading a non-existent file.
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


# INCORRECT SYNTAX
bad_syntax_user = new_client()
A(bad_syntax_user, 'register', 'error wrong number of fields')
A(bad_syntax_user, 'register bad_syntax', 'error wrong number of fields')
A(bad_syntax_user, 'register bad_syntax bad/as[hell)', 'success')
A(bad_syntax_user, 'logout extra', 'error wrong number of fields')
A(bad_syntax_user, 'logout', 'success')
A(bad_syntax_user, 'login bad_syntax', 'error wrong number of fields')
A(bad_syntax_user, 'login bad_syntax bad/as[hell)', 'success')
A(bad_syntax_user, 'send iafisher', 'error wrong number of fields')
A(bad_syntax_user, 'recv extra', 'error wrong number of fields')
A(bad_syntax_user, 'upload', 'error wrong number of fields')
A(bad_syntax_user, 'upload whatever.txt', 'error wrong number of fields')
A(bad_syntax_user, 'upload whatever.txt 100', 'error wrong number of fields')
A(bad_syntax_user, 'upload whatever.txt 3a abc', 'error invalid length field of upload message')


# LONG MESSAGES
# Yes, your password can be all whitespace.
long_user = new_client('long_user    ')
A(long_user, 'upload long.txt 1025 ' + 'a'*1025, 'success')
A(long_user, 'download long.txt', 'file long.txt 1025 ' + 'a'*1025)
# A command that straddles a message boundary.
A(long_user, 'upload long2.txt 1000 ' + 'a'*1000 + '\r\nlistfiles',
    'success\r\nfilelist hello.txt junk.bin long.txt long2.txt')


# UTF-8 SUPPORT
utf8_user = new_client('utf8_юникод мой пароль')
A(utf8_user, 'logout', 'success')
A(utf8_user, 'login utf8_юникод мой пароль', 'success')
A(iafisher, 'send utf8_юникод Hello, 世界!', 'success')
# Test each message type and a variety of scripts (Cyrillic, Chinese, Sanskrit).
A(utf8_user, 'recv', 'message <timestamp> iafisher utf8_юникод Hello, 世界!')
A(utf8_user, 'upload दस्तावेज़ 149 ॐ\nश्रीपरमात्मने नमः\nअथ श्रीमद्भगवद्गीता\nप्रथमोऽध्यायः', 'success')
A(utf8_user, 'listfiles', 'filelist hello.txt junk.bin long.txt long2.txt दस्तावेज़')
A(utf8_user, 'download दस्तावेज़', 'file दस्तावेज़ 149 ॐ\nश्रीपरमात्मने नमः\nअथ श्रीमद्भगवद्गीता\nप्रथमोऽध्यायः')

# TRYING TO BREAK THE SERVER
pentest_user = new_client()
A(pentest_user, b'\r\n', 'error no such command')
# Server shouldn't crash when client closes connection.
pentest_user.send(b'logout\r\n')
pentest_user.close()
pentest_user = new_client()
A(pentest_user, 'register infowarrior prophet of disaster', 'success')
# Lie about the length of a file upload.
# Note that there's no point in overstating the size of the file, because the
# server will just spin until the stated number of bytes are available.
A(pentest_user, 'upload hacker.exe 3 1234\r\nrecv', 'error message not terminated with CRLF\r\nerror inbox is empty')
A(pentest_user, 'logout', 'success')
# A password of a single space is allowed (but not encouraged).
A(pentest_user, 'register pentest  ', 'success')
A(pentest_user, 'logout', 'success')
A(pentest_user, 'login pentest  ', 'success')
# Make sure that a valid message sent after an invalid one is still processed.
A(pentest_user, 'upload hacker.exe 3a _\r\nrecv', 'error invalid length field of upload message\r\nerror inbox is empty')


ASSERT_EMPTY(iafisher)
ASSERT_EMPTY(bob)
ASSERT_EMPTY(alice)
ASSERT_EMPTY(syntax_user)
ASSERT_EMPTY(upload_user)
ASSERT_EMPTY(auth_user)
ASSERT_EMPTY(bad_syntax_user)
ASSERT_EMPTY(long_user)
ASSERT_EMPTY(utf8_user)
ASSERT_EMPTY(pentest_user)
