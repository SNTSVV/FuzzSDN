#!/usr/bin/env python3
# coding: utf-8
import math
import operator
import random
from copy import deepcopy
from re import search
from re import search

from sympy import *

from rdfl_exp.utils.interval import IntervalSet

# ==== ( Lookup tables ) =======================================================


COND_TO_FUZZER_ACTION_LUT = {
    # Regular fields
    "of_version"    : {"loc": 0, "size": 1},
    "of_type"       : {"loc": 1, "size": 1},
    "length"        : {"loc": 2, "size": 2},
    "xid"           : {"loc": 4, "size": 4},
    "buffer_id"     : {"loc": 8, "size": 4},
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

CDT_REPLACEMENT_LUT = {
    "(match_type_is_valid = True)":         "(match_type = 1)",
    "(match_type_is_valid = False)":        "(match_type != 1)",

    "(reason_NoMatch = True)":              "(reason = 0)",
    "(reason_NoMatch = False)":             "(reason != 0)",
    "(reason_Action = True)":               "(reason = 1)",
    "(reason_Action = False)":              "(reason != 1)",
    "(reason_InvalidTTL = True)":           "(reason = 2)",
    "(reason_InvalidTTL = False)":          "(reason != 2)",
    "(reason_Illegal = True)":              "(reason > 2)",
    "(reason_Illegal = False)":             "(reason <= 2)",

    "(oxm_class_NXM_0 = True)":             "(oxm_class = 0)",
    "(oxm_class_NXM_0 = False)":            "(oxm_class != 0)",
    "(oxm_class_NXM_1 = True)":             "(oxm_class = 1)",
    "(oxm_class_NXM_1 = False)":            "(oxm_class != 1)",
    "(oxm_class_OPENFLOW_BASIC = True)":    "(oxm_class = 32768)",
    "(oxm_class_OPENFLOW_BASIC = False)":   "(oxm_class != 32768)",
    "(oxm_class_EXPERIMENTER = True)":      "(oxm_class = 65535)",
    "(oxm_class_EXPERIMENTER = False)":     "(oxm_class != 65535)",

    "(oxm_class_INVALID = True)":           "(oxm_class != 0) and (oxm_class != 1) and (oxm_class != 32768) and (oxm_class != 65535)",
    "(oxm_class_INVALID = False)":          "((oxm_class = 0) or (oxm_class = 1) or (oxm_class = 32768) or (oxm_class = 65535))",

    "(match_pad_is_zero = True)":           "(match_pad = 0)",
    "(match_pad_is_zero = False)":          "(match_pad != 0)",

    "(pad_is_zero = True)":                 "(pad = 0)",
    "(pad_is_zero = False)":                "(pad != 0)",

    "(ethertype_is_arp = True)":            "(pad = 2054)",
    "(ethertype_is_arp = False)":           "(pad != 2054)"
}

STR_TO_OP_DICT = {
    "=": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
    "<=": operator.le,
    "<": operator.lt
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

    # ===== ( Constructor ) ====================================================

    def __init__(self, expr, class_=None):
        self.expr = expr
        self.class_ = class_
    # End def __init__

    @classmethod
    def from_string(cls, rule_str: str):

        rule_class = None

        # Copy the rule string
        tmp_rule = deepcopy(rule_str)

        # Replace all the elements according to the LUT
        for elem in CDT_REPLACEMENT_LUT:
            if elem in tmp_rule:
                tmp_rule = tmp_rule.replace(elem, CDT_REPLACEMENT_LUT[elem])

        # Get the class of the rule
        # Regex used to get the rule
        rgx_cls_1 = r"(?<==>).*=.*(?=\()"
        rgx_cls_2 = r"(?<==>).*=.*"
        class_match = search(rgx_cls_1, rule_str)
        if class_match:
            rule_class = class_match.group(0).split("=")[1].strip()
        else:
            class_match = search(rgx_cls_2, rule_str)
            if class_match:
                rule_class = class_match.group(0).split("=")[1].strip()

        # Infer the expression from the rule.

        tmp_rule = tmp_rule.replace(' ', '')  # Remove all spaces

        # Replace the ands and ors by their symbols
        tmp_rule = tmp_rule.replace("and", "&")
        tmp_rule = tmp_rule.replace("or", "|")

        # First replace the parenthesis by brackets and then transform them back
        # to parenthesis. This avoid a parenthesis being handled severa times
        tmp_rule = tmp_rule.replace("((", "[symbols['")
        tmp_rule = tmp_rule.replace("))", "']]")
        tmp_rule = tmp_rule.replace("(", "symbols['")
        tmp_rule = tmp_rule.replace(")", "']")

        tmp_rule = tmp_rule.replace("[", "(")
        tmp_rule = tmp_rule.replace("]", ")")
        # Remove the rule part
        tmp_rule = tmp_rule.split('=>')[0]

        # evaluate the expression
        if tmp_rule is None or tmp_rule == '':
            return None
        else:
            return Rule(eval(tmp_rule), rule_class)
    # End def from_string

    # ===== ( Operator overriding ) ====================================================================================

    def __and__(self, other):
        return Rule(simplify(self.expr & other.expr))

    def __or__(self, other):
        return Rule(simplify(self.expr | other.expr))

    def __invert__(self):
        return Rule(simplify(~self.expr))

    # ====== ( Overloading ) ===========================================================================================

    def __repr__(self):
        r_str = str(self.expr)
        if self.class_ is not None:
            r_str += " => class={}".format(self.class_)
        return r_str

    # ====== ( Getters ) ===============================================================================================

    def get_class(self):
        return self.class_

    def apply(self):
        models = list(m for m in satisfiable(self.expr, all_models=True))
        for m in models:
            print(m)

        # Return a sample of the rule
        return random.sample(models, 1)[0]


# End def rule


def convert_to_fuzzer_actions(rule: Rule):
    """ Transform the rules into a set of fuzzer interpretable actions """

    # TODO: handle poorly defined conditions, like "(field > value) and (field < value - 1)" (which is impossible)

    # sub functions
    def get_range_op_val(op, value):
        """ Define a range from the operator and the value"""
        _range = None

        if op == operator.ne:
            _range = IntervalSet((-math.inf, value - 1),
                                 (value + 1, math.inf))
        elif op == operator.ge:
            _range = IntervalSet((value, math.inf))
        elif op == operator.gt:
            _range = IntervalSet((value + 1, math.inf))
        elif op == operator.le:
            _range = IntervalSet((-math.inf, value))
        elif op == operator.lt:
            _range = IntervalSet((-math.inf, value - 1))

        return _range
    # End def get_range_cdt

    def get_new_action(field, loc, size, op, value):
        new_act = {
            "field": field,
            "firstByte": loc,
            "size": size,
            "action": "ByteFieldAction",
            # Action is always a byte field action
            "type": "unknown"
        }

        # 2.3.1 determine the type of operation:
        if op == operator.eq:  # Operator is "="
            new_act["type"] = "set"
            new_act["value"] = value

        else:  # Operator is ">", ">=", "<" or "<="
            new_act["type"] = "scramble_in_range"
            # Create the range depending on the size of the field
            bounds = IntervalSet((0, int(math.pow(2, 8 * size - 1))))
            # Get the absolute range from the operator and the value
            _range = get_range_op_val(op, value)
            # Intersect the action's range with the range of the new condition
            new_act["range"] = bounds & _range

        return new_act
    # End def get_new_action

    # 1. Get an application of the rule
    app_dict = rule.apply()

    # 2. Create a condition table
    conditions = []
    for key in app_dict:
        negate = False if app_dict[key] is True else True
        cdt_str = str(key)
        cdt = dict()

        if '>' in cdt_str and ">=" not in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('>')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = operator.gt if not negate else operator.le

        elif '>=' in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('>=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = operator.ge if not negate else operator.lt

        elif '<' in cdt_str and "<=" not in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('<')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = operator.lt if not negate else operator.ge

        elif '<=' in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('<=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = operator.le if not negate else operator.gt

        elif '=' in cdt_str and '!=' not in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = operator.eq if not negate else operator.ne

        elif '!=' in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('!=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = operator.ne if not negate else operator.eq

        conditions.append(cdt)

    fuzz_action = []
    for c in conditions:

        # 1. get the dict for the action
        action_dict = COND_TO_FUZZER_ACTION_LUT[c["field"]]

        # 2 Find if there is already an action on the same field
        act_ind = next((i for i, item in enumerate(fuzz_action) if
                        item["field"] == c["field"]), None)
        # 3.1 If we already found an action we merge them if possible
        if act_ind is not None:
            # 3.1.1 If there is already a set action, we skip all further steps
            if fuzz_action[act_ind]["type"] == "set":
                continue

            # 3.1.2 If the new operator is "=", we remove the range and set
            # the new type as "set"
            if c["op"] == operator.eq:  # Operator is "="
                fuzz_action[act_ind]["type"] = "set"
                fuzz_action[act_ind]["value"] = int(c["value"])
                if "range" in fuzz_action[act_ind]:
                    del fuzz_action[act_ind][
                        "range"]  # We remove the range key

            # 3.1.3 Otherwise, we update the range
            else:
                fuzz_action[act_ind]["type"] = "scramble_in_range"
                # Get the absolute range from the operator and the value
                op_range = get_range_op_val(c["op"], int(c["value"]))
                # Intersect the action's range with the range of the
                # condition
                fuzz_action[act_ind]["range"] &= op_range

        # 3.2 Otherwise we create a new action
        else:
            # 3.2.1 Get the new action
            action = get_new_action(field=c['field'],
                                    loc=action_dict['loc'],
                                    size=action_dict["size"],
                                    op=c["op"],
                                    value=int(c["value"]))
            # 3.2.2 Append it to the action list
            fuzz_action.append(action)

    # Finally convert all the IntervalSets to a list of ranges
    for act in fuzz_action:
        if "range" in act:
            if isinstance(act["range"], IntervalSet):
                act["range"] = [[x.inf, x.sup] for x in list(act["range"])]
                if len(act["range"]) == 0:
                    size = COND_TO_FUZZER_ACTION_LUT[act["field"]]["size"]
                    act["range"] = [[x.inf, x.sup] for x in list(IntervalSet((0, int(math.pow(2, 8 * size - 1)))))]

    return fuzz_action
# End def convert_to_fuzzer_actions


# ===== ( Leftover ) ===================================================================================================

# CUSTOM_FIELDS_TO_CDT = {
#     "match_type_is_valid": {
#         "True": {"field": "match_type", "op": operator.eq, "value": 1},
#         "False": {"field": "match_type", "op": operator.ne, "value": 1},
#     },
#     "reason_NoMatch": {
#         "True": {"field": "reason", "op": operator.eq, "value": 0},
#         "False": {"field": "reason", "op": operator.ne, "value": 0},
#     },
#     "reason_Action": {
#         "True": {"field": "reason", "op": operator.eq, "value": 1},
#         "False": {"field": "reason", "op": operator.ne, "value": 1},
#     },
#     "reason_InvalidTTL": {
#         "True": {"field": "reason", "op": operator.eq, "value": 2},
#         "False": {"field": "reason", "op": operator.ne, "value": 2},
#     },
#     "reason_Illegal": {
#         "True": {"field": "reason", "op": operator.gt, "value": 2},
#         "False": {"field": "reason", "op": operator.le, "value": 2},
#     },
#     "oxm_class_NXM_0": {
#         "True": {"field": "oxm_class", "op": operator.eq, "value": 0x0000},
#         "False": {"field": "oxm_class", "op": operator.ne, "value": 0x0000},
#     },
#     "oxm_class_NXM_1": {
#         "True": {"field": "oxm_class", "op": operator.eq, "value": 0x0001},
#         "False": {"field": "oxm_class", "op": operator.ne, "value": 0x0001},
#     },
#     "oxm_class_OPENFLOW_BASIC": {
#         "True": {"field": "oxm_class", "op": operator.eq, "value": 0x8000},
#         "False": {"field": "oxm_class", "op": operator.ne, "value": 0x8000},
#     },
#     "oxm_class_EXPERIMENTER": {
#         "True": {"field": "oxm_class", "op": operator.eq, "value": 0xFFFF},
#         "False": {"field": "oxm_class", "op": operator.ne, "value": 0xFFFF},
#     },
#     "oxm_class_INVALID": {
#         "True": [
#             {"field": "oxm_class", "op": operator.ne, "value": 0x0000},
#             {"field": "oxm_class", "op": operator.ne, "value": 0x0001},
#             {"field": "oxm_class", "op": operator.ne, "value": 0x8000},
#             {"field": "oxm_class", "op": operator.ne, "value": 0xFFFF}
#         ],
#         "False": {"field": "oxm_class", "op": operator.eq, "value": 0x0000},
#     },
#     "match_pad_is_zero": {
#         "True": {"field": "match_pad", "op": operator.eq, "value": 0},
#         "False": {"field": "match_pad", "op": operator.ne, "value": 0}
#     },
#     "pad_is_zero": {
#         "True": {"field": "pad", "op": operator.eq, "value": 0},
#         "False": {"field": "pad", "op": operator.ne, "value": 0}
#     },
#     "ethertype_is_arp": {
#         "True": {"field": "ethertype", "op": operator.eq, "value": 0x0806},
#         "False": {"field": "ethertype", "op": operator.ne, "value": 0x0806},
#     },
#
# }
# class Rule(object):
#     """
#     An object which role is to store a rule
#     """
#
#     # ===== ( Constructor ) ====================================================
#
#     def __init__(self):
#         self.__class = ""
#         self.__conditions = list()
#
#     # End def __init__
#
#     @classmethod
#     def from_string(cls, rule_str: str):
#         """
#         Create a Rule object from a rule string
#         :param rule_str:
#         :return:
#         """
#
#         # Create the new rule
#         new_rule = Rule()
#
#         # Define regex
#         rgx_cdt = r"\(([^(/)]+)\)"
#         rgx_cls_1 = r"(?<==>).*=.*(?=\()"
#         rgx_cls_2 = r"(?<==>).*=.*"
#
#         # Find all criteria and store them in a list
#         criteria_found = findall(rgx_cdt, rule_str)
#         for criterion in criteria_found:
#             params = criterion.split(" ")
#             new_rule.add_condition(field=params[0],
#                                    op=STR_TO_OP_DICT.get(params[1], "="),
#                                    value=params[2])
#
#         # Find to which class the rules applies
#         class_match = search(rgx_cls_1, rule_str)
#         if class_match:
#             new_rule.set_class(class_match.group(0).split("=")[1].strip())
#         else:
#             class_match = search(rgx_cls_2, rule_str)
#             if class_match:
#                 new_rule.set_class(class_match.group(0).split("=")[1].strip())
#
#         return new_rule
#
#     # End def from_string
#
#     @classmethod
#     def from_dict(cls, rule_dict: dict):
#         """
#         Create a Rule object from a rule dict object
#
#         :param rule_dict:
#         :return:
#         """
#
#         new_rule = cls.from_string(rule_dict["conditions"])
#         new_rule.set_class(rule_dict["class"])
#
#         return new_rule
#
#     # End def from_dict
#
#     # ===== ( Overload ) =======================================================
#
#     def __repr__(self):
#         repr_str = ""
#         first = True
#         for cond in self.__conditions:
#             if not first:
#                 repr_str += " and "
#             else:
#                 first = False
#
#             repr_str += "({} {} {})".format(cond["field"],
#                                             OP_TO_STR_DICT.get(cond["op"], "?"),
#                                             cond["value"])
#
#         repr_str += " => class={}".format(self.__class)
#         return repr_str
#
#     # End __repr__
#
#     # ===== ( Getters ) ======================================================
#
#     def get_class(self):
#         return self.__class
#
#     # End def get_class
#
#     def get_conditions(self):
#         return self.__conditions
#
#     # End def get_conditions
#
#     # ===== ( Setters ) ========================================================
#
#     def add_condition(self, field, op, value) -> None:
#         # Check if it is a custom field
#         if field in CUSTOM_FIELDS_TO_CDT:
#             field_dict = deepcopy(CUSTOM_FIELDS_TO_CDT[field][value])
#             if isinstance(field_dict, list):
#                 for field in field_dict:
#                     self.__conditions.append(field)
#             else:
#                 self.__conditions.append(field_dict)
#
#         # Check if the field is known
#         elif field in COND_TO_FUZZER_ACTION_DICT:
#             self.__conditions.append(
#                 {
#                     "field": field,
#                     "op": op,
#                     "value": value
#                 }
#             )
#
#         # Else raise an error
#         else:
#             pass  # TODO: Raise an error
#
#     # End def add_condition
#
#     def set_class(self, lb_cls):
#         self.__class = lb_cls
#
#     # End def set_class
#
#     # ===== ( Methods ) ========================================================
#
#     def to_dict(self):
#         """
#         Convert the rule to a dictionary
#         :return: A dictionary representing the rule
#         """
#         out_dict = dict()
#         cond_str = ""
#         first = True
#
#         for cond in self.__conditions:
#             if not first:
#                 cond_str += " and "
#             else:
#                 first = False
#             cond_str += "({} {} {})".format(cond["field"],
#                                             OP_TO_STR_DICT.get(cond["op"], "?"),
#                                             cond["value"])
#
#         out_dict["conditions"] = cond_str
#         out_dict["class"] = self.get_class()
#
#         return out_dict
#
#     # End def to_dict
#
#     def to_fuzzer_actions(self, negate=False):
#         """ Transform the rules into a set of fuzzer interpretable actions """
#
#         # TODO: handle poorly defined conditions, like "(field > value) and (field < value - 1)" (which is impossible)
#
#         # sub functions
#         def get_range_op_val(op, value):
#             """ Define a range from the operator and the value"""
#             _range = None
#
#             if op == operator.ne:
#                 _range = IntervalSet((-math.inf, value - 1),
#                                      (value + 1, math.inf))
#             elif op == operator.ge:
#                 _range = IntervalSet((value, math.inf))
#             elif op == operator.gt:
#                 _range = IntervalSet((value + 1, math.inf))
#             elif op == operator.le:
#                 _range = IntervalSet((-math.inf, value))
#             elif op == operator.lt:
#                 _range = IntervalSet((-math.inf, value - 1))
#
#             return _range
#
#         # End def get_range_cdt
#
#         def get_new_action(field, loc, size, op, value):
#             new_act = {
#                 "field": field,
#                 "firstByte": loc,
#                 "size": size,
#                 "action": "ByteFieldAction",
#                 # Action is always a byte field action
#                 "type": "unknown"
#             }
#
#             # 2.3.1 determine the type of operation:
#             if op == operator.eq:  # Operator is "="
#                 new_act["type"] = "set"
#                 new_act["value"] = value
#
#             else:  # Operator is ">", ">=", "<" or "<="
#                 new_act["type"] = "scramble_in_range"
#                 # Create the range depending on the size of the field
#                 bounds = IntervalSet((0, int(math.pow(2, 8 * size - 1))))
#                 # Get the absolute range from the operator and the value
#                 _range = get_range_op_val(op, value)
#                 # Intersect the action's range with the range of the
#                 # condition
#                 new_act["range"] = bounds & _range
#
#             return new_act
#
#         # End def get_new_action
#
#         fuzz_action = list()
#         # Parse the rule normally
#         if negate is False:
#             for c in self.__conditions:
#                 # 1. get the dict for the action
#                 action_dict = COND_TO_FUZZER_ACTION_DICT[c["field"]]
#
#                 # 2 Find if there is already an action on the same field
#                 act_ind = next((i for i, item in enumerate(fuzz_action) if
#                                 item["field"] == c["field"]), None)
#                 # 3.1 If we already found an action we merge them if possible
#                 if act_ind is not None:
#                     # 3.1.1 If there is already a set action, we skip all further steps
#                     if fuzz_action[act_ind]["type"] == "set":
#                         continue
#
#                     # 3.1.2 If the new operator is "=", we remove the range and set
#                     # the new type as "set"
#                     if c["op"] == operator.eq:  # Operator is "="
#                         fuzz_action[act_ind]["type"] = "set"
#                         fuzz_action[act_ind]["value"] = int(c["value"])
#                         if "range" in fuzz_action[act_ind]:
#                             del fuzz_action[act_ind][
#                                 "range"]  # We remove the range key
#                     # 3.1.3 Otherwise, we update the range
#                     else:
#                         fuzz_action[act_ind]["type"] = "scramble_in_range"
#                         # Get the absolute range from the operator and the value
#                         op_range = get_range_op_val(c["op"], int(c["value"]))
#                         # Intersect the action's range with the range of the
#                         # condition
#                         fuzz_action[act_ind]["range"] &= op_range
#
#                 # 3.2 Otherwise we create a new action
#                 else:
#                     # 3.2.1 Get the new acction
#                     action = get_new_action(field=c['field'],
#                                             loc=action_dict['loc'],
#                                             size=action_dict["size"],
#                                             op=c["op"],
#                                             value=int(c["value"]))
#                     # 3.2.2 Append it to the action list
#                     fuzz_action.append(action)
#
#         else:
#             for c in self.__conditions:
#                 # 1. get the dict for the action
#                 action_dict = COND_TO_FUZZER_ACTION_DICT[c["field"]]
#
#                 # 2. Negate the operator
#                 cdt = deepcopy(c)
#                 if cdt["op"] == operator.eq:
#                     cdt["op"] = operator.ne  # '='  -> '!='
#                 elif cdt["op"] == operator.ne:
#                     cdt["op"] = operator.eq  # '!=' -> '='
#                 elif cdt["op"] == operator.ge:
#                     cdt["op"] = operator.lt  # '>=' -> '<'
#                 elif cdt["op"] == operator.le:
#                     cdt["op"] = operator.gt  # '<=' -> '>'
#                 elif cdt["op"] == operator.gt:
#                     cdt["op"] = operator.le  # '>'  -> '<='
#                 elif cdt["op"] == operator.lt:
#                     cdt["op"] = operator.ge  # '<'  -> '>='
#
#                 # 3. Create an action for the cdt
#                 action = get_new_action(field=cdt['field'],
#                                         loc=action_dict['loc'],
#                                         size=action_dict["size"],
#                                         op=cdt["op"],
#                                         value=int(cdt["value"]))
#                 # 4. Append the action to the action list
#                 fuzz_action.append(action)
#
#         # Finally convert all the IntervalSets to a list of ranges
#         for act in fuzz_action:
#             if "range" in act:
#                 if isinstance(act["range"], IntervalSet):
#                     act["range"] = [[x.inf, x.sup] for x in list(act["range"])]
#
#         return fuzz_action
#     # End def to_fuzzer_actions
# End class Rule
