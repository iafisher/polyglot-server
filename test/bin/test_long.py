"""Test that long messages are handled properly.

Written as a Python module rather than a test script because the script runner
doesn't support advanced features like multiple requests and responses very
well.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: August 2018
"""

import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((socket.gethostbyname('localhost'), 8888))

client.send(b'register longtest pwd\r\n')
data = client.recv(4096)
assert data == b'success\r\n'

# Test a long message.
client.send(b'upload foo.txt 1025 ' + b'a'*1025 + b'\r\n')
data = client.recv(4096)
assert data == b'success\r\n'
client.send(b'download foo.txt\r\n')
data = client.recv(4096)
assert data == b'file foo.txt 1025 ' + b'a'*1025 + b'\r\n'

# Test a command that straddles a 1024-byte boundary.
client.send(b'upload bar.txt 1000 ' + b'a' * 1000 + b'\r\nlistfiles\r\n')
data = client.recv(4096)
assert data == b'success\r\n'
data = client.recv(4096)
assert data == b'filelist bar.txt foo.txt\r\n'
