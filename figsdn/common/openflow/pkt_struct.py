# -*- coding: utf-8 -*-
"""Module that convert"""
from __future__ import annotations
from collections import OrderedDict
from math import ceil

from figsdn.common.openflow.types import ofp_type


class Field:
    """

    """

    def __init__(self, name: str, size: int, mask=None):
        self.name = name
        self.size = size
        self.mask = mask
    # End def __init__

    def __repr__(self):
        repr_str = "Field(name={}, size={}".format(self.name, self.size)
        if self.mask is not None:
            repr_str += ", mask={}".format(hex(self.mask))
        repr_str += ")"
        return repr_str

    @property
    def min(self):
        return 0

    @property
    def max(self):
        if self.mask is None:
            return pow(2, self.size * 8) - 1
        else:
            mask_copy = self.mask
            mtz = 0
            while (mask_copy & 1) == 0:
                mask_copy >>= 1
                mtz += 1
            return self.mask >> mtz  # remove the trailing zero of the mask
# End class Field


class PktStruct:
    """A Class representing the structure of a packet.

    The fields are ordered by they order of insertion.

    Args:
        fields (iterable)
    """

    def __init__(self, *fields):
        # Check that there are only fields passed as arguments
        if not all(isinstance(x, Field) for x in fields):
            raise AttributeError("PktStruct class accept only fields as parameters")
        self.fields = list()
        if len(fields) > 0:
            self.fields.extend(fields)
    # End def __init__

    # ===== ( properties ) ======

    @property
    def bit_size(self):
        """Return the total size in bits of the structure."""
        bits_len = 0

        for f in self.fields:
            if f.mask is None:
                bits_len += f.size * 8
            else:  # Count the number of bit assigned by the mask
                mask_copy = f.mask
                while mask_copy > 0:
                    bits_len += (mask_copy & 1)  # binary comparison
                    mask_copy = mask_copy >> 1  # binary shifting

        return bits_len
    # End def bit_size

    @property
    def byte_size(self):
        """Return the total size in bytes of the PktStruct."""
        return ceil(self.bit_size / 8.0)
    # End def byte_size

    # ==== (builtin overload) =====

    def __len__(self):
        return len(self.fields)

    def __iter__(self):
        yield from self.fields
    # End def __iter__

    def __getitem__(self, key):
        # Get the field by its position in the list
        if isinstance(key, int):
            return self.fields[key]

        elif isinstance(key, str):
            try:
                return next(f for f in self if f.name == key)
            except StopIteration:
                raise AttributeError("No field with name \"{}\" found in the PktStruct".format(key)) from None

        else:
            raise TypeError("__getitem__ key must be integer or str, not {}".format(type(key).__name__))
    # End def __getitem__

    # ===== ( methods ) ====

    def append(self, *fields: Field):
        """Appends one or several fields to the list of fields"""
        for f in fields:
            self.fields.append(f)
    # End def append

    def extend(self, other: PktStruct):
        self.fields.extend(other.fields)
    # End def extend

    def index(self, f_name: str):
        """Return the index of a field by its name."""
        try:
            return next(idx for idx, e in enumerate(self.fields) if e.name == f_name)
        except StopIteration:
            raise AttributeError("No field with name \"{}\" found in the PktStruct".format(f_name)) from None
    # End def index

    def offset(self, key, in_bits=False):
        """Return the offset of a field."""
        if isinstance(key, int):
            if key >= len(self):
                raise IndexError("field index out of range")
            idx = key
        elif isinstance(key, str):
            idx = self.index(key)
        else:
            raise AttributeError("attribute \"key\" must be integer or str, not {}".format(type(key).__name__))

        offset = 0
        if idx > 0:  # If the index is 0 then just return 0
            for i in range(1, idx + 1):
                # Add the length of the previous field, unless the previous field is masked and this one as well.
                if self[i].mask is None or self[i].mask is not None and self[i - 1].mask is None:
                    offset += self[i - 1].size

        return offset
    # End def offset

    def to_dict(self) -> OrderedDict:
        """Return an OrderedDict representation of the PktStruct."""
        out_dict = OrderedDict()

        for f in self.fields:
            out_dict[f.name] = {
                "offset" : self.offset(f.name),
                "size"   : f.size,
                "min"    : f.min,
                "max"    : f.max,
            }
            if f.mask is not None:
                out_dict[f.name]["mask"] = f.mask

        return out_dict
    # End def to_dict
# End class PktStruct


