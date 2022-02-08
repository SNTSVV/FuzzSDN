#!/bin/env python3
import logging
import os.path

from rdfl_exp.analytics.log.log_parser import LogParser
from rdfl_exp.analytics.log.regexes import LOG_RGX
from rdfl_exp.config import DEFAULT_CONFIG as CONFIG


class OnosLogParser(LogParser):

    def __init__(self):
        super().__init__()
        self.__log = logging.getLogger(__name__)
        self.__log_path = os.path.join(os.path.expanduser(CONFIG.onos.root_dir), 'karaf', 'data', 'log', 'karaf.log')

    def parse_log(self):
        self.__log.info("Parsing ONOS log file at: \"{}\"".format(self.__log_path))
        # Read the log first
        self.__log.debug("Loading the file...")
        self.load_from_file(self.__log_path)

        has_error = False
        error_type = None
        error_reason = None
        error_effect = None

        self.__log.debug("Detecting error tokens the log...")
        matches = self._match(LOG_RGX['ONOS'])

        for match in matches:
            # When no error was previously detected
            if has_error is False:
                if match['rgx_key'] == 'PROCESSING_ERROR':
                    self.__log.trace("Processing error detected.")
                    has_error = True
                    error_type = 'PROCESSING_ERROR'
                    continue  # Process the next match

                elif match['rgx_key'] == 'OPENFLOW_ERROR':
                    self.__log.trace("OpenFlow error detected.")
                    has_error = True
                    error_type = 'OPENFLOW_ERROR'
                    error_reason = match['match']['code']
                    continue  # Process the next match

                elif match['rgx_key'] == 'PKT_DESERIALIZATION_ERROR':
                    self.__log.trace("Packet Deserialization Error detected.")
                    has_error = True
                    error_type = 'PKT_DESERIALIZATION_ERROR'
                    error_reason = "{}: {}".format(match['match']['exception'], match['match']['reason'])
                    continue  # Process the next match
            # If there already was an error
            else:
                # If the previous error is a processing error
                if error_type == 'PROCESSING_ERROR':
                    # If its an exception in the decoder...
                    if match['rgx_key'] == 'DECODER_EXCEPTION':
                        if "OFParseError" in match['match']['exception']:
                            self.__log.trace("OFParseError detected (reason: \"{}\")".format(match['match']['reason']))
                            error_type = 'PARSING_ERROR'
                            error_reason = match['match']['reason']

                        elif 'NullPointerException' in match['match']['exception']:
                            self.__log.trace("NullPointerException detected (reason: \"{}\")".format(match['match']['reason']))
                            error_type = 'NULL_POINTER_EXCEPTION'
                            error_reason = match['match']['reason']

                        else:
                            self.__log.trace("Unknown Exception (exception: {}, reason: \"{}\")".format(match['match']['exception'], match['match']['reason']))
                            error_type = "UNKNOWN: {}".format(match['match']['exception'])
                            error_reason = match['match']['exception']
                        continue  # Process the next match

                # If there is an error and we detect a switch disconnection
                if match['rgx_key'] == 'SWITCH_DISCONNECTED' and has_error is True:
                    self.__log.trace("Switch disconnection detected")
                    error_effect = 'SWITCH_DISCONNECTED'

        return has_error, error_type, error_reason, error_effect, self.log_trace

    # End def parse_log
# End class OnosLogParser
