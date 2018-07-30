import sqlite3
import sys


if len(sys.argv) != 2:
    sys.stderr.write('Usage: python3 createdb.py <path to database>\n')
    sys.exit(1)
else:
    db = sqlite3.connect(sys.argv[1])
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
    db.close()
