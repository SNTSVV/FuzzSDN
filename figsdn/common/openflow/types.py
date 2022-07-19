"""Defines of enum for errors on openflow v1.4 (0x05)."""

from enum import IntEnum


class ofp_type(IntEnum):
    """
    Values for ’type’ in ofp_message.

    These values are immutable: they will not change in future versions of the protocol (although new values may be
    added).
    """
    # Immutable messages
    OFPT_HELLO              = 0
    OFPT_ERROR              = 1
    OFPT_ECHO_REQUEST       = 2
    OFPT_ECHO_REPLY         = 3
    OFPT_EXPERIMENTER       = 4

    # Switch configuration messages.
    OFPT_FEATURES_REQUEST   = 5,
    OFPT_FEATURES_REPLY     = 6,
    OFPT_GET_CONFIG_REQUEST = 7,
    OFPT_GET_CONFIG_REPLY   = 8,
    OFPT_SET_CONFIG         = 9,

    # Asynchronous messages.
    OFPT_PACKET_IN          = 10
    OFPT_FLOW_REMOVED       = 11
    OFPT_PORT_STATUS        = 12

    # Controller command messages.
    OFPT_PACKET_OUT         = 13
    OFPT_FLOW_MOD           = 14
    OFPT_GROUP_MOD          = 15
    OFPT_PORT_MOD           = 16
    OFPT_TABLE_MOD          = 17

    # Multipart messages.
    OFPT_MULTIPART_REQUEST  = 18
    OFPT_MULTIPART_REPLY    = 19

    # Barrier messages
    OFPT_BARRIER_REQUEST    = 20
    OFPT_BARRIER_REPLY      = 21

    # Controller role change request messages.
    OFPT_ROLE_REQUEST       = 24,
    OFPT_ROLE_REPLY         = 25,

    # Asynchronous message configuration.
    OFPT_GET_ASYNC_REQUEST  = 26,
    OFPT_GET_ASYNC_REPLY    = 27,
    OFPT_SET_ASYNC          = 28,

    # Meters and rate limiters configuration messages.
    OFPT_METER_MOD          = 29,

    # Controller role change event messages.
    OFPT_ROLE_STATUS        = 30,

    # Asynchronous messages.
    OFPT_TABLE_STATUS       = 31,

    # Request forwarding by the switch
    OFPT_REQUESTFORWARD     = 32,

    # Bundle operations(multiple messages as a single operation).
    OFPT_BUNDLE_CONTROL     = 33,
    OFPT_BUNDLE_ADD_MESSAGE = 34,

    # Controller Status async message.
    OFPT_CONTROLLER_STATUS  = 35,
# End def ofp_type