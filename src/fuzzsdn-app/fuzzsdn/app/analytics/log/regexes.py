#!/bin/env python3

# Dictionary of regexes used by ONOS
LOG_RGX = {

    'ONOS': {
        # Switch connection to ONOS
        'SWITCH_CONNECTION': r'(?<=New\sswitch\sconnection\sfrom\s/)'              # Match the message
                             r'(?P<ip_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:*\d{1,5})?)',     # Match the IP address

        # Switch added to ONOS Flow table
        'ADDED_SWITCH': r'Added\sswitch\s'                                          # Match added switch
                        r'(?P<mac_addr>(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})',   # Match the mac address

        # Switch Disconnected
        'SWITCH_DISCONNECTED_NICIRA':  r'Switch\sdisconnected\scallback\sfor\ssw:NiciraSwitchHandshaker{'           # Match message
                                       r'session=(?P<ip_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:*\d{1,5})?),\s'    # Match session
                                       r'dpid=(?P<dpid>(?:[0-9A-Fa-f]{2}[:-]){7}[0-9A-Fa-f]{2})}'                   # Match dpid
                                       r'\.\sCleaning\sup',                                                         # Match message

        # Switch Disconnected
        'SWITCH_DISCONNECTED_STD': r'Switch\sdisconnected\scallback\sfor\ssw:'
                                   r'\[\/(?P<ip_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:*\d{1,5})?)\s'
                                   r'DPID\[(?P<dpid>(?:[0-9A-Fa-f]{2}[:-]){7}[0-9A-Fa-f]{2})\]\]'
                                   r'\.\sCleaning\sup',

        # Switch Disconnected
        'SWITCH_DISCONNECTED_HELLO': r'Switch\sdisconnected\scallback\sfor\ssw:'
                                     r'\[\/(?P<ip_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:*\d{1,5})?)\s'
                                     r'DPID\[\?\]\]'
                                     r'\.\sCleaning\sup',


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

        'PROCESSING_ERROR_HELLO': r'Error\swhile\sprocessing\smessage\sfrom\sswitch\s\[\/'
                                  r'(?P<IP>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d{1,5}'
                                  r'\sDPID\[\?\]\]\s*state\sWAIT_HELLO',

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
                                      r',\scode=(?P<code>[^,]*)',                   # Match the error code

        'OF_BAD_REQUEST_ERROR':       r'OFBadRequestErrorMsgVer\d{0-2}\('
                                      r'xid=(?P<xid>\d+), code=BAD_VERSION, data=(?P<data>.*\))'
                                      r'\sfrom\sswitch\s\[\/'
                                      r'(?P<IP>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})\s'
                                      r'DPID\[(?P<DPID>(?:[0-9A-Fa-f]{2}[:-]){7}[0-9A-Fa-f]{2})]]'
                                      r'\sin\sstate\s(?P<state>.*)',
        
        'SWITCH_STATE_ERROR': r'Disconnecting\sswitch.*due\sto\sswitch\sstate\serror:'                  # Switch state error message
                              r'\sSwitch:\s\[\[\/(?P<IP>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})'    # IP
                              r'\sDPID\[(?P<DPID>(?:[0-9A-Fa-f]{2}[:-]){7}[0-9A-Fa-f]{2})\]\]\],\s'     # DPID
                              r'State:\s\[(?P<state>.*)\],\s'                                           # state
                              r'received:\s\[(?P<received>.*)\],\s'                                     # received
                              r'details:\s(?P<reason>.*)'                                               # Reason
    },

    'RYU': {
        # Matches an EVENT
        'EVENT':            r'EVENT\s+'             # Match event token
                            r'(?P<event>.*)',       # Match event message into event group

        'HELLO_EVENT': r'hello\sev\s<(?P<event>.*)>',  #

        'OPF_ERROR':  r'OFPErrorMsg\('                                      # Match the beginning of the error message
                      r'type=(?P<type>0[xX][0-9a-fA-F]+)'                   # Match the error message
                      r',\scode=(?P<code>0[xX][0-9a-fA-F]+)'                # Match the code
                      r',\sdata=(?P<data>b\'(?:\\x[0-9a-fA-F]{2})*\')\)',   # Match the data byte string

        # Match Parsing errors
        'PARSING_ERROR':    r'Encountered an error while parsing OpenFlow packet from switch.\s'
                            r'This implies the switch sent a malformed OpenFlow packet\.\s*'
                            r'(?P<message>.+)',     # Match the of message

        # Matches an exception and parses it
        'EXCEPTION':        r'Traceback \(most recent call last\):'                 # Match literally
                            r'(?:\n.*)+?'                                           # Repeat in a non capturing group matching a newline followed by 0+ times any character
                            r'\n(?P<type>\S*?(?:exception|error|Error|Exception))'   # Match newline and capturing group "type" 0+ characters non greedy and than match Exception of Error followed by ":"
                            r':?[^\S\n]*'                                           # Match a ":" plus a whitespace characters
                            r'(?P<reason>.+)?',                                     # Capturing group 1+ times any character as the reason


    }
}

