CC = gcc
CFLAGS = -Wall -Werror -std=c99 -pedantic
LFLAGS = -lpthread

server: server.c
	$(CC) $(CFLAGS) server.c -o server $(LFLAGS)

.PHONY: clean

clean:
	rm -f server *.o
