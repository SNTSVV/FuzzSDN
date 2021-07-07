import math
import operator
import re


# ==== ( Lookup tables ) =======================================================

COND_TO_FUZZER_ACTION_DICT = {
    "of_version"    : {"loc": 0,  "size": 1},
    "of_type"       : {"loc": 1,  "size": 1},
    "length"        : {"loc": 2,  "size": 2},
    "xid"           : {"loc": 4,  "size": 4},
    "buffer_id"     : {"loc": 8,  "size": 4},
    "total_len"     : {"loc": 12, "size": 2},
    "reason"        : {"loc": 14, "size": 1},
    "table_id"      : {"loc": 15, "size": 1},
    "cookie"        : {"loc": 16, "size": 8},
    "match_type"    : {"loc": 24, "size": 2},
    "match_length"  : {"loc": 26, "size": 2},
    "match_pad"     : {"loc": 28, "size": 4},
    "oxm_class"     : {"loc": 32, "size": 2},
    "oxm_field"     : {"loc": 34, "size": 1},
    "oxm_length"    : {"loc": 35, "size": 1},
    "oxm_value"     : {"loc": 36, "size": 4},
    "pad"           : {"loc": 40, "size": 2},
    "eth_dst"       : {"loc": 42, "size": 6},
    "eth_src"       : {"loc": 48, "size": 6},
    "ethertype"     : {"loc": 54, "size": 2},
    "arp_htype"     : {"loc": 56, "size": 2},
    "arp_ptype"     : {"loc": 58, "size": 2},
    "arp_hlen"      : {"loc": 60, "size": 1},
    "arp_plen"      : {"loc": 61, "size": 1},
    "arp_oper"      : {"loc": 62, "size": 2},
    "arp_sha"       : {"loc": 64, "size": 6},
    "arp_spa"       : {"loc": 70, "size": 4},
    "arp_tha"       : {"loc": 74, "size": 6},
    "arp_tpa"       : {"loc": 80, "size": 4}
}

STR_TO_OP_DICT = {
    "=" : operator.eq,
    ">=": operator.ge,
    ">" : operator.gt,
    "<=": operator.le,
    "<" : operator.lt
}

OP_TO_STR_DICT = {
    operator.eq: "=",
    operator.ge: ">=",
    operator.gt: ">",
    operator.le: "<=",
    operator.lt: "<"
}

# ===== ( Class Object ) =======================================================


class Rule(object):
    """
    An object which role is to store a rule
    """

    # ===== ( Constructor ) ====================================================

    def __init__(self):
        self.__class = ""
        self.__conditions = list()
    # End def __init__

    def __repr__(self):
        repr_str = ""
        first = True
        for cond in self.__conditions:
            if not first:
                repr_str += " and "
            else:
                first = False

            repr_str += "({} {} {})".format(cond["field"],
                                            OP_TO_STR_DICT.get(cond["op"], "?"),
                                            cond["value"])

        repr_str += " => class={}".format(self.__class)
        return repr_str

    # ===== ( Getters ) ======================================================

    def get_class(self):
        return self.__class
    # End def set_class

    # ===== ( Setters ) ========================================================

    def add_condition(self, field, op, value):
        self.__conditions.append(
            {
                "field": field,
                "op": op,
                "value": value
            }
        )
    # End def add_condition

    def set_class(self, lb_cls):
        self.__class = lb_cls
    # End def set_class

    # ===== ( Methods ) ========================================================

    def to_fuzzer_actions(self):
        """
        """
        # TODO: handle custom made fields
        # TODO: handle poorly defined conditions, like "(field > value) and (field < value - 1)" (which is impossible)

        fuzz_action = list()
        for c in self.__conditions:

            # 1. get the dict for the action
            action_dict = COND_TO_FUZZER_ACTION_DICT[c["field"]]

            # 2 Find if there is already an action on the same field
            act_ind = next((i for i, item in enumerate(fuzz_action) if item["field"] == c["field"]), None)
            print(act_ind)
            # 3.1 If we already found an action we merge them if possible
            if act_ind is not None:
                # 3.1.1 If there is already a set action, we skip all futher steps
                if fuzz_action[act_ind]["type"] == "set":
                    continue

                # 3.1.2 If the new operator is "=", we remove the range and set
                # the new type as "set"
                if c["op"] == operator.eq:  # Operator is "="
                    fuzz_action[act_ind]["type"] = "set"
                    fuzz_action[act_ind]["value"] = c["value"]
                    if "range" in fuzz_action[act_ind]:
                        del fuzz_action[act_ind]["range"]  # We remove the range key
                # 3.1.3 Otherwise, we update the range
                else:
                    fuzz_action[act_ind]["type"] = "scramble_in_range"
                    # Create modify the range of act_range
                    if not c["op"](fuzz_action[act_ind]["range"][0], int(c["value"])):
                        fuzz_action[act_ind]["range"][0] = int(c["value"])
                    elif not c["op"](fuzz_action[act_ind]["range"][1], int(c["value"])):
                        fuzz_action[act_ind]["range"][1] = int(c["value"])

            # 3.2 Otherwise we create a new action
            else:
                action = {
                    "field": c['field'],
                    "action": "ByteFieldAction",  # Action is always a byte field action
                    "type": "unknown"
                }

                # 2.3.1 determine the type of operation:
                if c["op"] == operator.eq:  # Operator is "="
                    action["type"] = "set"
                    action["value"] = c["value"]

                else:  # Operator is ">", ">=", "<" or "<="
                    action["type"] = "scramble_in_range"
                    ul = int(math.pow(2, 8 * int(action_dict["size"])) - 1)  # Create the range depending on the size of the field
                    action["range"] = [0, ul]

                    # Update the range
                    if not c["op"](action["range"][0], int(c["value"])):
                        action["range"][0] = int(c["value"])
                    elif not c["op"](action["range"][1], int(c["value"])):
                        action["range"][1] = int(c["value"])

                # 3.2.2 We add the new action to the action list
                fuzz_action.append(action)
            print(fuzz_action)

        return fuzz_action
    # End def to_fuzzer_actions

# End class Rule


# ===== ( Methods ) ============================================================


def from_string(rule_str):
    """
    Create a Rule object from a rule string

    :param rule_str:
    :return:
    """

    # Create the new rule
    new_rule = Rule()

    # Define regex
    rgx = r"\(([^(/)]+)\)"

    # Find all criteria and store them in a list
    criteria_found = re.findall(rgx, rule_str)
    for criterion in criteria_found:
        params = criterion.split(" ")
        new_rule.add_condition(field=params[0],
                               op=STR_TO_OP_DICT.get(params[1], "="),
                               value=params[2])

        # find to which class the rules applies
        # result = re.findall(rgx, rule_str)[0]
    return new_rule
# End def from_string


def from_dict(rule_dict: dict):
    """
    Create a Rule object from a rule dict object

    :param rule_dict:
    :return:
    """

    new_rule = from_string(rule_dict["conditions"])
    new_rule.set_class(rule_dict["class"])

    return new_rule
# End def from_string
