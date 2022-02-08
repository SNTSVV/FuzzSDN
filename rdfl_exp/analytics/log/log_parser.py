#!/bin/env python3
import mmap
import os
import re
import shutil
from typing import List

import rdfl_exp.setup


class LogParser:
    """
    LogParser is the base class for any log parsing operation
    """

    def __init__(self):
        self._cached_log = os.path.join(rdfl_exp.setup.tmp_dir(), "{}_cached_log".format(id(self)))
        self._loaded = False
    # End def init

    # ===== ( Properties ) =============================================================================================

    @property
    def log_trace(self):
        if self._cached_log is None:
            return RuntimeError("No log loaded")

        with open(self._cached_log, 'r') as f:
            log_trace = "".join(f.readlines())

        return log_trace
    # End def log_trace

    # ===== ( Methods ) ================================================================================================

    def parse_log(self):
        """
        Parse the log file and output a tuple with
        :return:
        """
        raise NotImplementedError()
    # End def parse_log

    def load_from_file(self, log_path):
        """
        Load a log file by copying it into a temporary file.
        :param log_path: The path to the file
        """
        shutil.copy(log_path, self._cached_log)
        self._loaded = True
    # End def load_from_file

    def load_from_string(self, log_str):
        """
        Load a log file from a string by writing it into a temporary file.
        :param log_str: The path to the file
        """
        with open(self._cached_log, 'w') as f:
            f.write(log_str)
        self._loaded = True
    # End def load_from_string

    # ===== ( Protected Methods ) ======================================================================================

    def _match(self, regexes: dict) -> List[dict]:
        """
        Parse the cached log file and outputs a list of matches, ordered by appearance, to be further processed by a
        specialized log parser or by the user.

        :param regexes: A dictionary of regex with the name of the regex has key and a regex string as values
        :return: a list dictionaries with a regex key and a match, sorted by the order in which they appear
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
