#!/bin/env python3
import logging
import os

from figsdn.app import setup
from figsdn.app.analytics.log import LOG_RGX, LogParser
from figsdn.common.openflow.v0x05.error import ErrorType


class RyuLogParser(LogParser):
    """
    Log Parser class for RYU SDN Controller
    """

    def __init__(self):
        super().__init__()
        self.__log = logging.getLogger(__name__)
        self.__log_path = os.path.join(os.path.expanduser(setup.config().ryu.log_dir), 'ryu.log')
    # End def __init__

    def parse_log(self, path=None):
        """

        :return: has_error, error_type, error_reason, error_effect, log_trace
        """
        self.__log.info("Parsing RYU log file at: \"{}\"".format(self.__log_path if path in (None, '') else path))
        # Read the log first
        if path is None or path == '':
            self.load_from_file(self.__log_path)
        else:
            self.load_from_file(path)

        has_error = False
        error_type = None
        error_reason = None
        error_effect = None

        matches = super()._match(LOG_RGX['RYU'])

        for key_match in matches:
            key = key_match['rgx_key']
            match = key_match['match']

            if not has_error:
                if key == 'PARSING_ERROR':
                    has_error = True
                    error_type = 'PARSING_ERROR'

                if key == "OPF_ERROR":
                    has_error = True
                    error_type = "OPENFLOW_ERROR"

                    # Translate the type and code from hex number to dec numbers
                    error_reason = ErrorType(int(match['type'], 16)).code_class(int(match['code'], 16)).name

                if 'key' in 'EXCEPTION':
                    has_error = True
                    error_type = 'GENERIC_ERROR'
                    if 'KeyError' in match['type']:
                        if 'in_port' in match['reason']:
                            error_reason = 'BAD_IN_PORT'
                    else:
                        error_reason = "{} {}".format(match['type'], match['reason'])

            else:
                if error_type == 'PARSING_ERROR' and key == 'EXCEPTION':
                    if 'AssertionError' in match['type']:
                        error_reason = 'ASSERTION_ERROR'
                    elif 'struct.error' in match['type']:
                        if 'requires a buffer of at least' in match['reason']:
                            error_reason = 'BUFFER_OVERFLOW'
                        else:
                            error_reason = match['reason']
                    elif 'Exception' in match['type'] and 'Unexpected OXM payload' in match['reason']:
                        error_reason = 'BAD_OXM_PAYLOAD'
                    else:
                        error_reason = "{} {}".format(match['type'], match['reason'])

        return has_error, error_type, error_reason, error_effect, self.log_trace
    # End def parse_log
# End class RyuLogParser
