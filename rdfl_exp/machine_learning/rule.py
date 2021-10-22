#!/usr/bin/env python3
# coding: utf-8
import math
import random
from copy import deepcopy
from re import search

from sympy import *
from sympy.logic.boolalg import Boolean, BooleanTrue

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


# ===== ( RuleSet class ) ==============================================================================================

class RuleSet(object):

    # ===== ( Constructor ) ============================================================================================

    def __init__(self, rules=None):
        self.target_class = 'unknown_error'
        self.other_class  = 'known_error'
        self.rules = list() if rules is None else list(rules)
    # End def __init__

    # ===== ( Overrides ) ==============================================================================================

    def __str__(self):
        string = "Ruleset:\n"
        string += "\n".join(str(rule) for rule in self.rules)
        string += "\nNumber of Rules: {}\n".format(len(self.rules))
        string += "Support: {}\n".format(self.support())
        string += "Confidence: {}\n".format(self.confidence())

        return string

    def __getitem__(self, index):
        return self.rules[index]

    def __len__(self):
        return len(self.rules)

    # ===== ( Getters / Setters ) ======================================================================================

    def add_rule(self, rule):
        self.rules.append(rule)
    # End def add_rule

    def get_rules(self):
        return deepcopy(self.rules)
    # End def add_rule

    # ===== ( Methods ) ================================================================================================

    def copy(self, n_rules_limit=None):
        """
        Return a deep copy of ruleset.

        :param n_rules_limit : int (default=None)
            Limit copy to this a subset of original rules.
        """
        result = deepcopy(self)
        if n_rules_limit is not None:
            result.rules = result.rules[:n_rules_limit]
        return result
    # End def copy

    def clear(self):
        self.rules.clear()
    # End def clear

    def has_rules(self):
        # If there is no rule or a single bold rule then return false
        if len(self.rules) <= 1:
            return False
        else:
            return True
    # End def has_rule

    def support(self, idx=None):
        """
        Calculate the support of the ruleset or the rule number 'idx'.

        :param idx: int (default=None)
            The index of the rule we want to get the support for (default=None)
        :returns: float or int
            The support of rule 'idx' between 0 and 1 or the total support of the Ruleset [0-?]
        """
        if idx is None:
            return sum(rule.coverage for rule in self.rules)
        else:
            return self.rules[idx].coverage / self.support()
    # End def support

    def confidence(self, idx=None, relative=False):
        if idx is None:
            return sum(self.confidence(i) * self.support(i) for i in range(len(self)))
        # Else we calculate the confidence of the rule at idx
        elif relative is False:
            rule = self.rules[idx]
            return (rule.coverage - rule.false_positives)/rule.coverage
        else:
            return self.confidence(idx, False) / sum(self.confidence(i) for i in range(len(self)))
    # End def confidence

    def budget(self, idx):
        absolute_budget = self.support(idx) * (1 - self.confidence(idx, True))
        budget_sum = sum(self.support(j) * (1 - self.confidence(j, True)) for j in range(len(self)))
        return absolute_budget / budget_sum
    # End def budget

    # ===== ( Private methods ) ========================================================================================

    # TODO: Privatize method
    def canonicalize(self):
        """
        Canonicalize the ruleset according to the target

        Canonicalization means that the rule set is reworked to have only rules that are relevant to the class we want to predict.
        Which means n detailed rules that predicts the target class and 1 bold rule that predicts the other classes.
        """

        target_rules = list()
        other_rules = list()

        for rule in self:
            if rule.get_class() == self.target_class:
                target_rules.append(rule)
            else:
                other_rules.append(rule)

        other_rules_cvg     = sum(r.coverage for r in other_rules)
        other_rules_fp      = sum(r.false_positives for r in other_rules)
        target_rules_cvg    = sum(r.coverage for r in target_rules)
        target_rules_fp     = sum(r.false_positives for r in target_rules)

        # If the target rule is single and is a bold rule, then we change its expression
        if len(target_rules) == 1 and target_rules[0].expr == None:

            new_target_rule = None
            for other_rule in other_rules:
                if new_target_rule is None:
                    new_target_rule = ~other_rule
                else:
                    new_target_rule &= ~other_rule
            new_target_rule.coverage = target_rules_cvg
            new_target_rule.false_positives = target_rules_fp
            new_target_rule.class_ = self.target_class
            target_rules = list([new_target_rule])

        new_other_rule = None
        for target_rule in target_rules:
            if new_other_rule is None:
                new_other_rule = ~target_rule
            else:
                new_other_rule &= ~target_rule

        new_other_rule.coverage = other_rules_cvg
        new_other_rule.false_positives = other_rules_fp
        new_other_rule.class_ = self.other_class
        other_rules = list([new_other_rule])

        self.rules.clear()
        for r in target_rules:
            self.rules.append(r)
        for r in other_rules:
            self.rules.append(r)
    # End def __canonicalize
