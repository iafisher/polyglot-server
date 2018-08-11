/**
 * Author:  Ian Fisher (iafisher@protonmail.com)
 * Version: August 2018
 */

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "log.h"


static log_level_t current_log_level = LOG_LVL_INFO;


void set_logging_level(log_level_t new_level) {
    current_log_level = new_level;
}

#define TIME_BUF_LEN 20
static void log_unconditional(const char* lvl, const char* fmt, va_list args) {
    time_t t = time(NULL);
    char timebuf[TIME_BUF_LEN];
    strftime(timebuf, TIME_BUF_LEN, "%Y-%m-%d %H:%M:%S", gmtime(&t));

    fprintf(stderr, "[%s] %s,000: ", lvl, timebuf);
    vfprintf(stderr, fmt, args);
    fprintf(stderr, "\n");
}


void log_info(const char* fmt, ...) {
    if (current_log_level <= LOG_LVL_INFO) {
        va_list args;
        va_start(args, fmt);
        log_unconditional("INFO", fmt, args);
        va_end(args);
    }
}


void log_fatal(const char* fmt, ...) {
    if (current_log_level <= LOG_LVL_CRITICAL) {
        va_list args;
        va_start(args, fmt);
        log_unconditional("CRITICAL", fmt, args);
        va_end(args);
        exit(2);
    }
}
