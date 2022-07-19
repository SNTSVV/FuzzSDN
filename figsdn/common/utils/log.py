#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import threading


# ====== ( Utility classes ) ===========================================================================================

class LogPipe(threading.Thread):

    def __init__(self, level, log_name=None):
        """Set up the object with a logger and a loglevel and start the thread """
        threading.Thread.__init__(self)
        self.daemon = False

        self.logger = logging.getLogger(__name__ if log_name is None else log_name)
        self.level = level
        self.fdRead, self.fdWrite = os.pipe()
        self.pipeReader = os.fdopen(self.fdRead)

        self.start()
    # End def __init__

    def fileno(self):
        """Return the write file descriptor of the pipe"""
        return self.fdWrite

    # End def fileno

    def run(self):
        """Run the thread, logging everything."""
        for line in iter(self.pipeReader.readline, ''):
            self.logger.log(self.level, line.strip('\n'))

        self.pipeReader.close()

    # End def run

    def close(self):
        """Close the write end of the pipe."""
        os.close(self.fdWrite)
    # End def close()
# End class LogPipe

# ====== ( Utility functions ) =========================================================================================


def add_logging_level(level_name, level_num, method_name=None):
    """Comprehensively adds a new logging level to the `logging` module and the currently configured logging class.

    To avoid accidental clobberings of existing attributes, this method will raise an `AttributeError` if the level name
    is already an attribute of the `logging` module or if the method name is already present

    Example
    -------
    >>> add_logging_level('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5
    ------

    Args:
        level_name: becomes an attribute of the `logging` module with the value
        level_num:
        method_name: becomes a convenience method for both `logging`
                     itself and the class returned by `logging.getLoggerClass()` (usually just
                     `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
                     used.

    Raises:
        AttributeError: to avoid accidental clobberings of existing attributes if the level name is already an
                        attribute of the `logging` module or if the method name is already present
    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError('{} already defined in `logging` module'.format(level_name))
    if hasattr(logging, method_name):
        raise AttributeError('{} already defined in `logging` module'.format(method_name))
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError('{} already defined in logger class'.format(method_name))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)
# End def add_logging_level