#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import threading


class LogPipe(threading.Thread):

    def __init__(self, level, log_name=None):
        """Setup the object with a logger and a loglevel and start the thread """
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
