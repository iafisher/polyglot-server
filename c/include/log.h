/**
 * Logging for the server.
 *
 * Author:  Ian Fisher (iafisher@protonmail.com)
 * Version: August 2018
 */

#ifndef MY_LOG_H
#define MY_LOG_H

typedef enum { LOG_LVL_DEBUG, LOG_LVL_INFO, LOG_LVL_CRITICAL, LOG_LVL_NONE } 
    log_level_t;

void set_logging_level(log_level_t);

void log_info(const char* fmt, ...);
void log_fatal(const char* fmt, ...);

#endif
