#!/usr/bin/env python3
# coding: utf-8
import math
import random
from copy import deepcopy
from re import search

from sympy import *

from rdfl_exp.utils.interval import IntervalSet

# ==== ( Lookup tables ) ==============================================================================================

# LUT to convert "field" conditions into fuzzer actions
FIELD_AS_FEATURE_LUT = {
    # Fields for Fields as feature
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
    "oxm_0_class"   : {"loc": 32, "size": 2},
    "oxm_0_field"   : {"loc": 34, "size": 1},
    "oxm_0_length"  : {"loc": 35, "size": 1},
    "oxm_0_value"   : {"loc": 36, "size": 4},
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

# LUT to convert "bytes" condition into fuzzer actions. The LUT must be generated at least once before usage using the
# function generate_bytes_as_feature_lut
BYTES_AS_FEATURE_LUT = dict()

# LUT to convert "domain knowledge" based conditions into "field" based conditions
DOMAIN_KNOWLEDGE_CDT_LUT = {
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


def generate_bytes_as_feature_lut():
    """Generate the BYTES_AS_FEATURE_LUT automatically."""
    global BYTES_AS_FEATURE_LUT

    BYTES_AS_FEATURE_LUT = dict()
    for i in range(256):
        BYTES_AS_FEATURE_LUT["byte_{}".format(i)] = {'loc': i, 'size': 1}
# End def generate_bytes_as_feature_lut
# ===== ( Rule class ) =================================================================================================


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
        for elem in DOMAIN_KNOWLEDGE_CDT_LUT:
            if elem in tmp_rule:
                tmp_rule = tmp_rule.replace(elem, DOMAIN_KNOWLEDGE_CDT_LUT[elem])

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

    # ====== ( Setters ) ===============================================================================================

    def set_class(self, class_: str):
        self.class_ = class_

    # ====== ( Methods ) ===============================================================================================

    def apply(self):
        models = list(m for m in satisfiable(self.expr, all_models=True))
        # Return a sample of the rule
        return random.sample(models, 1)[0]
# End class Rule


# ===== ( Rule class ) =================================================================================================

def convert_to_fuzzer_actions(rule: Rule):
    """ Transform the rules into a set of fuzzer interpretable actions """

    # TODO: handle poorly defined conditions, like "(field > value) and (field < value - 1)" (which is impossible)

    # First, generate the Bytes-as-Feature LUT if it wasn't done before
    if len(BYTES_AS_FEATURE_LUT) == 0:
        generate_bytes_as_feature_lut()

    # sub functions
    def get_range_from_op_and_val(op, value):
        """ Define a range from the operator and the value"""
        _range = None

        if op == '!=':
            _range = IntervalSet((-math.inf, value - 1), (value + 1, math.inf))
        elif op == ">=":
            _range = IntervalSet((value, math.inf))
        elif op == ">":
            _range = IntervalSet((value + 1, math.inf))
        elif op == "<=":
            _range = IntervalSet((-math.inf, value))
        elif op == "<":
            _range = IntervalSet((-math.inf, value - 1))
        else:
            raise ValueError("Unsupported operator '{}'".format(op))

        return _range
    # End def get_range_cdt

    def get_new_action(field, size, op, value):
        new_act = {
            "intent": "MUTATE_FIELD",
            "fieldName": field,
        }

        # 2.3.1 determine the type of operation:
        if op == '=':
            new_act["intent"] = "SET_FIELD"
            new_act["value"] = value

        else:  # Operator is ">", ">=", "<" or "<="
            new_act["range"] = None
            # Create the range depending on the size of the field
            bounds = IntervalSet((0, int(math.pow(2, 8 * size - 1))))
            # Get the absolute range from the operator and the value
            _range = get_range_from_op_and_val(op, value)
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
            cdt["op"] = '>' if not negate else '<='

        elif '>=' in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('>=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = '>=' if not negate else '<'

        elif '<' in cdt_str and "<=" not in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('<')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = '<' if not negate else '>='

        elif '<=' in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('<=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = '<=' if not negate else '>'

        elif '=' in cdt_str and '!=' not in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = '=' if not negate else '!='

        elif '!=' in cdt_str:
            cdt["field"], cdt["value"] = cdt_str.split('!=')
            cdt["value"] = int(cdt["value"])
            cdt["op"] = '!=' if not negate else '='

        conditions.append(cdt)

    fuzz_action = []
    for c in conditions:
        # 1. get the dict for the action
        if c["field"] in FIELD_AS_FEATURE_LUT:
            action_dict = FIELD_AS_FEATURE_LUT[c["field"]]
        elif c["field"] in BYTES_AS_FEATURE_LUT:
            action_dict = BYTES_AS_FEATURE_LUT[c["field"]]
        else:
            raise RuntimeError("Field {} is not present in the Field-as-Feature's LUT"
                               "nor the Bytes-as-Feature's LUT".format(c["field"]))

        # 2 Find if there is already an action on the same field
        act_ind = next((i for i, item in enumerate(fuzz_action) if item["fieldName"] == c["field"]), None)
        # 3.1 If we already found an action we merge them if possible
        if act_ind is not None:
            # 3.1.1 If there is already a set action, we skip all further steps
            if fuzz_action[act_ind]["intent"] == "SET_FIELD":
                continue

            # 3.1.2 If the new operator is "=", we remove the range and set
            # the new type as "set"
            if c["op"] == '=':  # Operator is "="
                fuzz_action[act_ind]["intent"] = "SET_FIELD"
                fuzz_action[act_ind]["value"] = int(c["value"])
                if "range" in fuzz_action[act_ind]:
                    del fuzz_action[act_ind]["range"]  # We remove the range key

            # 3.1.3 Otherwise, we update the range
            else:
                fuzz_action[act_ind]["intent"] = "MUTATE_FIELD"
                # Get the absolute range from the operator and the value
                op_range = get_range_from_op_and_val(c["op"], int(c["value"]))
                # Intersect the action's range with the range of the
                # condition
                fuzz_action[act_ind]["range"] &= op_range

        # 3.2 Otherwise we create a new action
        else:
            # 3.2.1 Get the new action
            action = get_new_action(field=c['field'],
                                    size=action_dict["size"],
                                    op=c["op"],
                                    value=int(c["value"]))
            # 3.2.2 Append it to the action list
            fuzz_action.append(action)

    # Finally convert all the IntervalSets to a list of ranges
    for act in fuzz_action:
        if "range" in act:
            if isinstance(act['range'], IntervalSet):
                if act['range'].is_empty() is True:
                    act.pop('range', None)  # then the range is no longer needed
                else:
                    act['range'] = [[x.inf, x.sup] for x in list(act['range'])]

    return fuzz_action
# End def convert_to_fuzzer_actions