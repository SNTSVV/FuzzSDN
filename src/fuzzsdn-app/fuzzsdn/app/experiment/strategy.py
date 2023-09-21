# -*- coding: utf-8 -*-
import logging
import random
from typing import Optional

from fuzzsdn.common.openflow.pkt_struct import Field, PktStruct
from fuzzsdn.common.openflow.types import ofp_type
from fuzzsdn.app.experiment import Analyzer, Rule
from fuzzsdn.common.openflow import pkt_struct

_log = logging.getLogger(__name__)


def beads_fuzzer_actions():
    actions = list()

    pkt_dict = pkt_struct.of(
        ofp_type.OFPT_PACKET_IN,
        match={"oxms": 1},
        data={
            "type": "ethernet",
            "ethertype": "arp"
        }
    ).to_dict()

    field = random.choice(list(pkt_dict.keys()))

    action = {
        "intent"    : "mutate_field",
        "fieldName" : field,
        "range"     : [[pkt_dict[field]["min"], pkt_dict[field]["max"]]]
    }
    actions.append(action)

    return actions
# End def beads_fuzzer_actions()


def fuzzsdn_action_mutate_rule(rule : Rule, amount, scenario, criterion, mutation_rate, analyzer: Optional[Analyzer] = None):

    packet_structure = None
    include_header = True if criterion == "first_hello_message" else False

    _log.debug("Creating strategy for \"{}\" with criterion \"{}\"".format(scenario, criterion))

    # Any scenario
    if criterion == "first_hello_message":
        include_header = True
        packet_structure = pkt_struct.of(type_=ofp_type.OFPT_HELLO)

    elif criterion == "first_arp_message":
        include_header = False
        packet_structure = pkt_struct.of(type_=ofp_type.OFPT_PACKET_IN,
                                         match={"oxms": 1},
                                         data={
                                             "type": "ethernet",
                                             "ethertype": "arp"
                                         })

    elif criterion in "first_echo_reply":
        include_header = True
        if analyzer:
            packet_structure = from_fuzzer_list_of_fields(analyzer.last_list_of_fields)
        else:
            packet_structure = pkt_struct.of(ofp_type.OFPT_ECHO_REPLY)

    elif criterion == "first_echo_request":
        include_header = True
        if analyzer:
            packet_structure = from_fuzzer_list_of_fields(analyzer.last_list_of_fields)
        else:
            packet_structure = pkt_struct.of(ofp_type.OFPT_ECHO_REQUEST)

    elif criterion == "first_barrier_request":
        include_header = True
        if analyzer:
            packet_structure = from_fuzzer_list_of_fields(analyzer.last_list_of_fields)
        else:
            packet_structure = pkt_struct.of(ofp_type.OFPT_BARRIER_REQUEST)

    elif criterion == "first_barrier_reply":
        include_header = True
        if analyzer:
            packet_structure = from_fuzzer_list_of_fields(analyzer.last_list_of_fields)
        else:
            packet_structure = pkt_struct.of(ofp_type.OFPT_BARRIER_REPLY)

    elif criterion == "first_flow_mod":
        include_header = True
        if analyzer:
            packet_structure = from_fuzzer_list_of_fields(analyzer.last_list_of_fields)
        else:
            packet_structure = pkt_struct.of(ofp_type.OFPT_FLOW_MOD)

    elif criterion == "first_flow_removed":
        include_header = True
        if analyzer:
            packet_structure = from_fuzzer_list_of_fields(analyzer.last_list_of_fields)
        else:
            packet_structure = pkt_struct.of(ofp_type.OFPT_FLOW_REMOVED)

    # Finally, return the converted actions
    return rule.convert_to_fuzzer_actions(
        n=amount,
        include_header=include_header,
        mutation_rate=mutation_rate,
        ctx=packet_structure.to_dict() if packet_structure is not None else None
    )
# End def fuzzsdn_action_mutate_rule


def from_fuzzer_list_of_fields(fields: list) -> PktStruct:
    out = PktStruct()
    for f in fields:
        out.append(Field(f['name'], f['length'], mask=f['mask'] if 'mask' in f else None))
    return out
# End def from_fuzzer_struct
