#!/usr/bin/env python3
"""A Python implementation of the polyglot-server project.

See the top-level directory's README file for details.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: July 2018

TODO: Use SQL joins.
    https://www.w3schools.com/sql/sql_join.asp
TODO: Replace self.socket.send(error); return with raise ChatError(...)
TODO: argparse
"""

import datetime
import functools
import os
import socket
import sqlite3
import threading
from collections import defaultdict


BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')


class ChatServer:
    def __init__(self, port=8888, path_to_db=DB_FILE):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not os.path.isfile(path_to_db):
            self.createdb()

    def run_forever(self):
        self.socket.bind((socket.gethostbyname('localhost'), self.port))
        self.socket.listen()
        try:
            while True:
                conn, addr = self.socket.accept()
                conn_thread = ChatConnection(conn)
                conn_thread.start()
        finally:
            self.socket.close()

    def createdb(self):
        db = sqlite3.connect(DB_FILE)
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username varchar(30) NOT NULL,
                password varchar(50) NOT NULL,
                logged_in BOOLEAN NOT NULL CHECK (logged_in IN (0,1))
            );
        ''')
        cursor.execute('''
            CREATE TABLE messages (
                message_id INTEGER PRIMARY KEY,
                timestamp varchar(25) NOT NULL,
                source_id INTEGER NOT NULL,
                destination varchar(30) NOT NULL,
                inbox_id INTEGER NOT NULL,
                body varchar(256) NOT NULL,
                FOREIGN KEY (source_id) REFERENCES users (user_id)
                    ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (inbox_id) REFERENCES users (user_id)
                    ON UPDATE CASCADE ON DELETE CASCADE
            );
        ''')
        db.commit()
        cursor.close()


def message_handler(nfields, ws_in_last_field=False, auth=True, binfields=()):
    """A decorator for handler methods in the ChatConnection class.

    The decorator splits the message bytes into fields and sends an error if
    the message is ill-formatted.
    """

    def wraps(f):
        @functools.wraps(f)
        def wrapped(self, message):
            if auth and self.uid is None:
                self.socket.send(b'error must be logged in\r\n')
                return
            elif not auth and self.uid is not None:
                self.socket.send(b'error must not be logged in\r\n')
                return

            if ws_in_last_field:
                try:
                    args = message.split(b' ', maxsplit=nfields)
                except ValueError:
                    self.socket.send(b'error wrong number of fields\r\n')
                    return
            else:
                args = message.split(b' ')

            for i, arg in enumerate(args):
                if i not in binfields:
                    try:
                        arg.decode('utf-8')
                    except UnicodeDecodeError:
                        self.socket.send(b'error invalid UTF-8\r\n')
                        return

            # Remove the command name.
            args.pop(0)
            if len(args) != nfields:
                self.socket.send(b'error wrong number of fields\r\n')
                return
            else:
                f(self, *args)
        return wrapped
    return wraps


class ChatConnection(threading.Thread):
    def __init__(self, conn):
        super().__init__()
        self.socket = conn
        # self.uid and self.username are None as long as no user is logged in
        # on the connection.
        self.uid = None
        # Invariant: when self.buffer is non-empty, it always aligns with the
        # start of a client message.
        # TODO: Change this to a parameter to receive_message.
        self.buffer = b''

    def run(self):
        self.db = sqlite3.connect(DB_FILE)
        self.cursor = self.db.cursor()
        try:
            while True:
                message = self.receive_message()
                if not message:
                    break
                first_space = message.find(b' ')
                if first_space == -1:
                    # Commands without fields are not followed by a space.
                    first_space = len(message)
                cmd = message[:first_space]
                try:
                    handler = self.dispatch[cmd]
                except KeyError:
                    self.socket.send(b'error no such command\r\n')
                else:
                    handler(self, message)
        finally:
            self.socket.close()
            self.db.close()

    def receive_message(self):
        data = self.socket.recv(1024) if not self.buffer else self.buffer
        if not data:
            return b''

        # Find the message terminator.
        end = data.find(b'\r\n')
        while end == -1:
            old_end = len(data)
            data += self.socket.recv(1024)
            if len(data) == old_end:
                return data
            end = data.find(b'\r\n', old_end)

        # Special parsing has to be done for the upload message, because the
        # first CRLF sequence in the data stream could be part of the file
        # itself and not the end of the message. To find the end, we have to
        # read the `filelength` field.
        if data.startswith(b'upload '):
            second_space = data.find(b' ', 7)  # 7 == len(b'upload '')
            third_space = data.find(b' ', second_space+1)
            if second_space != -1 and third_space != -1:
                try:
                    length = int(data[second_space+1:third_space])
                except ValueError:
                    pass
                else:
                    # Now that the length field has been extracted, receiving
                    # the rest of the data is simple.
                    datapos = third_space + 1
                    length_so_far = len(data) - datapos
                    data += recv_large(self.socket, length - length_so_far)
                    end = datapos + length

        self.buffer = data[end+2:]
        return data[:end]

    @message_handler(nfields=2, auth=False)
    def process_register(self, username, password):
        self.cursor.execute('''
            SELECT username FROM users WHERE username=?;
        ''', (username,))
        if self.cursor.fetchone() is None:
            # NOTE: Storing plaintext passwords is a terrible idea, but this
            # project is not designed to be cryptographically secure.
            self.cursor.execute('''
                INSERT INTO users (username, password, logged_in)
                VALUES (?, ?, ?);
            ''', (username, password, 1))
            self.uid = self.cursor.lastrowid
            self.db.commit()
            self.socket.send(b'success\r\n')
        else:
            self.socket.send(b'error username already registered\r\n')

    @message_handler(nfields=2, auth=False)
    def process_login(self, username, password):
        self.cursor.execute('''
            SELECT user_id FROM users where username=? AND password=?;
        ''', (username, password))
        userrow = self.cursor.fetchone()
        if userrow is not None:
            self.uid = userrow[0]
            self.cursor.execute('''
                UPDATE users SET logged_in=1 WHERE user_id=?;
            ''', (self.uid,))
            self.db.commit()
            self.socket.send(b'success\r\n')
        else:
            self.socket.send(b'error invalid username or password\r\n')

    @message_handler(nfields=0)
    def process_logout(self):
        if self.uid is not None:
            self.cursor.execute('''
                UPDATE users SET logged_in=0 WHERE user_id=?;
            ''', (self.uid,))
            self.db.commit()
            self.uid = None
            self.socket.send(b'success\r\n')
        else:
            self.socket.send(b'error not logged in\r\n')

    @message_handler(nfields=2, ws_in_last_field=True)
    def process_send(self, recipient, message):
        if len(message) > 256:
            self.socket.send(b'error message too long\r\n')
            return

        if recipient == '*':
            self.broadcast_message(message)
            return

        recipient_id = self.username_to_id(recipient)
        if recipient_id is not None:
            self.store_message(recipient, recipient_id, message)
            self.socket.send(b'success\r\n')
        else:
            self.socket.send(b'error recipient does not exist\r\n')

    def broadcast_message(self, message):
        self.cursor.execute('''
            SELECT user_id FROM users;
        ''')
        # TODO: Can probably make this more efficient.
        for row in self.cursor.fetchall():
            recipient_id = row[0]
            self.store_message('*', recipient_id, message)

    def store_message(self, recipient, recipient_id, message):
        timestamp = datetime.datetime.utcnow() \
            .replace(microsecond=0).isoformat() + 'Z'
        self.cursor.execute('''
            INSERT INTO messages (timestamp, source_id, destination,
                inbox_id, body)
            VALUES (?, ?, ?, ?, ?);
        ''', (timestamp, self.uid, recipient, recipient_id, message))
        self.db.commit()

    @message_handler(nfields=0)
    def process_checkinbox(self):
        self.cursor.execute('''
            SELECT source_id, destination FROM messages WHERE inbox_id=?;
        ''', (self.uid,))
        message_count = defaultdict(int)
        for row in self.cursor.fetchall():
            source_id, destination = row
            if destination == '*':
                source_name = b'*'
            else:
                self.cursor.execute('''
                    SELECT username FROM users WHERE user_id=?;
                ''', (source_id,))
                source_name = self.cursor.fetchone()[0]
            message_count[source_name] += 1

        response_body = b' '.join(k + b' ' + str(v).encode('utf-8')
            for k, v in message_count.items())
        if response_body:
            self.socket.send(b'inbox ' + response_body + b'\r\n')
        else:
            self.socket.send(b'inbox\r\n')

    @message_handler(nfields=1)
    def process_recv(self, sender):
        sender_id = self.username_to_id(sender)
        if sender_id is None:
            self.socket.send(b'error user does not exist\r\n')
            return

        self.cursor.execute('''
            SELECT * FROM messages WHERE inbox_id=? AND source_id=?;
        ''', (self.uid, sender_id))
        row = self.cursor.fetchone()
        if row is not None:
            self.cursor.execute('''
                DELETE FROM messages WHERE message_id=?;
            ''', (row[0],))
            self.db.commit()

            timestamp = row[1]
            destination = row[3]
            body = row[5]
            self.socket.send(b'message %b %b %b %b\r\n'
                % (timestamp.encode('utf-8'), sender, destination, body))
        else:
            self.socket.send(b'error no messages from user\r\n')

    @message_handler(nfields=3, ws_in_last_field=True, binfields=(4,))
    def process_upload(self, filename, filelength, filebytes):
        pass

    @message_handler(nfields=0)
    def process_getfilelist(self):
        pass

    @message_handler(nfields=1)
    def process_download(self, filename):
        pass

    # This dictionary is used to find the proper handler for a message based on
    # its first word.
    dispatch = {
        b'register': process_register,
        b'login': process_login,
        b'logout': process_logout,
        b'send': process_send,
        b'checkinbox': process_checkinbox,
        b'recv': process_recv,
        b'upload': process_upload,
        b'getfilelist': process_getfilelist,
        b'download': process_download,
    }

    def username_to_id(self, username):
        self.cursor.execute('''
            SELECT user_id FROM users WHERE username=?;
        ''', (username,))
        row = self.cursor.fetchone()
        if row is not None:
            return row[0]
        else:
            return None


def recv_large(sock, n):
    """Receive n bytes, where n is potentially a very large number."""
    data = b''
    while len(data) < n:
        data += sock.recv(max(1024, n - len(data)))
    return data


if __name__ == '__main__':
    server = ChatServer()
    server.run_forever()
