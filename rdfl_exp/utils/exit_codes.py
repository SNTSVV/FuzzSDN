#!/usr/bin/env python3
from enum import IntEnum


class ExitCode(IntEnum):
    """
    Enum class that defines standards exit codes and can be used with SystemExit
    """
    UNDEF               = -1  # Used when an error code is not defined

    OK                  = 0  # No error occurred.
    ERROR               = 1  #
    SHELL_ERROR         = 2  # Misuse of shell builtins(according to Bash documentation)
    CMD_CANT_EXEC       = 126  # Command cannot be executed
    CMD_NOT_FOUND       = 127  # Command not found
    INVALID_EXIT_ARG    = 128  # Invalid argument to exit
    TERM_CTRL_C         = 130  # Terminated by CTRL+C

    # Exit codes commonly used with Python
    PY_USAGE            = 64  # Specified command was used incorrectly, such as when the wrong number of arguments are given.
    PY_DATA_ERR         = 65  # Specified input data was incorrect.
    PY_NO_INPUT         = 66  # Specified input file did not exist or was not readable.
    PY_NO_USER          = 67  # Specified user did not exist.
    PY_NO_HOST          = 68  # Specified host did not exist.
    PY_UNAVAILABLE      = 69  # A required service is unavailable.
    PY_SOFTWARE         = 70  # An internal software error was detected.
    PY_OS_ERR           = 71  # An operating system error was detected, such as the inability to fork or create a pipe.
    PY_OS_FILE          = 72  # Some system file did not exist, could not be opened, or had some other kind of error.
    PY_CANT_CREAT       = 73  # A user specified output file could not be created.
    PY_IOERR            = 74  # An error occurred while doing I/O on some file.
    PY_TEMPFAIL         = 75  # Temporary failure occurred. This indicates something that may not really be an error, such as a network connection that couldn’t be made during a retryable operation.
    PY_PROTOCOL         = 76  # A protocol exchange was illegal, invalid, or not understood.
    PY_NO_PERM          = 77  # Insufficient permissions to perform the operation (but not intended for file system problems).
    PY_CONFIG           = 78  # Some kind of configuration error occurred.
    PY_NOT_FOUND        = 79  # Something like "an entry was not found".

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
    # End def ExitCode

if __name__ == '__main__':
    print(ExitCode(80))