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
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>


// Command-line flags.
static unsigned short flag_quiet = 0;


void log_info(const char*, ...);


#define LOG_FATAL(message, ...) \
    do { \
        fprintf(stderr, "[critical ]" message "\n", __VA_ARGS__); \
        exit(2);
    } while (0)


void run_forever(unsigned int port, const char* path_to_db,
        const char* path_to_files);
void* handle_connection(void* sockptr);

void* emalloc(size_t);


#define OPT(arg, shortname, longname) \
    (strcmp(arg, shortname) == 0 || strcmp(arg, longname) == 0)


int main(int argc, char* argv[]) {
    unsigned int port = 8888;
    const char* path_to_db = "db.sqlite3";
    const char* path_to_files = "files";

    for (int i = 1; i < argc; i++) {
        if (OPT(argv[i], "-q", "--quiet")) {
            flag_quiet = 1;
        } else if (OPT(argv[i], "-d", "--database")) {
            if (i == argc - 1) {
                fputs("Error: -d or --database not followed by database.\n", stderr);
                return 2;
            }
            path_to_db = argv[++i];
        } else if (OPT(argv[i], "-p", "--port")) {
            if (i == argc - 1) {
                fputs("Error: -p or --port not followed by port.\n", stderr);
                return 2;
            }
            port = atoi(argv[++i]);
        } else if (OPT(argv[i], "-f", "--files")) {
            if (i == argc - 1) {
                fputs("Error: -f or --files not followed by file path.\n", stderr);
                return 2;
            }
            path_to_files = argv[++i];
        } else {
            fprintf(stderr, "Error: unrecognized argument \"%s\"\n", argv[i]);
            return 2;
        }
    }

    run_forever(port, path_to_db, path_to_files);
    return 0;
}


void run_forever(unsigned int port, const char* path_to_db, 
        const char* path_to_files) {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        LOG_FATAL("Could not open socket");
    }

    struct sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof address) < 0) {
        LOG_FATAL("Could not bind to socket");
    }

    if (listen(server_fd, 5) < 0) {
        LOG_FATAL("Could not listen to socket");
    }

    int new_socket;
    socklen_t addrlen = sizeof address;
    while ((new_socket = accept(server_fd, (struct sockaddr*)&address, &addrlen)) >= 0) {
        pthread_t thread_id;
        int* sockptr = emalloc(sizeof *sockptr);
        *sockptr = new_socket;
        if (pthread_create(&thread_id, NULL, handle_connection, (void*)sockptr) != 0) {
            LOG_FATAL("Could not spawn thread");
        }
    }
}


#define BUFSIZE 1024


void* handle_connection(void* sockptr) {
    int conn = *(int*)sockptr;

    char buffer[BUFSIZE];
    while (1) {
        ssize_t nbytes = read(conn, buffer, BUFSIZE);
        if (nbytes > 0) {
            write(conn, buffer, nbytes);
        } else {
            break;
        }
    }

    free(sockptr);
    return NULL;
}


void log_info(const char* message, ...) {
    if (!flag_quiet) {
        va_list args;
        va_start(args, message);
        fprintf(stderr, "[info] ");
        vfprintf(stderr, message, args);
        va_end(args);
    }
}



void* emalloc(size_t nbytes) {
    void* ret = malloc(nbytes);
    if (ret == NULL) {
        LOG_FATAL("Out of memory");
    }
    return ret;
}
