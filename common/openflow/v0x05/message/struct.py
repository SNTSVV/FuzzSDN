# -*- coding: utf-8 -*-
"""
Utility module that gives the structure of a message
"""
from common.openflow.v0x05.common.message import ofp_type


# TODO: Construct it automatically from matches, etc, etc,
def get_msg_struct(type_ : ofp_type, **kwargs):
    """
    Return a struct that characterize the format of a message
    :param type_:
    :param kwargs:
    :return:
    """

    struct = list()

    if type_ == ofp_type.OFPT_PACKET_IN:

        struct.extend([
            {"name": "version"          , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "of_type"          , "size":  8, "min": 0, "max": int(pow(2, 8 * 1) - 1)},
            {"name": "length"           , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "xid"              , "size": 32, "min": 0, "max": int(pow(2, 8 * 4) - 1)},
            {"name": "buffer_id"        , "size": 32, "min": 0, "max": int(pow(2, 8 * 4) - 1)},
            {"name": "total_len"        , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "reason"           , "size":  8, "min": 0, "max": int(pow(2, 8 * 1) - 1)},
            {"name": "table_id"         , "size":  8, "min": 0, "max": int(pow(2, 8 * 1) - 1)},
            {"name": "cookie"           , "size":  8, "min": 0, "max": int(pow(2, 8 * 8) - 1)},
            {"name": "match_type"       , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "match_length"     , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "match_pad"        , "size": 32, "min": 0, "max": int(pow(2, 8 * 4) - 1)},
            {"name": "oxm_0_class"      , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "oxm_0_field"      , "size":  7, "min": 0, "max": int(pow(2, 7) - 1)},
            {"name": "oxm_0_has_mask"   , "size":  1, "min": 0, "max": 1},
            {"name": "oxm_0_length"     , "size":  8, "min": 0, "max": int(pow(2, 8 * 1) - 1)},
            {"name": "oxm_0_value"      , "size": 32, "min": 0, "max": int(pow(2, 8 * 4) - 1)},
            {"name": "pad"              , "size":  8, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "eth_dst"          , "size": 48, "min": 0, "max": int(pow(2, 8 * 6) - 1)},
            {"name": "eth_src"          , "size": 48, "min": 0, "max": int(pow(2, 8 * 6) - 1)},
            {"name": "ethertype"        , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "arp_htype"        , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "arp_ptype"        , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "arp_hlen"         , "size":  8, "min": 0, "max": int(pow(2, 8 * 1) - 1)},
            {"name": "arp_plen"         , "size":  8, "min": 0, "max": int(pow(2, 8 * 1) - 1)},
            {"name": "arp_oper"         , "size": 16, "min": 0, "max": int(pow(2, 8 * 2) - 1)},
            {"name": "arp_sha"          , "size": 48, "min": 0, "max": int(pow(2, 8 * 6) - 1)},
            {"name": "arp_spa"          , "size": 32, "min": 0, "max": int(pow(2, 8 * 4) - 1)},
            {"name": "arp_tha"          , "size": 48, "min": 0, "max": int(pow(2, 8 * 6) - 1)},
            {"name": "arp_tpa"          , "size": 32, "min": 0, "max": int(pow(2, 8 * 4) - 1)}
        ])

    else:
        raise AttributeError("Unknown Openflow (0x05) message \"{}\"".format(type_))

    return struct
# End def get_msg_struct
