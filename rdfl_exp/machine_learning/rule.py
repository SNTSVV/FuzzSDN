#!/usr/bin/env python3
# coding: utf-8
import math
import operator
import re
from copy import deepcopy

# ==== ( Lookup tables ) =======================================================
from rdfl_exp.utils.interval import Interval, Union

COND_TO_FUZZER_ACTION_DICT = {
    # Regular fields
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
    "arp_tpa"       : {"loc": 80, "size": 4},
}

CUSTOM_FIELDS_TO_CDT = {
    "match_type_is_valid": {
        "True"  : {"field": "match_type", "op": operator.eq, "value": 1},
        "False" : {"field": "match_type", "op": operator.ne, "value": 1},
    },
    "reason_NoMatch": {
        "True"  : {"field": "reason", "op": operator.eq, "value": 0},
        "False" : {"field": "reason", "op": operator.ne, "value": 0},
    },
    "reason_Action": {
        "True"  : {"field": "reason", "op": operator.eq, "value": 1},
        "False" : {"field": "reason", "op": operator.ne, "value": 1},
    },
    "reason_InvalidTTL": {
        "True"  : {"field": "reason", "op": operator.eq, "value": 2},
        "False" : {"field": "reason", "op": operator.ne, "value": 2},
    },
    "reason_Illegal": {
        "True"  : {"field": "reason", "op": operator.gt, "value": 2},
        "False" : {"field": "reason", "op": operator.le, "value": 2},
    },
    "oxm_class_NXM_0": {
        "True": {"field": "oxm_class", "op": operator.eq, "value": 0x0000},
        "False": {"field": "oxm_class", "op": operator.ne, "value": 0x0000},
    },
    "oxm_class_NXM_1": {
        "True": {"field": "oxm_class", "op": operator.eq, "value": 0x0001},
        "False": {"field": "oxm_class", "op": operator.ne, "value": 0x0001},
    },
    "oxm_class_OPENFLOW_BASIC": {
        "True": {"field": "oxm_class", "op": operator.eq, "value": 0x8000},
        "False": {"field": "oxm_class", "op": operator.ne, "value": 0x8000},
    },
    "oxm_class_EXPERIMENTER": {
        "True": {"field": "oxm_class", "op": operator.eq, "value": 0xFFFF},
        "False": {"field": "oxm_class", "op": operator.ne, "value": 0xFFFF},
    },
    "oxm_class_INVALID": {
        "True":  [
            {"field": "oxm_class", "op": operator.ne, "value": 0x0000},
            {"field": "oxm_class", "op": operator.ne, "value": 0x0001},
            {"field": "oxm_class", "op": operator.ne, "value": 0x8000},
            {"field": "oxm_class", "op": operator.ne, "value": 0xFFFF}
        ],
        "False": {"field": "oxm_class", "op": operator.eq, "value": 0x0000},
    },
    "match_pad_is_zero": {
        "True":  {"field": "match_pad", "op": operator.eq,  "value": 0},
        "False": {"field": "match_pad", "op": operator.ne, "value": 0}
    },
    "pad_is_zero": {
        "True":  {"field": "pad", "op": operator.eq, "value": 0},
        "False": {"field": "pad", "op": operator.ne, "value": 0}
    },
    "ethertype_is_arp": {
        "True":   {"field": "ethertype", "op": operator.eq, "value": 0x0806},
        "False":  {"field": "ethertype", "op": operator.ne, "value": 0x0806},
    },

    # TODO: Add fields for the pads
}

STR_TO_OP_DICT = {
    "=" : operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">" : operator.gt,
    "<=": operator.le,
    "<" : operator.lt
}

OP_TO_STR_DICT = {
    operator.eq: "=",
    operator.ne: "!=",
    operator.ge: ">=",
    operator.gt: ">",
    operator.le: "<=",
    operator.lt: "<"
}

# ===== ( Rule class ) =========================================================


