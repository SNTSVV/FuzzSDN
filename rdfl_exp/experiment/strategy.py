# -*- coding: utf-8 -*-
import random

import common.openflow.v0x05.message.struct as ofp_0x05_msg_struct
from common.openflow.v0x05.common.message import ofp_type


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


# self testing

if __name__ == '__main__':
    import json

    print(json.dumps(beads_fuzzer_actions(), indent=4, sort_keys=False))