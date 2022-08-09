#!/bin/env python3
import logging
import os.path
import re
from typing import Optional

from figsdn.app.analytics.log import LOG_RGX, LogParser
from figsdn.app import setup


class OnosLogParser(LogParser):
    """
    Log Parser class for ONOS SDN Controller
    """

    def __init__(self):
        super().__init__()
        self.__log = logging.getLogger(__name__)
        try:
            self.__log_dir = os.path.join(os.path.expanduser(setup.config().onos.root_dir), 'karaf', 'data', 'log')
        except AttributeError:
            self.__log.warning("Couldn't find log directory to onos.")
            self.__log_dir = None
    # End def __init__

    def parse_log(self, path : Optional[str] = None, pattern : Optional[re.Pattern] = None, concatenate : bool = True, reverse : bool = False):
        self.__log.info("Parsing ONOS log file at: \"{}\"".format(self.__log_dir if path in (None, '') else path))
        # Read the log first
        if path is None or path == '':
            self.load_from_file(self.__log_dir,
                                pattern=re.compile(r'karaf(-\d+)*\.log', re.I),
                                concatenate=True,
                                reverse=False)
        else:
            self.load_from_file(path,
                                pattern=pattern,
                                concatenate=concatenate,
                                reverse=reverse)

        has_error = False
        error_type = None
        error_reason = None
        error_effect = None
        
        hello_happened = False

        connected_switches = list()

        self.__log.debug("Detecting error tokens the log...")
        key_and_matches = self._match(LOG_RGX['ONOS'])

        for key_match in key_and_matches:
            # When no error was previously detected
            rgx_key = key_match['rgx_key']
            rgx_match = key_match['match']

            if rgx_key == 'SWITCH_CONNECTION':
                connected_switches.append(str(rgx_match['ip_addr']))  # Add the

            # If there is no hello message yet, then nothing should be processed
            if hello_happened is False:
                if rgx_key == 'OF_HELLO':
                    hello_happened = True
                elif rgx_key == 'PROCESSING_ERROR_HELLO':
                    self.__log.trace("Hello processing error detected.")
                    hello_happened = True
                    has_error = True
                    error_type = 'PROCESSING_ERROR'

            else:
                if has_error is False:
                    if rgx_key == 'PROCESSING_ERROR':
                        self.__log.trace("Processing error detected.")
                        has_error = True
                        error_type = 'PROCESSING_ERROR'
                        continue  # Process the next match

                    elif rgx_key == 'OPENFLOW_ERROR':
                        self.__log.trace("OpenFlow error detected.")
                        has_error = True
                        error_type = 'OPENFLOW_ERROR'
                        error_reason = rgx_match['code']
                        continue  # Process the next match

                    elif rgx_key == 'PKT_DESERIALIZATION_ERROR':
                        self.__log.trace("Packet Deserialization Error detected.")
                        has_error = True
                        error_type = 'PKT_DESERIALIZATION_ERROR'
                        if 'null' in str(rgx_match['reason']).lower():
                            error_reason = None
                        else:
                            error_reason = rgx_match['reason']
                        continue  # Process the next match

                    elif rgx_key == 'OF_BAD_REQUEST_ERROR':
                        self.__log.trace("OF_BAD_REQUEST_ERROR detected")
                        has_error = True
                        error_type = 'OPENFLOW_ERROR'
                        error_reason = 'OF_BAD_REQUEST_ERROR'
                        continue

                    elif rgx_key == 'SWITCH_STATE_ERROR':
                        self.__log.trace("Switch State error detected")
                        has_error = True
                        error_type = 'SWITCH_STATE_ERROR'
                        print('here')
                        if 'switch should never send this message in the current state' in str(rgx_match['reason']).lower():
                            error_reason = 'received \"{}\" in state \"{}\"'.format(rgx_match['received'], rgx_match['state'])
                        else:
                            error_reason = '({} (received: \"{}\", state: \"{}\")'.format(str(rgx_match['reason']).lower(),
                                                                                          rgx_match['received'],
                                                                                          rgx_match['state'])
                        continue

                # If there already was an error
                else:
                    # If the previous error is a processing error
                    if error_type == 'PROCESSING_ERROR':
                        # If its an exception in the decoder...
                        if rgx_key == 'DECODER_EXCEPTION':
                            if "OFParseError" in rgx_match['exception']:
                                self.__log.trace("OFParseError detected (reason: \"{}\")".format(rgx_match['reason']))
                                error_type = 'PARSING_ERROR'
                                error_reason = rgx_match['reason']

                            elif 'NullPointerException' in rgx_match['exception']:
                                self.__log.trace("NullPointerException detected (reason: \"{}\")".format(rgx_match['reason']))
                                error_type = 'NULL_POINTER_EXCEPTION'
                                if str(rgx_match['reason']).lower() == 'null':
                                    error_reason = None
                                else:
                                    error_reason = rgx_match['reason']
                            elif 'IllegalArgumentException' in rgx_match['exception']:
                                self.__log.trace("IllegalArgumentException detected (reason: \"{}\")".format(rgx_match['reason']))
                                error_type = 'ILLEGAL_ARGUMENT_EXCEPTION'
                                if str(rgx_match['reason']).lower() == 'null':
                                    error_reason = None
                                else:
                                    error_reason = rgx_match['reason']
                            else:
                                self.__log.trace("Unknown Exception (exception: {}, reason: \"{}\")".format(rgx_match['exception'], rgx_match['reason']))
                                error_type = "UNKNOWN: {}".format(rgx_match['exception'])
                                error_reason = rgx_match['reason']
                            continue  # Process the next match

            # Find if there is a switch disconnection
            if rgx_key in ('SWITCH_DISCONNECTED_STD', 'SWITCH_DISCONNECTED_NICIRA', 'SWITCH_DISCONNECTED_HELLO'):
                if has_error is True:
                    self.__log.trace("Switch disconnection detected")
                    error_effect = 'SWITCH_DISCONNECTED'

        return has_error, error_type, error_reason, error_effect, self.log_trace
    # End def parse_log
# End class OnosLogParser



if __name__ == '__main__':

    from figsdn.common.utils.log import add_logging_level
    add_logging_level('TRACE', logging.DEBUG - 1)

    parser = OnosLogParser()

    results = parser.parse_log('/Users/raphael.ollando/',
                               pattern=re.compile(r'test_log(\d+)*\.log', re.I),
                               concatenate=True,
                               reverse=False
                              )
    print(results[-1])