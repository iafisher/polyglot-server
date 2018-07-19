A small but non-trivial programming project, designed to 

## Project specification
### Overview
The project consists of two executables: a chat server and a chat client.
The two programs allow multiple users to send direct and broadcast messages to
one another using a command-line interface.

### The chat protocol
The chat protocol comprises a set of messages that may be sent between a client
and a server. All messages are UTF-8 encoded and terminated with a null byte.
All messages begin with a command name, followed by zero or more message fields
(identified by angle brackets in the description below). The fields are
separated by a single space. For messages with no fields, the command name is
followed immediately by the null byte, with no trailing space.

The following messages may be sent by a client to the server.

`login <username>`: Log in to the server with the username, which must be a
sequence of alphanumeric characters and underscores. If the username contains
invalid characters, or if there is already a logged-in client with the same
username, then the server returns the `error` message. Otherwise the server
returns the `success` message. This message must be sent before any others.

`send <timestamp> <username> <message>`: Send the message to the identified
user. The timestamp field contains the UTC time the message was sent, in the
format e.g. 2018-07-18T17:12:47Z (ISO 8601 format). The username field may be
a particular username or an asterisk, which directs the message to all logged-in
users.

`checkinbox`: Check the client's inbox. The server returns an `inbox` message.

`recv <username>`: Receive one message that was sent by the identified user. The
server returns a `message` response, or `error` if there are no messages from
the user. The message returned will be deleted from the client's inbox so that
subsequent calls to `checkinbox` do not include it in the message counts.


The following messages may be sent by the server to a client.

`success`: When an operation has succeeded.

`error`: When an operation has failed, or when a command could not be parsed.

`inbox <user_1> <message_count_1> ... <user_n> <message_count_n>`: Return the
list of unread messages directed to the client. Only the usernames and counts of
messages are returned, not the messages themselves. The list only contains
non-zero entries. Broadcast messages are treated the same as direct messages.

`message <timestamp> <from> <to> <body>`: Return a particular message. The to
field is included to differentiate broadcast messages (for which the field is
an asterisk) with direct messages.

### The chat client

### The chat server

## Implementations
The full project is currently implemented in the following languages:
 - None yet!

I plan to implement it in these languages in the future:
 - C
 - Python
 - Rust
 - Go
 - Java
