/**
 * A C implementation of the polyglot-server project.
 *
 * See the top-level directory's README for details.
 *
 * Author:  Ian Fisher (iafisher@protonmail.com)
 * Version: August 2018
 */

#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>
#include "log.h"


void run_forever(unsigned int port, const char* path_to_db,
        const char* path_to_files);

void* handle_connection(void* sockptr);

void* emalloc(size_t);


// A macro tailored to parsing command-line arguments.
#define OPT(sname, lname, store) \
    } else if (strcmp(argv[i], sname) == 0 || strcmp(argv[i], lname) == 0) { \
        if (i == argc - 1) { \
            fputs("Error: " sname " or " lname " not followed by arg.\n", \
                stderr); \
            return 2; \
        } \
        store = argv[++i]; \


int main(int argc, char* argv[]) {
    const char* port_as_str = "8888";
    const char* path_to_db = "db.sqlite3";
    const char* path_to_files = "files";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-q") == 0 || strcmp(argv[i], "--quiet") == 0) {
            set_logging_level(LOG_LVL_INFO);
        OPT("-d", "--database", path_to_db)
        OPT("-f", "--files", path_to_files)
        OPT("-p", "--port", port_as_str)
        } else {
            fprintf(stderr, "Error: unrecognized argument \"%s\"\n", argv[i]);
            return 2;
        }
    }

    run_forever(atoi(port_as_str), path_to_db, path_to_files);
    return 0;
}


void run_forever(unsigned int port, const char* path_to_db, 
        const char* path_to_files) {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        log_fatal("Could not open socket");
    }

    struct sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof address) < 0) {
        log_fatal("Could not bind to socket");
    }

    if (listen(server_fd, 5) < 0) {
        log_fatal("Could not listen to socket");
    }

    log_info("Listening on port %d", port);

    int new_socket;
    socklen_t addrlen = sizeof address;
    while ((new_socket = accept(server_fd, (struct sockaddr*)&address, &addrlen)) >= 0) {
        pthread_t thread_id;
        int* sockptr = emalloc(sizeof *sockptr);
        *sockptr = new_socket;
        if (pthread_create(&thread_id, NULL, handle_connection, (void*)sockptr) != 0) {
            log_fatal("Could not spawn thread");
        }
    }
}


#define BUFSIZE 1024


void* handle_connection(void* sockptr) {
    int conn = *(int*)sockptr;

    log_info("Connection opened");

    char buffer[BUFSIZE];
    while (1) {
        ssize_t nbytes = read(conn, buffer, BUFSIZE);
        if (nbytes > 0) {
            log_info("Received message \"%.*s\"", (int)nbytes, buffer);
            write(conn, buffer, nbytes);
        } else {
            break;
        }
    }

    free(sockptr);
    return NULL;
}


void* emalloc(size_t nbytes) {
    void* ret = malloc(nbytes);
    if (ret == NULL) {
        log_fatal("Out of memory");
    }
    return ret;
}
