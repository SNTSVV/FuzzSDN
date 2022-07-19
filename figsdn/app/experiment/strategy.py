# -*- coding: utf-8 -*-
import random

import figsdn.common.openflow.message.struct as ofp_0x05_msg_struct
from figsdn.common.openflow.types import ofp_type


# NB: Simple implementation for now
def beads_fuzzer_actions():
    actions = list()
    msg_struct = ofp_0x05_msg_struct.get_msg_struct(ofp_type.OFPT_PACKET_IN)

    field = random.choice(msg_struct)

    action = {
        "intent"    : "mutate_field",
        "fieldName" : field["name"],
        "range"     : [field["min"], field["max"]]
    }
    actions.append(action)

    return actions


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
