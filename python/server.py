#!/usr/bin/env python3
"""A Python implementation of the polyglot-server project.

See the top-level directory's README file for details.

Author:  Ian Fisher (iafisher@protonmail.com)
Version: August 2018

TODO: Use SQL joins.
    https://www.w3schools.com/sql/sql_join.asp
"""

import argparse
import datetime
import functools
import logging
import os
import socket
import sqlite3
import sys
import threading


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


BASE_DIR = os.path.dirname(os.path.realpath(__file__))

FILE_DIR = os.path.join(BASE_DIR, 'files')
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')
LOG_FILE = os.path.join(BASE_DIR, 'log', 'server.log')
SERVER_PORT = 8888


class ChatServer:
    def __init__(self, port, path_to_db, path_to_files):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.path_to_files = path_to_files
        self.path_to_db = path_to_db

    def run_forever(self):
        try:
            self.socket.bind((socket.gethostbyname('localhost'), self.port))
        except PermissionError:
            fatal('Could not bind to port %d (permission denied)', self.port)
        except OSError:
            fatal('Could not bind to port %d. Is it already in use?', self.port)

        logger.info('Listening on port %d', self.port)
        self.socket.listen()
        try:
            while True:
                conn, addr = self.socket.accept()
                conn_thread = ChatConnection(conn, self.path_to_db,
                    self.path_to_files)
                conn_thread.start()
        finally:
            self.socket.close()


# A Python version of Rust's Result type--more efficient than raising an
# exception.
Result = lambda r: (r, None)
Error = lambda e: (None, e)


def message_handler(nfields, ws_in_last_field=False, auth=True, binary=False):
    """A decorator for handler methods in the ChatConnection class.

    The decorator splits the message bytes into fields and sends an error if
    the message is ill-formatted.

    Parameters:
        nfields: How many space-separated fields does the message contain,
            excluding the command name itself?
        ws_in_last_field: Does the last field allow whitespace?
        auth: Must the user be logged in?
        binary: Can the message contain arbitrary bytes?
    """

    def wraps(f):
        @functools.wraps(f)
        def wrapped(self, message):
            if binary is False:
                try:
                    message = message.decode('utf-8')
                except UnicodeDecodeError:
                    return Error('invalid UTF-8')

            if auth and self.uid is None:
                return Error('must be logged in')
            elif not auth and self.uid is not None:
                return Error('must not be logged in')

            sep = b' ' if binary else ' '
            if ws_in_last_field:
                try:
                    args = message.split(sep, maxsplit=nfields)
                except ValueError:
                    return Error('wrong number of fields')
            else:
                args = message.split(sep)

            # Remove the command name.
            args.pop(0)
            if len(args) != nfields:
                return Error('wrong number of fields')
            else:
                return f(self, *args)
        return wrapped
    return wraps


