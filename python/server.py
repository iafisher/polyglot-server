#!/usr/bin/env python3
"""A Python implementation of the polyglot-server project.

See the top-level directory's README file for details.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: July 2018
"""

import socket
import threading

class ChatServer:
    def __init__(self, port=8888):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run_forever(self):
        self.socket.bind( (socket.gethostbyname('localhost'), self.port) )
        self.socket.listen()
        while True:
            conn, addr = self.socket.accept()
            conn_thread = ChatConnection(conn)
            conn_thread.start()

class ChatConnection(threading.Thread):
    def __init__(self, conn):
        super().__init__()
        self.socket = conn

    def run(self):
        while True:
            data = self.socket.recv(1024)
            if not data:
                break
            print(data)
            self.socket.send(b'success\0')

if __name__ == '__main__':
    server = ChatServer()
    server.run_forever()
