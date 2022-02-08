#!/bin/env python3

# Dictionary of regexes used by ONOS
LOG_RGX = {

    'ONOS': {
        # Switch connection to ONOS
        'SWITCH_CONNECTION': r'(?<=New\sswitch\sconnection\sfrom\s/)'              # Match the message
                             r'(?P<ip_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'     # Match the ip address
                             r':*(?P<port>\d{1,5})',                                # Match the port if it is given

        # Switch added to ONOS Flow table
        'ADDED_SWITCH': r'Added\sswitch\s'                                          # Match added switch
                        r'(?P<mac_addr>(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})',   # Match the mac address

        # Switch Disconnected
        'SWITCH_DISCONNECTED': r'Switch\sdisconnected\scallback\sfor\ssw:NiciraSwitchHandshaker{'           # Match message
                               r'session=(?P<session>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d{1,5},\s'    # Match session
                               r'dpid=(?P<dpid>(?:[0-9A-Fa-f]{2}[:-]){7}[0-9A-Fa-f]{2})}'               # Match dpid
                               r'\.\sCleaning\sup',                                                         # Match message


        # ONOS controller send HELLO Message
        'OF_HELLO': r'Sending\s'
                    r'(?P<version>OF_\d{1,2})\sHello'                   # Match the version of the Hello message
                    r'\sto\s/'                                         
                    r'(?P<ip_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # Match the IP address
                    r':*(?P<port>\d{1,5})',                             # Match the port

        # ONOS Parsing Error
        'PROCESSING_ERROR': r'Error\swhile\sprocessing\smessage\sfrom\s'
                            r'switch\sNiciraSwitchHandshaker{'
                            r'session=(?P<session>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d{1,5},\s'
                            r'dpid=(?P<dpid>(?:[0-9A-Fa-f]{2}[:-]){7}[0-9A-Fa-f]{2})}',

        # Matches Traceback and parse the error
        'TRACEBACK': r'Traceback \(most recent call last\):'                                 # Match the traceback
                     r'(?:\n.*)+?\n(?P<type>.*?(?:exception|error|Error|Exception):)\s*'     # Match the type
                     r'(?P<reason>.+)',                                                      # Match the reason


        'DECODER_EXCEPTION': r'io\.netty\.handler\.codec\.DecoderException:\s'
                             r'(?P<exception>[^:]*):\s'
                             r'(?P<reason>.*)',

        # packet deserialization error
        'PKT_DESERIALIZATION_ERROR': r'Packet\sdeserialization\sproblem\n?'     # Match the message
                                     r'(?P<exception>[^:]*)\s?:\s?'             # Match the exception
                                     r'(?P<reason>.*)',                         # Match the reason

        # Standard OF Error Message
        'OPENFLOW_ERROR':             r'Received\serror\smessage\s(?P<msg>[^(]*)'  # Match the error type
                                      r'\(xid=(?P<xid>[^,]*)'                       # Match the XID
                                      r',\scode=(?P<code>[^,]*)'                    # Match the error code
    }
}
