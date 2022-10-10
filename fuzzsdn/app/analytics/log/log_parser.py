#!/bin/env python3
import mmap
import os
import re
import shutil
from typing import List, Optional

from fuzzsdn.common import app_path


class LogParser:
    """
    LogParser is the base class for any log parsing operation
    """

    def __init__(self):
        self._cached_log = os.path.join(app_path.tmp_dir(), "{}_cached_log".format(id(self)))
        self._loaded = False
    # End def init

    # ===== ( Properties ) =============================================================================================

    @property
    def log_trace(self):
        if self._cached_log is None:
            return AttributeError("No logs cached.")

        with open(self._cached_log, 'r') as f:
            log_trace = "".join(f.readlines())

        return log_trace
    # End def log_trace

    # ===== ( Methods ) ================================================================================================

    def parse_log(self):
        """Parse the log file and output a tuple with the informations."""
        raise NotImplementedError('subclasses must override parse_log()!')
    # End def parse_log

    def load_from_file(self, path : str, pattern : Optional[re.Pattern] = None, concatenate : bool = True, reverse : bool = False):
        """Load a log file by copying it into a temporary file.

        Args:
            path (str)          : The path to the directory where the log files are located.
            pattern (re)        : The match pattern (use re.compile(<pattern>, <flags>))
            concatenate (bool)  : If set to true, all the files matching the pattern are concatenated into a single log
                                file. If set to False, it's only the last one in the sorted list.
            reverse (bool)      : Concatenate the files in a reversed fashion
        """

        if os.path.isdir(path):
            if pattern is None:
                raise RuntimeError("{} is a directory and no pattern was given.")

            # List all the files that match the pattern
            log_names = [os.path.join(path, f) for f in os.listdir(path) if pattern.match(f)]

            # If concatenate is true, concatenate all the logs
            if concatenate is True and len(log_names) > 1:
                with open(self._cached_log, 'w') as out_file:
                    for f_name in sorted(log_names, reverse=reverse):
                        with open(f_name) as in_file:
                            for line in in_file:
                                out_file.write(line)

            # Else, just copy the last file
            elif len(log_names) > 0:
                shutil.copy(sorted(log_names, reverse=reverse)[-1], self._cached_log)

            else:
                raise RuntimeError("Couldn't find any log message, matching pattern '{}' under '{}'".format(pattern.pattern, path))

        # If it's a just a file, copy the log file to the cache.
        else:
            shutil.copy(path, self._cached_log)

        # Signal that the file is loaded
        self._loaded = True
    # End def load_from_file

    def load_from_string(self, log_str):
        """Load a log file from a string by writing it into a temporary file.

        Args:
            log_str: The path to the file
        """
        with open(self._cached_log, 'w') as f:
            f.write(log_str)
        self._loaded = True
    # End def load_from_string

    # ===== ( Protected Methods ) ======================================================================================

    def _match(self, regexes: dict) -> List[dict]:
        """Parse the cached log file and outputs a list of matches.

        The matches are ordered by appearance, to be further processed by a specialized log parser or by the user.

        Args:
            regexes: A dictionary of regex with the name of the regex has key and a regex string as values

        Returns:
            A list dictionaries with a regex key and a match, sorted by the order in which they appear
        """
        matches = []
        with open(self._cached_log, 'r+') as f:
            # map the file to memory to avoid too many copies
            mm_log_file = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ).read().decode("utf-8")

        for rgx_key in regexes.keys():
            for match in re.finditer(regexes[rgx_key], mm_log_file):
                matches.append({'rgx_key': rgx_key, 'match': match})

        # Sort the regex by their match position
        return sorted(matches, key=lambda m: m['match'].start())
    # End def _match

# End class LogParser