# End class RuleSet

# ===== ( Rule class ) =================================================================================================


class Rule(object):

    # ===== ( Constructor ) ====================================================

    def __init__(self, expr, class_=None, cvg=0, fp=0):
        self.expr = to_dnf(expr, simplify=True, force=True)
        self.class_ = class_
        self.coverage = cvg
        self.false_positives = fp
    # End def __init__

    @classmethod
    def from_string(cls, rule_str: str):

        rule_cdt = None
        rule_cls = None
        rule_cvg = None
        rule_fp = None

        # Define the regex used for matching different part if the string
        rgx_rules = r"(?P<rule>.*)(?==>)"  # Regex used to find the class. Matches patterns like "word=word" located after a "=>"
        rgx_cls = r"(?<==>\s)(?P<lbl>\w*)=(?P<cls>\w*)"  # Regex used to find the class. Matches patterns like "word=word" located after a "=>"
        rgx_stats = r"(?<=\()(?P<cvg>\d*.\d*)\/(?P<fp>\d*.\d*)(?=\))"

        # Copy the rule string
        tmp_rule = deepcopy(rule_str)

        # Replace all the elements according to the LUT
        for elem in DOMAIN_KNOWLEDGE_CDT_LUT:
            if elem in tmp_rule:
                tmp_rule = tmp_rule.replace(elem, DOMAIN_KNOWLEDGE_CDT_LUT[elem])

        # Get the class of the rule
        match = search(rgx_cls, rule_str)
        if match:
            rule_cls = match.group("cls").strip()

        # Get the stats of the rule
        match = search(rgx_stats, rule_str)
        if match:
            rule_cvg = int(match.group("cvg").split('.')[0])
            rule_fp = int(match.group("fp").split('.')[0])

        # Match the rules conditions
        match = search(rgx_rules, rule_str)
        if match:
            rule_cdt = match.group("rule").replace(' ', '')  # Remove all spaces
            # Replace the ands and ors by their symbols
            rule_cdt = rule_cdt.replace("and", "&")
            rule_cdt = rule_cdt.replace("or", "|")
            # First replace the parenthesis by brackets and then transform them back
            # to parenthesis. This avoid a parenthesis being handled several times
            rule_cdt = rule_cdt.replace("((", "[symbols['")
            rule_cdt = rule_cdt.replace("))", "']]")
            rule_cdt = rule_cdt.replace("(", "symbols['")
            rule_cdt = rule_cdt.replace(")", "']")
            rule_cdt = rule_cdt.replace("[", "(")
            rule_cdt = rule_cdt.replace("]", ")")

            if rule_cdt != '':
                rule_cdt = eval(rule_cdt)
            else:
                rule_cdt = None

        return Rule(rule_cdt, rule_cls, rule_cvg, rule_fp)
    # End def from_string

    # ===== ( Operator overriding ) ====================================================================================

    def __and__(self, other):

        if self.expr is None and other.expr is None:
            return self
        elif self.expr is None:
            return Rule(to_dnf(other.expr, simplify=True, force=True))
        elif other.expr is None:
            return Rule(to_dnf(self.expr, simplify=True, force=True))
        else:
            return Rule(to_dnf(self.expr & other.expr, simplify=True, force=True))

    def __or__(self, other):
        if self.expr is None and other.expr is None:
            return self
        elif self.expr is None:
            return Rule(to_dnf(other.expr, simplify=True, force=True))
        elif other.expr is None:
            return Rule(to_dnf(self.expr, simplify=True, force=True))
        else:
            return Rule(to_dnf(self.expr | other.expr, simplify=True, force=True))

    def __invert__(self):
        if self.expr is None:
            return self
        else:
            return Rule(to_dnf(~self.expr, simplify=True, force=True))

    # ====== ( Overloading ) ===========================================================================================

    def __repr__(self):
        r_str = str(to_dnf(self.expr, simplify=True, force=True))
        if self.class_ is not None:
            r_str += " => class={} ({}/{})".format(self.class_, self.coverage, self.false_positives)
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