def of(type_: ofp_type, **kwargs) -> PktStruct:
    """Return a struct that characterize the format of a message.

    Accepted types are OFPT_HELLO, OFPT_ECHO_REQUEST and OFPT_ECHO_REPLY.
    Each type as a list of arguments that can be accepted

    Args:
        type_ (ofp_type) : The type of message to generate a struct for
        **kwargs: Options during to refine the packet structure
            - **hello_elements (int): if a OFPT_HELLO message is set, define the number of hello elements in it
            - **match (dict): used to add some match
                - **oxms (int) : number of oxms in the match
    Returns:
        A PktStruct of the message
    """

    pkt_struct = PktStruct()

    if type_ == ofp_type.OFPT_HELLO:
        # Add the header
        pkt_struct.append(
            Field(name="version", size=1),
            Field(name="type", size=1),
            Field(name="length", size=2),
            Field(name="xid", size=4))

        if "hello_elements" in kwargs:
            elements = kwargs.get("hello_elements")
            for i in range(len(elements)):
                pkt_struct.append(Field("hello_elem_{}_type".format(i), size=2))
                pkt_struct.append(Field("hello_elem_{}_len".format(i), size=2))

                if elements[i]["type"] == 1:
                    for j in range(elements[i]["bitmaps"]):
                        pkt_struct.append(Field("hello_elem_{}_bitmap_{}", size=4))

                i += 1

    # Echo messages
    elif type_ in (ofp_type.OFPT_ECHO_REQUEST, type_ == ofp_type.OFPT_ECHO_REPLY):
        # Add the header
        pkt_struct.append(
            Field(name="version", size=1),
            Field(name="type", size=1),
            Field(name="length", size=2),
            Field(name="xid", size=4))

        if "data" in kwargs:
            pkt_struct.append(Field(name="data", size=kwargs.get("data", 0)))

    elif type_ == ofp_type.OFPT_PACKET_IN:
        pkt_struct.append(
            Field(name="version", size=1),
            Field(name="type", size=1),
            Field(name="length", size=2),
            Field(name="xid", size=4),
            Field(name="buffer_id", size=4),
            Field(name="total_len", size=2),
            Field(name="reason", size=1),
            Field(name="table_id", size=1),
            Field(name="cookie", size=8),
        )

        # Build the match !
        if "match" in kwargs and isinstance(kwargs.get('match'), dict):

            pkt_struct.append(
                Field(name="match_type", size=2),
                Field(name="match_length", size=2),
                Field(name="match_pad", size=4)  # TODO: Dynamically calculate length of pad
            )

            match_dict = kwargs.get('match')

            if 'oxms' in match_dict:
                for i in range(int(match_dict['oxms'])):
                    pkt_struct.append(
                        Field(name="oxm_{}_class".format(i), size=2),
                        Field(name="oxm_{}_field".format(i), size=1, mask=0b11111110),
                        Field(name="oxm_{}_has_mask".format(i), size=1, mask=0b00000001),
                        Field(name="oxm_{}_length".format(i), size=1),
                        Field(name="oxm_{}_value".format(i), size=4)
                    )

        # Pad before data (16 bits)
        pkt_struct.append(Field(name="pad", size=2))

        if "data" in kwargs:
            data_dict = kwargs.get('data')
            if data_dict["type"] == 'ethernet':
                pkt_struct.append(
                    Field(name="eth_dst", size=6),
                    Field(name="eth_src", size=6),
                    Field(name="ethertype", size=2)
                )

                if data_dict.get("ethertype", None) == "arp":
                    pkt_struct.append(
                        Field(name="arp_htype", size=2),
                        Field(name="arp_ptype", size=2),
                        Field(name="arp_hlen", size=1),
                        Field(name="arp_plen", size=1),
                        Field(name="arp_oper", size=2),
                        Field(name="arp_sha", size=6),
                        Field(name="arp_spa", size=4),
                        Field(name="arp_tha", size=6),
                        Field(name="arp_tpa", size=4)
                    )

        elif "data_length" in kwargs:
            data_length = int(kwargs.get("data_length"))
            pkt_struct.append(Field(name="data", size=8 * data_length))

        else:
            pass

    # Barrier messages.
    elif type_ in (ofp_type.OFPT_BARRIER_REQUEST, ofp_type.OFPT_BARRIER_REPLY):
        pkt_struct.append(
            Field(name="version", size=1),
            Field(name="type", size=1),
            Field(name="length", size=2),
            Field(name="xid", size=4))

    elif type_ == ofp_type.OFPT_FLOW_REMOVED:
        pkt_struct.append(
            Field(name="version", size=1),
            Field(name="type", size=1),
            Field(name="length", size=2),
            Field(name="xid", size=4),
            Field(name="cookie", size=8),
            Field(name="priority", size=2),
            Field(name="reason", size=1),
            Field(name="table_id", size=1),
            Field(name="duration_sec", size=4),
            Field(name="duration_nsec", size=4),
            Field(name="idle_timeout", size=2),
            Field(name="hard_timeout", size=2),
            Field(name="packet_count", size=8),
            Field(name="byte_count", size=8),
            Field(name="match_type", size=2),
            Field(name="match_length", size=2),
            Field(name="oxm_0_class", size=2),
            Field(name="oxm_0_field", size=1, mask=254),
            Field(name="oxm_0_has_mask", size=1, mask=1),
            Field(name="oxm_0_length", size=1),
            Field(name="oxm_0_value", size=2),
            Field(name="match_pad", size=6)
        )

    else:
        raise AttributeError("Unknown Openflow message \"{}\"".format(type_))

    return pkt_struct
# End def get_msg_struct
