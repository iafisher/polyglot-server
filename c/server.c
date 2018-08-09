/**
 * A C implementation of the polyglot-server project.
 *
 * See the top-level directory's README for details.
 *
 * Author:  Ian Fisher (iafisher@protonmail.com)
 * Version: August 2018
 */
#include <stdio.h>
#include <sys/socket.h>


// Command-line flags.
static unsigned short flag_quiet = 0;


void log_info(const char*, ...);
void log_fatal(const char*, ...);

void run_forever(unsigned int port);
void handle_connection();


int main(int argc, char* argv[]) {
    puts("Hello world!");
    run_forever(8888);
    return 0;
}


void run_forever(unsigned int port) {
    int server_fd = socket(AF_INET, SOCK_STREAM);
    if (server_fd == 0) {
        log_fatal("Could not open socket");
    }

    // TODO: Research these options.
    struct sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr*)address, sizeof address) < 0) {
        log_fatal("Could not bind to socket");
    }

    if (listen(server_fd, 5) < 0) {
        log_fatal("Could not listen to socket");
    }

    int new_socket;
    while ((new_socket = accept(server_fd, (struct sockaddr*)address,
        sizeof address)) >= 0) {
        
    }
}


void log_info(const char* message, ...) {
    if (!flag_quiet) {
        va_list args;
        va_start(args, message);
        vfprintf(message, args);
        va_end(args);
    }
}


void log_fatal(const char* message, ...) {
    va_list args;
    va_start(args, message);
    vfprintf(message, args);
    va_end(args);
    exit(2);
}