# ===== ( Methods ) =================================================================================================

# TODO: handle poorly defined conditions, like "(field > value) and (field < value - 1)" (which is impossible)
def convert_to_fuzzer_actions(rule: Rule):
    """ Transform the rules into a set of fuzzer interpretable actions """

    # The fuzzer action to be generated
    fuzzer_action = {
        "intent" : "MUTATE_PACKET_RULE",
        "target" : "OF_PACKET",
        "includeHeader": False,
        "rule": list()
    }

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

    def get_new_condition(field, size, op, value):
        new_cdt = {
            "field": field,
        }

        # 2.3.1 determine the type of operation:
        if op == '=':
            new_cdt["range"] = IntervalSet(value, value)

        else:  # Operator is ">", ">=", "<" or "<="
            new_cdt["range"] = None
            # Create the range depending on the size of the field
            bounds = IntervalSet((0, int(math.pow(2, 8 * size))))
            # Get the absolute range from the operator and the value
            _range = get_range_from_op_and_val(op, value)
            # Intersect the action's range with the range of the new condition
            new_cdt["range"] = bounds & _range

        return new_cdt
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

    rule_cdts = []
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
        act_ind = next((i for i, item in enumerate(rule_cdts) if item["field"] == c["field"]), None)
        # 3.1 If we already found an action we merge them if possible
        if act_ind is not None:
            # 3.1.1 If the new operator is "=", we remove the range and set
            # the new type as "set"
            if c["op"] == '=':  # Operator is "="
                rule_cdts[act_ind]["range"] = IntervalSet(int(c["value"]), int(c["value"]))

            # 3.1.2 Otherwise, we update the range
            else:
                # Get the absolute range from the operator and the value
                op_range = get_range_from_op_and_val(c["op"], int(c["value"]))
                # Intersect the action's range with the range of the
                # condition
                rule_cdts[act_ind]["range"] &= op_range

        # 3.2 Otherwise we create a new action
        else:
            # 3.2.1 Get the new action
            action = get_new_condition(field=c['field'], size=action_dict["size"], op=c["op"], value=int(c["value"]))
            # 3.2.2 Append it to the action list
            rule_cdts.append(action)

    # Finally convert all the IntervalSets to a list of ranges
    for act in rule_cdts:
        if "range" in act:
            if isinstance(act['range'], IntervalSet):
                if act['range'].is_empty() is True:
                    act.pop('range', None)  # then the range is no longer needed
                else:
                    act['range'] = [[x.inf, x.sup] for x in list(act['range'])]

    # Finally add the conditions to the rule
    fuzzer_action["rule"] = rule_cdts

    return fuzzer_action
# End def convert_to_fuzzer_actions


