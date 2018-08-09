/**
 * Author:  Ian Fisher
 * Version: August 2018
 */
use std::io::prelude::*;
use std::net::TcpStream;
use std::net::TcpListener;
use std::thread;


struct ChatConnection {
    stream: TcpStream,
    buffer: [u8; 1024],
}


fn main() {
    // This implementation heavily based on chapter 20 of the Rust book, "Building a Multithreaded
    // Web Server" (https://doc.rust-lang.org/book/2018-edition/ch20-01-single-threaded.html).
    let listener = TcpListener::bind("127.0.0.1:8888").expect("Could not bind to socket");

    for stream in listener.incoming() {
        let stream = stream.expect("Could not accept connection");

        thread::spawn(|| {
            let mut connection = ChatConnection::new(stream);
            connection.run();
        });
    }
}


impl ChatConnection {
    pub fn new(stream: TcpStream) -> Self {
        ChatConnection { stream, buffer: [0; 1024] }
    }

    pub fn run(&mut self) {
        loop {
            if let Some(message) = self.receive_message() {
                println!("{:?}", message);
                self.stream.write(&message[..]).expect("Could not write to socket");
                self.stream.flush().expect("Could not flush the socket");
            } else {
                break;
            }
        }
    }

    fn receive_message(&mut self) -> Option<Vec<u8>> {
        let mut data = Vec::with_capacity(1024);
        if self.buffer.len() > 0 {
            data.extend_from_slice(&self.buffer);
        } else {
            self.stream.read(&mut data).expect("Could not read from socket");
        };

        let mut crlf_pos = find_crlf(&data[..]);
        loop {
            match crlf_pos {
                Some(pos) => {
                    let old_end = data.len();
                    self.stream.read(&mut data).expect("Could not read from socket");
                    if data.len() == old_end {
                        return None;
                    }
                    crlf_pos = find_crlf(&data[(pos+2)..]);
                },
                None => break,
            }
        }

        Some(data)
    }
}


fn find_crlf(buffer: &[u8]) -> Option<usize> {
    buffer.windows(2).position(|window| window == b"\r\n")
}
