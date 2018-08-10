CC = gcc
CFLAGS = -Wall -Werror -std=c99 -pedantic -Iinclude
LFLAGS = -lpthread

server: src/server.c src/log.c
	$(CC) $(CFLAGS) src/server.c src/log.c -o $@ $(LFLAGS)

.PHONY: clean

clean:
	rm -f server *.o