class Rule(object):
    """
    An object which role is to store a rule
    """

    # ===== ( Constructor ) ====================================================

    def __init__(self):
        self.__class = ""
        self.__conditions = list()
    # End def __init__

    @classmethod
    def from_string(cls, rule_str: str):
        """
        Create a Rule object from a rule string
        :param rule_str:
        :return:
        """

        # Create the new rule
        new_rule = Rule()

        # Define regex
        rgx_cdt = r"\(([^(/)]+)\)"
        rgx_cls_1 = r"(?<==>).*=.*(?=\()"
        rgx_cls_2 = r"(?<==>).*=.*"

        # Find all criteria and store them in a list
        criteria_found = re.findall(rgx_cdt, rule_str)
        for criterion in criteria_found:
            params = criterion.split(" ")
            new_rule.add_condition(field=params[0],
                                   op=STR_TO_OP_DICT.get(params[1], "="),
                                   value=params[2])

        # Find to which class the rules applies
        class_match = re.search(rgx_cls_1, rule_str)
        if class_match:
            new_rule.set_class(class_match.group(0).split("=")[1].strip())
        else:
            class_match = re.search(rgx_cls_2, rule_str)
            if class_match:
                new_rule.set_class(class_match.group(0).split("=")[1].strip())

        return new_rule
    # End def from_string

    @classmethod
    def from_dict(cls, rule_dict: dict):
        """
        Create a Rule object from a rule dict object

        :param rule_dict:
        :return:
        """

        new_rule = cls.from_string(rule_dict["conditions"])
        new_rule.set_class(rule_dict["class"])

        return new_rule
    # End def from_dict

    # ===== ( Overload ) =======================================================

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
    # End __repr__

    # ===== ( Getters ) ======================================================

    def get_class(self):
        return self.__class
    # End def get_class

    def get_conditions(self):
        return self.__conditions
    # End def get_conditions

    # ===== ( Setters ) ========================================================

    def add_condition(self, field, op, value) -> None:
        # Check if it is a custom field
        if field in CUSTOM_FIELDS_TO_CDT:
            field_dict = deepcopy(CUSTOM_FIELDS_TO_CDT[field][value])
            if isinstance(field_dict, list):
                for field in field_dict:
                    self.__conditions.append(field)
            else:
                self.__conditions.append(field_dict)

        # Check if the field is known
        elif field in COND_TO_FUZZER_ACTION_DICT:
            self.__conditions.append(
                {
                    "field": field,
                    "op": op,
                    "value": value
                }
            )

        # Else raise an error
        else:
            pass  # TODO: Raise an error
    # End def add_condition

    def set_class(self, lb_cls):
        self.__class = lb_cls
    # End def set_class

    # ===== ( Methods ) ========================================================

    def to_dict(self):
        """
        Convert the rule to a dictionary
        :return: A dictionary representing the rule
        """
        out_dict = dict()
        cond_str = ""
        first = True

        for cond in self.__conditions:
            if not first:
                cond_str += " and "
            else:
                first = False
            cond_str += "({} {} {})".format(cond["field"],
                                            OP_TO_STR_DICT.get(cond["op"], "?"),
                                            cond["value"])

        out_dict["conditions"] = cond_str
        out_dict["class"] = self.get_class()

        return out_dict
    # End def to_dict

    def to_fuzzer_actions(self):
        """
        """
        # TODO: handle poorly defined conditions, like "(field > value) and (field < value - 1)" (which is impossible)

        fuzz_action = list()
        for c in self.__conditions:
            # 1. get the dict for the action
            action_dict = deepcopy(COND_TO_FUZZER_ACTION_DICT[c["field"]])

            # 2 Find if there is already an action on the same field
            act_ind = next((i for i, item in enumerate(fuzz_action) if item["field"] == c["field"]), None)
            # 3.1 If we already found an action we merge them if possible
            if act_ind is not None:
                # 3.1.1 If there is already a set action, we skip all futher steps
                if fuzz_action[act_ind]["type"] == "set":
                    continue

                # 3.1.2 If the new operator is "=", we remove the range and set
                # the new type as "set"
                if c["op"] == operator.eq:  # Operator is "="
                    fuzz_action[act_ind]["type"] = "set"
                    fuzz_action[act_ind]["value"] = int(c["value"])
                    if "range" in fuzz_action[act_ind]:
                        del fuzz_action[act_ind]["range"]  # We remove the range key
                # 3.1.3 Otherwise, we update the range
                else:
                    fuzz_action[act_ind]["type"] = "scramble_in_range"

                    # Update the range
                    op_range = None
                    if c["op"] == operator.ne:
                        op_range = Union(Interval((-math.inf, int(c["value"])-1)),
                                         Interval((int(c["value"])+1, math.inf)))

                    elif c["op"] == operator.ge:
                        op_range = Union(Interval((int(c["value"]), math.inf)))

                    elif c["op"] == operator.gt:
                        op_range = Union(Interval((int(c["value"])+1, math.inf)))

                    elif c["op"] == operator.le:
                        op_range = Union(Interval((-math.inf, int(c["value"]))))

                    elif c["op"] == operator.lt:
                        op_range = Union(Interval((-math.inf, int(c["value"])-1)))

                    fuzz_action[act_ind]["range"].inter(op_range, inplace=True)

            # 3.2 Otherwise we create a new action
            else:
                action = {
                    "field"     : c['field'],
                    "firstByte" : action_dict["loc"],
                    "size"      : action_dict["size"],
                    "action"    : "ByteFieldAction",  # Action is always a byte field action
                    "type"      : "unknown"
                }

                # 2.3.1 determine the type of operation:
                if c["op"] == operator.eq:  # Operator is "="
                    action["type"] = "set"
                    action["value"] = int(c["value"])

                else:  # Operator is ">", ">=", "<" or "<="
                    action["type"] = "scramble_in_range"
                    ul = int(math.pow(2, 8 * int(action_dict["size"])) - 1)  # Create the range depending on the size of the field
                    action["range"] = Union(Interval((0, ul)))

                    # Update the range
                    op_range = None
                    if c["op"] == operator.ne:
                        op_range = Union(Interval((-math.inf, int(c["value"])-1)),
                                         Interval((int(c["value"])+1, math.inf)))

                    elif c["op"] == operator.ge:
                        op_range = Union(Interval((int(c["value"]), math.inf)))

                    elif c["op"] == operator.gt:
                        op_range = Union(Interval((int(c["value"])+1, math.inf)))

                    elif c["op"] == operator.le:
                        op_range = Union(Interval((-math.inf, int(c["value"]))))

                    elif c["op"] == operator.lt:
                        op_range = Union(Interval((-math.inf, int(c["value"])-1)))

                    action["range"].inter(op_range, inplace=True)

                # 3.2.2 We add the new action to the action list
                fuzz_action.append(action)

        # Convert all the unions ranges to a list of ranges
        for act in fuzz_action:
            if "range" in act:
                if isinstance(act["range"], Union):
                    act["range"] = [[x.inf, x.sup] for x in list(act["range"])]
        return fuzz_action
    # End def to_fuzzer_actions

# End class Rule
