#!/usr/bin/env python3
# coding: utf-8
import base64
import binascii
import struct
import traceback

import pandas as pd


# ==== ( Filters ) =============================================================
def filter_boolean(x):
    if x == "None":
        return False
    else:
        return x


def filter_reason(x):
    if not hasattr(filter_reason, "table"):
        filter_reason.table = {
            0x00: 'reason_NoMatch',
            0x01: 'reason_Action',
            0x02: 'reason_InvalidTTL'
        }
    return filter_reason.table.get(int(x), 'reason_Illegal')
##############################################


def filter_oxm_class(x):
    if not hasattr(filter_oxm_class, "table"):
        filter_oxm_class.table = {
            0x0000: 'oxm_class_NXM_0',
            0x0001: 'oxm_class_NXM_1',
            0x8000: 'oxm_class_OPENFLOW_BASIC',
            0xFFFF: 'oxm_class_EXPERIMENTER'
        }

    return filter_oxm_class.table.get(int(x), 'oxm_class_INVALID')
############################


def eth_adr_to_int(x):
    if not hasattr(eth_adr_to_int, "table"):
        eth_adr_to_int.table = str.maketrans(dict.fromkeys(':.-'))  # it doesn't exist yet, so initialize it

    if x == "None":
        return 0x00
    else:
        return int(x.translate(eth_adr_to_int.table), 16)


def int_to_eth_adr(macint):
    if type(macint) != int:
        raise ValueError('invalid integer {}'.format(macint))
    return ':'.join(['{}{}'.format(a, b)
                     for a, b
                     in zip(*[iter('{:012x}'.format(macint))] * 2)])


def filter_eth_type(x):
    if x == "None":
        return 0x00
    else:
        return int(x, 16)


def filter_ipv4_adr(x):
    if x == "None":
        return 0x00
    else:
        ip = x.split('.')
        return int(''.join((hex(int(i))[2:] for i in ip)), 16)


def filter_hex(x):
    if x == "None":
        return 0x00
    else:
        return int(x, 16)


def _bytes_to_ofp_fields(data):

    if not hasattr(_bytes_to_ofp_fields, "fields"):
        _bytes_to_ofp_fields.fields = (
            ("of_version", "B"),
            ("of_type", "B"),
            ("length", "H"),
            ("xid", "I"),
            ("buffer_id", "I"),
            ("total_len", "H"),
            ("reason", "B"),
            ("table_id", "B"),
            ("cookie", "Q"),
            ("match_type", "H"),
            ("match_length", "H"),
            ("oxm_class", "H"),
            ("oxm_field", "B"),
            ("oxm_length", "B"),
            ("oxm_value", "I"),
            ("match_pad", "I"),
            ("pad", "H"),
            ("eth_dst", "6s"),
            ("eth_src", "6s"),
            ("ethertype", "H"),
            ("arp_htype", "H"),
            ("arp_ptype", "H"),
            ("arp_hlen", "B"),
            ("arp_plen", "B"),
            ("arp_oper", "H"),
            ("arp_sha", "6s"),
            ("arp_spa", "4s"),
            ("arp_tha", "6s"),
            ("arp_tpa", "4s"),
        )

    # Decode packet to a byte string
    packet_dict = None
    try:
        packet = base64.b64decode(data)
    except binascii.Error as e:
        print("Couldn't parse packet: {}\n{}".format(data, e))
        traceback.print_exc()
    else:
        # Unpack the byte string according to the fields
        unpack_string = "!"  # Network byte order
        for f in _bytes_to_ofp_fields.fields:
            unpack_string += f[1]
        ofp_packet = struct.unpack(unpack_string, packet[:struct.calcsize(unpack_string)])

        # Fill up the dict
        packet_dict = dict()
        for i in range(len(ofp_packet)):
            if _bytes_to_ofp_fields.fields[i][0] == "oxm_field":
                packet_dict["oxm_field"] = ofp_packet[i] >> 1
                packet_dict["oxm_has_mask"] = ofp_packet[i] & 0x01
            else:
                packet_dict[_bytes_to_ofp_fields.fields[i][0]] = ofp_packet[i]

    return pd.Series(packet_dict)


def decode_byte_data(data):
    return pd.Series(list(binascii.a2b_base64(data)))


