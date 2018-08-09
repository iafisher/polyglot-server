CC = gcc
FLAGS = -Wall -Werror -std=c99 -pedantic

server: server.c
	$(CC) $(FLAGS) server.c -o server

.PHONY: clean

clean:
	rm -f server *.o