class ChatConnection(threading.Thread):
    def __init__(self, conn, path_to_db, path_to_files):
        super().__init__()
        self.socket = conn
        # self.uid is None as long as no user is logged in on the connection.
        self.uid = None
        self.path_to_db = path_to_db
        self.path_to_files = path_to_files

    def run(self):
        self.db = sqlite3.connect(self.path_to_db)
        self.cursor = self.db.cursor()

        logger.info('Connection opened')
        buffer = b''
        try:
            while True:
                message, buffer = self.receive_message(buffer)
                logger.info('Received message %r', message)

                first_space = message.find(b' ')
                if first_space == -1:
                    # Commands without fields are not followed by a space.
                    first_space = len(message)

                cmd = message[:first_space]
                try:
                    handler = self.dispatch[cmd]
                except KeyError:
                    self.send_and_log(b'error no such command\r\n')
                else:
                    response, error = handler(self, message)
                    if error is not None:
                        self.send_and_log(b'error ' + error.encode('utf-8')
                            + b'\r\n')
                    else:
                        if isinstance(response, str):
                            response = response.encode('utf-8') + b'\r\n'
                        self.send_and_log(response)
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            logger.info('Connection closed')
            self.socket.close()
            self.db.close()

    def receive_message(self, buffer):
        """Return a tuple (message, buffer), where `message` is a CRLF-
        terminated bytestring and `buffer` is a bytestring containing whatever
        data was read on the socket past the end of `message`.

        The initial call to receive_message should pass in an empty bytestring
        for `buffer`; subsequent calls should pass in the buffer returned by
        the previous call, e.g.:

            message, buffer = self.receive_message(b'')
            message, buffer = self.receive_message(buffer)

        This maintains the invariant that `buffer` always aligns with the
        beginning of a message.
        """
        data = self.socket.recv(1024) if not buffer else buffer
        if not data:
            return b'', buffer

        # Find the message terminator.
        end = data.find(b'\r\n')
        while end == -1:
            old_end = len(data)
            data += self.socket.recv(1024)
            if len(data) == old_end:
                return data, b''
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
                    if datapos + length < end:
                        # This means that payload was not terminated with CRLF,
                        # which is a client error.
                        return b'', data[end+2:]
                    end = datapos + length

        return data[:end], data[end+2:]

    @message_handler(nfields=2, auth=False, ws_in_last_field=True)
    def process_register(self, username, password):
        if len(username) > 30:
            return Error('username longer than 30 chars')
        if len(password) > 50:
            return Error('password longer than 50 chars')

        self.cursor.execute('''
            SELECT username FROM users WHERE username=?;
        ''', (username,))
        if self.cursor.fetchone() is None:
            # NOTE: Storing plaintext passwords is a terrible idea, but this
            # project is not designed to be cryptographically secure.
            self.cursor.execute('''
                INSERT INTO users (username, password)
                VALUES (?, ?);
            ''', (username, password))
            self.uid = self.cursor.lastrowid
            self.db.commit()
            return Result('success')
        else:
            return Error('username is already registered')

    @message_handler(nfields=2, auth=False, ws_in_last_field=True)
    def process_login(self, username, password):
        self.cursor.execute('''
            SELECT user_id FROM users where username=? AND password=?;
        ''', (username, password))
        userrow = self.cursor.fetchone()
        if userrow is not None:
            self.uid = userrow[0]
            return Result('success')
        else:
            return Error('invalid username or password')

    @message_handler(nfields=0)
    def process_logout(self):
        self.uid = None
        return Result('success')

    @message_handler(nfields=2, ws_in_last_field=True)
    def process_send(self, recipient, message):
        if len(message) > 256:
            return Error('message too long')

        if recipient == '*':
            self.broadcast_message(message)
            return Result('success')
        else:
            recipient_id = self.username_to_id(recipient)
            if recipient_id is not None:
                self.store_message(recipient, recipient_id, message)
                return Result('success')
            else:
                return Error('recipient does not exist')

    def broadcast_message(self, message):
        self.cursor.execute('SELECT user_id FROM users;')
        # TODO: Can probably make this more efficient.
        for row in self.cursor.fetchall():
            recipient_id = row[0]
            self.store_message('*', recipient_id, message)

    def store_message(self, recipient, recipient_id, message):
        timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
        self.cursor.execute('''
            INSERT INTO messages (timestamp, source_id, destination,
                inbox_id, body)
            VALUES (?, ?, ?, ?, ?);
        ''', (timestamp, self.uid, recipient, recipient_id, message))
        self.db.commit()

    @message_handler(nfields=0)
    def process_recv(self):
        # Get all outstanding messages to the user.
        self.cursor.execute('''
            SELECT * FROM messages WHERE inbox_id=? ORDER BY message_id;
        ''', (self.uid,))
        rows = self.cursor.fetchall()

        # Delete the messages retrieved.
        self.cursor.execute('''
            DELETE FROM messages WHERE inbox_id=?;
        ''', (self.uid,))
        self.db.commit()

        if rows:
            return Result('\r\n'.join(map(self.row_to_message, rows)))
        else:
            return Error('inbox is empty')

    def row_to_message(self, row):
        timestamp, sender, dest, _, body = row[1:]
        sender = self.id_to_username(sender)
        return 'message {} {} {} {}'.format(timestamp, sender, dest, body)

    @message_handler(nfields=3, ws_in_last_field=True, binary=True)
    def process_upload(self, filename, filelength, filebytes):
        try:
            filename = filename.decode('utf-8')
        except UnicodeDecodeError:
            return Error('invalid UTF-8')

        fullname = os.path.join(self.path_to_files, filename)
        if not os.path.isfile(fullname):
            try:
                with open(fullname, 'wb') as f:
                    f.write(filebytes)
            except IOError:
                return Error('could not write to file')
            else:
                return Result('success')
        else:
            return Error('file already exists')

    @message_handler(nfields=0)
    def process_listfiles(self):
        filelist = os.listdir(self.path_to_files)
        if filelist:
            return Result('filelist ' + ' '.join(sorted(filelist)))
        else:
            return Result('filelist')

    @message_handler(nfields=1)
    def process_download(self, filename):
        fullname = os.path.join(self.path_to_files, filename)
        try:
            with open(fullname, 'rb') as f:
                data = f.read()
            return Result(b'file %b %d %b\r\n' % (filename.encode('utf-8'),
                len(data), data))
        except (IOError, FileNotFoundError):
            return Error('could not read from file')

    # This dictionary is used to find the proper handler for a message based on
    # its first word.
    dispatch = {
        b'register': process_register,
        b'login': process_login,
        b'logout': process_logout,
        b'send': process_send,
        b'recv': process_recv,
        b'upload': process_upload,
        b'listfiles': process_listfiles,
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

    def id_to_username(self, uid):
        self.cursor.execute('''
            SELECT username FROM users WHERE user_id=?;
        ''', (uid,))
        row = self.cursor.fetchone()
        if row is not None:
            return row[0]
        else:
            return None

    def send_and_log(self, msg):
        logger.info('Sending message %r', msg)
        self.socket.send(msg)


def recv_large(sock, n):
    """Receive n bytes, where n is potentially a very large number."""
    data = b''
    while len(data) < n:
        data += sock.recv(max(1024, n - len(data)))
    return data


def fatal(msg, *args, retcode=2):
    logger.critical(msg, *args)
    sys.exit(retcode)


if __name__ == '__main__':
    # Parse command-line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--database', default=DB_FILE,
        help='path to a SQLite3 database to use')
    parser.add_argument('-f', '--files', default=FILE_DIR,
        help='path to a directory to hold files uploaded to the server')
    parser.add_argument('-p', '--port', default=SERVER_PORT, type=int,
        help='port for the server to listen on')
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
        help='turn off logging')
    args = parser.parse_args()

    # Configure logging.
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(levelname)s] (%(threadName)s) '
        '%(asctime)s: %(message)s')
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    if not args.quiet:
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

    try:
        os.mkdir(args.files)
    except FileExistsError:
        pass
    except OSError:
        fatal('File folder %s does not exist and could not be created',
            args.files)

    server = ChatServer(args.port, args.database, args.files)
    server.run_forever()