def format_csv(csv_path, out_path=None, sep=','):
    """
    Format a dataset csv file.
    :param csv_path:
    :param sep:
    :param out_path:
    """
    # Load a dataset from the data folder or use the output of the previous pipeline
    raw_df = pd.read_csv(csv_path, sep=sep)

    # --------------------------------------------------------------------------
    # Make Field as features
    # --------------------------------------------------------------------------

    df = raw_df.copy(deep=True)

    # Interpret the field from the byte string
    field_features = df['data'].apply(_bytes_to_ofp_fields)
    df = pd.concat([df.iloc[:, :df.columns.get_loc("data")],  # Insert reasons before total_len
                    field_features,
                    df.iloc[:, df.columns.get_loc("data"):]], axis="columns")
    df.drop(['data'], axis='columns', inplace=True)

    # Format some columns
    df["eth_dst"] = df["eth_dst"].apply(lambda x: int.from_bytes(x, byteorder='big'))
    df["eth_src"] = df["eth_src"].apply(lambda x: int.from_bytes(x, byteorder='big'))
    df["arp_sha"] = df["arp_sha"].apply(lambda x: int.from_bytes(x, byteorder='big'))
    df["arp_spa"] = df["arp_spa"].apply(lambda x: int.from_bytes(x, byteorder='big'))
    df["arp_tha"] = df["arp_tha"].apply(lambda x: int.from_bytes(x, byteorder='big'))
    df["arp_tpa"] = df["arp_tpa"].apply(lambda x: int.from_bytes(x, byteorder='big'))
    df['error_type']    = df['error_type'].apply(lambda x: x if x == "parsing_error" else "non_parsing_error")

    # Drop error_trace column if it exists
    if 'error_trace' in df.columns:
        df.drop('error_trace', axis='columns')

    # --------------------------------------------------------------------------
    # Apply Domain Knowledge
    # --------------------------------------------------------------------------

    ## One hot encode the reason
    df['reason'] = df['reason'].apply(filter_reason)
    one_hot_reason = pd.get_dummies(df['reason']).astype(bool)
    ### Ensure that all the reason columns are generated
    reason_cols = ['reason_NoMatch', 'reason_Action', 'reason_InvalidTTL']
    for i in range(len(reason_cols)):
        if reason_cols[i] not in one_hot_reason:
            one_hot_reason.insert(min(i, len(reason_cols) - 1), reason_cols[i], False)
    ### Add the columns to the dataframe
    df = pd.concat([df.iloc[:, :df.columns.get_loc("reason")],  # Insert reasons before total_len
                    one_hot_reason,
                    df.iloc[:, df.columns.get_loc("reason"):]],
                   axis="columns")
    ### Drop the reason column
    df.drop(['reason'], axis='columns', inplace=True)

    ## Convert match type
    df['match_type'] = df['match_type'].apply(lambda x: True if x is not None and x == 0x01 else False)
    df.rename(columns={'match_type': 'match_type_is_valid'}, inplace=True)
    ## One hot encode the oxm class
    df['oxm_class'] = df['oxm_class'].apply(filter_oxm_class)
    one_hot_oxm_class = pd.get_dummies(df['oxm_class']).astype(bool)
    ### Ensure that all the oxm columns are generated
    oxm_cols = ['oxm_class_NXM_0', 'oxm_class_NXM_1',
                'oxm_class_OPENFLOW_BASIC', 'oxm_class_EXPERIMENTER']
    for i in range(len(oxm_cols)):
        if oxm_cols[i] not in one_hot_reason:
            one_hot_reason.insert(min(i, len(oxm_cols) - 1), oxm_cols[i], False)

    ### Add the columns to the dataframe
    df = pd.concat([df.iloc[:, :df.columns.get_loc("oxm_class")],
                    one_hot_oxm_class,
                    df.iloc[:, df.columns.get_loc("oxm_class"):]],
                   axis="columns")

    ### Drop the oxm_class column
    df.drop(['oxm_class'], axis='columns', inplace=True)

    ## Convert paddings
    df['match_pad'] = df['match_pad'].apply(lambda x: x != 0).astype(bool)
    df['pad']       = df['pad'].apply(lambda x: x != 0).astype(bool)
    df.rename(columns={'match_pad': 'match_pad_is_zero', 'pad': 'pad_is_zero'}, inplace=True)

    ## Calculate distance to intended ethernet addresses
    # df['eth_src'] = df['eth_src'].apply(lambda x: math.log(abs(x - eth_adr_to_int('10.0.0.1'))))
    # df['eth_dst'] = df['eth_dst'].apply(lambda x: math.log(abs(x - eth_adr_to_int('10.0.0.2'))))
    # df.rename(columns={'eth_src': 'eth_src_distance', 'eth_dst': 'eth_dst_distance'}, inplace=True)

    ## Convert oxm_has_mask to boolean
    df['oxm_has_mask'] = df['oxm_has_mask'].astype(bool)

    # Convert EtherType
    df['ethertype'] = df['ethertype'].apply(lambda x: True if x == 0x0806 else False)
    df.rename(columns={'ethertype': 'ethertype_is_arp'}, inplace=True)

    # Drop the unused columns
    df = df.drop([
        'cookie',       # cookie is a unique identifier for a fuzzed message. It is irrelevant to use it.
        'buffer_id',    #
        'table_id',     #
        'error_reason',
        'error_effect'
    ],
        axis='columns')

    # Drop error_trace column if it exists
    if 'error_trace' in df.columns:
        df.drop('error_trace', axis='columns')

    # Stores the data
    df.to_csv(out_path if out_path is not None else csv_path,
              sep=sep,
              index=False,
              encoding='utf-8-sig')
