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
        ASSERT(data == response, 'expected {!r}, got {!r}', response, data)


def new_client(credentials=None):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((socket.gethostbyname('localhost'), 8888))
    if credentials is not None:
        client.send(b'register ' + to_bytes(credentials))
    return client


def to_bytes(str_or_bytes):
    if isinstance(str_or_bytes, str):
        return str_or_bytes.encode('utf-8') + b'\r\n'
    else:
        return str_or_bytes


client = new_client()
A(client, 'logout', 'error must be logged in')
A(client, 'send alice Hello!', 'error must be logged in')
A(client, 'recv alice', 'error must be logged in')
A(client, 'upload hello.txt 5 hello', 'error must be logged in')
A(client, 'download hello.txt', 'error must be logged in')
A(client, 'listfiles', 'error must be logged in')
ASSERT_EMPTY(client)
