# -.- coding utf-8 -.-
"""Match structure and related enums.
An OpenFlow match is composed of a flow match header and a sequence of zero or
more flow match fields.
"""
from enum import Enum, IntEnum


class Ipv6ExtHdrFlags(Enum):
    """Bit definitions for IPv6 Extension Header pseudo-field."""
    OFPIEH_NONEXT   = 1 << 0    # "No next header" encountered.
    OFPIEH_ESP      = 1 << 1    # Encrypted Sec Payload header present.
    OFPIEH_AUTH     = 1 << 2    # Authentication header present.
    OFPIEH_DEST     = 1 << 3    # 1 or 2 dest headers present.
    OFPIEH_FRAG     = 1 << 4    # Fragment header present.
    OFPIEH_ROUTER   = 1 << 5    # Router header present.
    OFPIEH_HOP      = 1 << 6    # Hop-by-hop header present.
    OFPIEH_UNREP    = 1 << 7    # Unexpected repeats encountered.
    OFPIEH_UNSEQ    = 1 << 8    # Unexpected sequencing encountered.
# End def Ipv6ExtHdrFlags


class OxmOfbMatchField(IntEnum):
    """
    OXM Flow match field types for OpenFlow basic class.
    A switch is not required to support all match field types, just those
    listed in the Table 10. Those required match fields don’t need to be
    implemented in the same table lookup. The controller can query the switch
    about which other fields it supports.
    """
    OFPXMT_OFB_IN_PORT          = 0     # Switch input port.
    OFPXMT_OFB_IN_PHY_PORT      = 1     # Switch physical input port.
    OFPXMT_OFB_METADATA         = 2     # Metadata passed between tables.
    OFPXMT_OFB_ETH_DST          = 3     # Ethernet destination address.
    OFPXMT_OFB_ETH_SRC          = 4     # Ethernet source address.
    OFPXMT_OFB_ETH_TYPE         = 5     # Ethernet frame type.
    OFPXMT_OFB_VLAN_VID         = 6     # VLAN id.
    OFPXMT_OFB_VLAN_PCP         = 7     # VLAN priority.
    OFPXMT_OFB_IP_DSCP          = 8     # IP DSCP (6 bits in ToS field).
    OFPXMT_OFB_IP_ECN           = 9     # IP ECN (2 bits in ToS field).
    OFPXMT_OFB_IP_PROTO         = 10    # IP protocol.
    OFPXMT_OFB_IPV4_SRC         = 11    # IPv4 source address.
    OFPXMT_OFB_IPV4_DST         = 12    # IPv4 destination address.
    OFPXMT_OFB_TCP_SRC          = 13    # TCP source port.
    OFPXMT_OFB_TCP_DST          = 14    # TCP destination port.
    OFPXMT_OFB_UDP_SRC          = 15    # UDP source port.
    OFPXMT_OFB_UDP_DST          = 16    # UDP destination port.
    OFPXMT_OFB_SCTP_SRC         = 17    # SCTP source port.
    OFPXMT_OFB_SCTP_DST         = 18    # SCTP destination port.
    OFPXMT_OFB_ICMPV4_TYPE      = 19    # ICMP type.
    OFPXMT_OFB_ICMPV4_CODE      = 20    # ICMP code.
    OFPXMT_OFB_ARP_OP           = 21    # ARP opcode.
    OFPXMT_OFB_ARP_SPA          = 22    # ARP source IPv4 address.
    OFPXMT_OFB_ARP_TPA          = 23    # ARP target IPv4 address.
    OFPXMT_OFB_ARP_SHA          = 24    # ARP source hardware address.
    OFPXMT_OFB_ARP_THA          = 25    # ARP target hardware address.
    OFPXMT_OFB_IPV6_SRC         = 26    # IPv6 source address.
    OFPXMT_OFB_IPV6_DST         = 27    # IPv6 destination address.
    OFPXMT_OFB_IPV6_FLABEL      = 28    # IPv6 Flow Label
    OFPXMT_OFB_ICMPV6_TYPE      = 29    # ICMPv6 type.
    OFPXMT_OFB_ICMPV6_CODE      = 30    # ICMPv6 code.
    OFPXMT_OFB_IPV6_ND_TARGET   = 31    # Target address for ND.
    OFPXMT_OFB_IPV6_ND_SLL      = 32    # Source link-layer for ND.
    OFPXMT_OFB_IPV6_ND_TLL      = 33    # Target link-layer for ND.
    OFPXMT_OFB_MPLS_LABEL       = 34    # MPLS label.
    OFPXMT_OFB_MPLS_TC          = 35    # MPLS TC.
    OFPXMT_OFP_MPLS_BOS         = 36    # MPLS BoS bit.
    OFPXMT_OFB_PBB_ISID         = 37    # PBB I-SID.
    OFPXMT_OFB_TUNNEL_ID        = 38    # Logical Port Metadata.
    OFPXMT_OFB_IPV6_EXTHDR      = 39    # IPv6 Extension Header pseudo-field
# End def OxmOfbMatchField


class MatchType(IntEnum):
    """
    Indicates the match structure in use.

    The match type is placed in the type field at the beginning of all match
    structures. The "OpenFlow Extensible Match" type corresponds to OXM TLV
    format described below and must be supported by all OpenFlow switches.
    Extensions that define other match types may be published on the ONF wiki.
    Support for extensions is optional
    """
    OFPMT_STANDARD  = 0  # Deprecated
    OFPMT_OXM       = 1  # OpenFlow Extensible Match
# End def MatchType


class OxmClass(IntEnum):
    """
    OpenFlow Extensible Match (OXM) Class IDs.

    The high order bit differentiate reserved classes from member classes.
    Classes 0x0000 to 0x7FFF are member classes, allocated by ONF.
    Classes 0x8000 to 0xFFFE are reserved classes, reserved for
    standardisation.
    """
    OFPXMC_NXM_0            = 0x0000  # Backward compatibility with NXM
    OFPXMC_NXM_1            = 0x0001  # Backward compatibility with NXM
    OFPXMC_OPENFLOW_BASIC   = 0x8000  # Basic class for OpenFlow
    OFPXMC_EXPERIMENTER     = 0xFFFF  # Experimenter class
# End def OxmClass