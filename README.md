A toy chat server, implemented in as many languages as I know.

## Project specification
### Overview
The project is a chat server program that allows multiple users to send direct
and broadcast messages to one another. It is designed as a minimal but
functional program that calls upon a range of common programming tasks,
including

 - Concurrency
 - Unicode handling
 - File I/O
 - Databases
 - Unix sockets
 - Logging
 - Testing

A chat network consists of one chat server and zero or more chat clients. Client
programs connect to the server using Unix sockets and send a login message with
their credentials. Once logged in, clients may send direct messages to one
another and broadcast messages to all users. A client does not have to be logged
in to receive a message: the server maintains an inbox of unread messages for
all registered users.

The server also stores user-uploaded files that are accessible to all users.

### The chat protocol
The chat protocol comprises a set of messages that may be sent between a client
and a server. All messages are UTF-8 encoded and terminated with a null byte
unless otherwise noted. All messages begin with a command name, followed by zero
or more message fields, which are denoted in the protocol specification by angle
brackets enclosing in a descriptive name. The fields are separated by a single
space. The command name in a message with no fields is followed immediately by
the null byte with no intervening space.

The following messages may be sent by a client to the server. All sessions
must begin with either a `register` or a `login` message from the client.

`register <username> <password>`: Create a new account. The server returns
`error` if the username does not consist solely of alphanumeric characters and
underscores, or if the username is already registered. Otherwise the server
returns `success`.

`login <username> <password>`: Log in to the server with the given credentials.
The server returns `success` if the credentials match a previous `register`
message, and `error` otherwise.

`send <timestamp> <username> <message>`: Send the message to the identified
user. The timestamp field contains the UTC time the message was sent, in the
format e.g. 2018-07-18T17:12:47Z (ISO 8601 format). The username field may be
an asterisk, in which case the message is sent to all users. The message field
must not be empty (though it may contain only whitespace). The server returns
`error` if the timestamp is in the future or more than thirty seconds in the
past, or if the user does not exist. The server returns `success` otherwise.

`checkinbox`: Check the client's inbox. The server returns an `inbox` message.

`recv <username>`: Receive one message that was sent by the identified user. The
server returns a `message` response, or `error` if there are no messages from
the user. The message returned will be deleted from the client's inbox so that
subsequent calls to `checkinbox` do not include it in the message counts.

`upload <filename> <filelength> <file>`: Upload the file to the server. The
file name field may not contain any whitespace or forward slashes. The file
length field is the length of the file in bytes, and the file field is the
actual contents of the file, as arbitrary binary data (not necessarily UTF-8
encoded). This message does not end with a null byte (unless the file itself
happens to). The server responds with a `success` message is the file is
successfully uploaded, and an `error` message otherwise.

`getfilelist`: Query for the names of the files that have been uploaded to the
server. The server returns a `filelist` message.

`download <filename>`: Download a file from the server. The server returns
either a `file` message or an `error` message.


The following messages may be sent by the server to a client.

`success`: When an operation has succeeded.

`error`: When an operation has failed, or when a command could not be parsed.

`inbox <user_1> <message_count_1> ... <user_n> <message_count_n>`: Response to
the `checkinbox` request. Each user from whom the client has unread messages is
listed along with the count of messages. Broadcast messages are treated the same
as direct messages, so if a user alice sends bob a direct message and also a
broadcast message, then the `inbox` response will contain an entry `alice 2`.
Broadcast and direct messages are received and stored in the inbox regardless of
whether the recipient is online when the message is sent.

`message <timestamp> <from> <to> <body>`: Response to the `recv` request. The
`to` field is included to differentiate broadcast messages, denoted with an
asterisk in the `to` field, from direct messages.

`filelist <file_1> ... <file_n>`: Response to the `getfilelist` request. The
file list may be empty if no files have been uploaded to the server.

`file <filename> <filelength> <file>`: Response to the `download` request. The
fields have the same meaning as in the `upload` message. This message does not
end with a null byte.

### The chat server
The chat server must respond to requests as described in the protocol
specification. It must listen on port 8888. It must maintain an SQLite3 database
of user credentials and unread messages. It must log every message it receives
and every response it returns. It must be concurrent. It must include a test
suite.

The details of implementation may vary between languages, but they must meet
the above requirements.

## Implementations
The full project is currently implemented in the following languages:
 - None yet!

I plan to implement it in these languages in the future:
 - C
 - Python
 - Rust
 - Go
 - Java
 - Haskell?
