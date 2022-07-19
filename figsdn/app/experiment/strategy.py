# -*- coding: utf-8 -*-
import random

import figsdn.common.openflow.message.struct as ofp_0x05_msg_struct
from figsdn.common.openflow.types import ofp_type
from figsdn.app.experiment import Rule, RuleSet
from figsdn.common.openflow import pkt_struct

CRITERION_CTX_OPTIONS = {

    "first_arp_message" : pkt_struct.of(
            type_=ofp_type.OFPT_PACKET_IN,
            match={"oxms": 1},
            data={
                "type": "ethernet",
                "ethertype": "arp"
            }),

    "first_hello_message" : pkt_struct.of(
            type_=ofp_type.OFPT_HELLO,
            hello_elements=[
                {"type" : 1, "bitmaps" : 2},
                {"type" : 1, "bitmaps" : 1}
            ]),
}

# NB: Simple implementation for now
def beads_fuzzer_actions():
    actions = list()

    field = random.choice(CRITERION_CTX_OPTIONS['first_arp_message'].to_dict())

    action = {
        "intent"    : "mutate_field",
        "fieldName" : field["name"],
        "range"     : [field["min"], field["max"]]
    }
    actions.append(action)

    return actions
# End def beads_fuzzer_actions()

def figsdn_action_mutate_rule(rule : Rule, amount, scenario, criterion, mutation_rate):

    ctx = None
    include_header = True if criterion == "first_hello_message" else False
    ctx = CRITERION_CTX_OPTIONS.get(criterion, None)

    return rule.convert_to_fuzzer_actions(
        n=amount,
        include_header=include_header,
        mutation_rate=mutation_rate,
        ctx=ctx.to_dict() if ctx is not None else None
    )
# End def figsdn_action_mutate_rule
