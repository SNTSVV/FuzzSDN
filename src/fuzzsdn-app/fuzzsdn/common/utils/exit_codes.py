# -*- coding: utf-8 -*-

import os
from enum import IntEnum


class ExitCode(IntEnum):
    """
    Enum class that wraps around standards exit codes and can be used with SystemExit
    """
    UNDEF               = -1                    # Used when an error code is not defined
    EX_OK               = os.EX_OK              # No error occurred.
    EX_SHELLERROR       = 2                     # Misuse of shell builtins(according to Bash documentation)
    EX_CANTEXEC         = 126                   # Command cannot be executed
    EX_CMDNOTFOUND      = 127                   # Command not found
    EX_INVALIDEXITARG   = 128                   # Invalid argument to exit
    EX_CTRLC            = 130                   # Terminated by CTRL+C
    EX_USAGE            = os.EX_USAGE           # Specified command was used incorrectly, such as when the wrong number of arguments are given.
    EX_DATAERR          = os.EX_DATAERR         # Specified input data was incorrect.
    EX_NOINPUT          = os.EX_NOINPUT         # Specified input file did not exist or was not readable.
    EX_NOUSER           = os.EX_NOUSER          # Specified user did not exist.
    EX_NOHOST           = os.EX_NOHOST          # Specified host did not exist.
    EX_UNAVAILABLE      = os.EX_UNAVAILABLE     # A required service is unavailable.
    EX_SOFTWARE         = os.EX_SOFTWARE        # An internal software error was detected.
    EX_OSERR            = os.EX_OSERR           # An operating system error was detected, such as the inability to fork or create a pipe.
    EX_OSFILE           = os.EX_OSFILE          # Some system files did not exist, could not be opened, or had some other kind of error.
    EX_CANTCREAT        = os.EX_CANTCREAT       # A user specified output file could not be created.
    EX_IOERR            = os.EX_IOERR           # An error occurred while doing I/O on some file.
    EX_TEMPFAIL         = os.EX_TEMPFAIL        # Temporary failure occurred. This indicates something that may not really be an error, such as a network connection that couldn't be made during a retryable operation.
    EX_PROTOCOL         = os.EX_PROTOCOL        # A protocol exchange was illegal, invalid, or not understood.
    EX_NOPERM           = os.EX_NOPERM          # Insufficient permissions to perform the operation (but not intended for file system problems).
    EX_CONFIG           = os.EX_CONFIG          # Some kind of configuration error occurred.
    EX_NOTFOUND         = os.EX_NOTFOUND if hasattr(os, 'EX_NOTFOUND') else UNDEF  # Something like "an entry was not found".

    @classmethod
    def has_member_for_value(cls, value):
        return value in cls._value2member_map_
    # End def has_member_for_value

# End class exit_code