# if __name__ == '__main__':
#
#     # test_string = "randomgwrngiwojgi\nnwofwnefowijg\nfnwoinfgwongf\n" + \
#     #     "(reason<200) and (reason!=5) and (reason!=200) and (reason!=132) and (oxm_0_class=4) => class=unknown_error (140.0/2.0)\n" + \
#     #     "(reason<200) and (reason!=5) and (reason!=200) and (reason!=132) and (oxm_0_class=2) => class=unknown_error (125.0/60.0)\n" + \
#     #     " => class=known_error (600.0/2.0)\n" + \
#     #     "fwejkfoiwnfownfg\nfiwjepfjpwijgfe\nfuowefoijwpofjowbgowqg134252"
#     #
#     # import re
#     # rules = []
#     # lines = test_string.split("\n")
#     # for line in lines:
#     #     # Check if the line match the structure of a rule
#     #     if re.match(r'(.*)=>(.*=.*\(.*/.*\))', line):
#     #         print(line)
#     #         rule = Rule.from_string(line)
#     #         if rule is not None:
#     #             rules.append(rule)
#     #
#     # rs1 = RuleSet()
#     # for r in rules:
#     #     rs1.add_rule(r)
#
#
#     r1 = Rule.from_string("(arp_oper<=1) & (arp_plen>=116) => class=unknown_reason (5/1)")
#     # r2 = Rule.from_string("(reason<200) and (reason!=5) and (reason!=200) and (reason!=132) and (oxm_0_class=2) => class=known_error (125.0/60.0)")
#     # r3 = Rule.from_string(" => class=unknown_error (600.0/2.0)")
#
#
#     rs1 = RuleSet([r1)
#     rs1.canonicalize()
#     for i in range(len(rs1)):
#         print("rule {}: {}\n\tconfidence: {}\n\trelative_confidence: {}\n\tsupport: {}\n\tbudget: {}\n\taction: {}".format(
#             i,
#             rs1.rules[i],
#             rs1.confidence(i, relative=False),
#             rs1.confidence(i, relative=True),
#             rs1.support(i),
#             rs1.budget(i),
#             convert_to_fuzzer_actions(rs1[i])))
#
#         print("sum of relative confidences: {}".format(sum(rs1.confidence(i, True) for i in range(len(rs1)))))
#         print("sum of budget: {}".format(sum(rs1.budget(i) for i in range(len(rs1)))))
#
#     # print(convert_to_fuzzer_actions(r1))
#
#
#     # r2 = Rule.from_string("(a<2) and (b<2) and (c>3)=> class=unknown_error (150.0/21.0)")
#     # r3 = Rule.from_string("(d=6) => class=unknown_error (30.0/0.0)")
#     # r4 = Rule.from_string("(c>2) and (a<10) and (c=1)=> class=unknown_error (6.0/1.0)")
#     # r5 = Rule.from_string("(a=2) and (c>1) => class=unknown_error (45.0/43.0)")
#     # r6 = Rule.from_string("(a>2) and (b<2) and (c>3)=> class=unknown_error (23.0/10.0)")
#     # r7 = Rule.from_string("(a<2) and (b>4) => class=unknown_error (300.0/56.0)")
#     # r8 = Rule.from_string("=> class=known_error (4000.0/0.0)")
#     #
#     # rs1 = RuleSet((r1, r2, r3, r4, r5, r6, r7, r8))
#     # rs1.canonicalize()
#     # for i in range(len(rs1)):
#     #     print("rule {}: {}\n\tconfidence: {}\n\trelative_confidence: {}\n\tsupport: {}\n\tbudget: {}".format(
#     #         i,
#     #         rs1.rules[i],
#     #         rs1.confidence(i, relative=False),
#     #         rs1.confidence(i, relative=True),
#     #         rs1.support(i),
#     #         rs1.budget(i)))
#     #
#     #     print("sum of relative confidences: {}".format(sum(rs1.confidence(i, True) for i in range(len(rs1)))))
#     #     print("sum of budget: {}".format(sum(rs1.budget(i) for i in range(len(rs1)))))
