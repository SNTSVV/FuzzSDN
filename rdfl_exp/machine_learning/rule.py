#!/usr/bin/env python3
# coding: utf-8
import math
import random
from copy import deepcopy
import re as RegEx

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
    "oxm_0_has_mask": {"loc": 34, "size": 1},
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
        self.target_class = 'unknown_reason'
        self.other_class  = 'known_reason'
        self.rules = list() if rules is None else list(rules)
    # End def __init__

    # ===== ( Overrides ) ==============================================================================================

    def __str__(self):
        string = "Rules:\n"
        string += "\n".join("\t" + str(rule) for rule in self.rules)
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
        Canonicalize the ruleset.

        A ruleset is in its canon form when the bold rules clauses is the proper neagation of all the other rules. and not None
        """

        std_rules = list()
        bold_rule = None

        for rule in self:
            if rule.expr is None:
                bold_rule = rule
            else:
                std_rules.append(rule)

        # Not in canon form and not a single bold rule
        if bold_rule is not None and len(std_rules) > 0:
            # If the target rule is single and is a bold rule, then we change its expression
            bold_rule_cvg = bold_rule.coverage
            bold_rule_fp  = bold_rule.false_positives
            bold_rule_cls = bold_rule.class_

            bold_rule = None
            for rule in std_rules:
                if bold_rule is None:
                    bold_rule = ~rule
                else:
                    bold_rule &= ~rule

            bold_rule.coverage = bold_rule_cvg
            bold_rule.false_positives = bold_rule_fp
            bold_rule.class_ = bold_rule_cls

            self.rules.clear()
            for r in std_rules:
                self.rules.append(r)
            self.rules.append(bold_rule)
    # End def __canonicalize
# End class RuleSet

# ===== ( Rule class ) =================================================================================================


class Rule(object):

    # ===== ( Constructor ) ====================================================

    def __init__(self, expr, class_=None, cvg: float = 0.0, fp: float = 0.0):
        self.expr = expr
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
        rgx_stats = r"(?<=\()(?P<cvg>\d+.\d+)\/(?P<fp>\d+.\d+)(?=\))"

        # Copy the rule string
        tmp_rule = deepcopy(rule_str)

        # Replace all the elements according to the LUT
        for elem in DOMAIN_KNOWLEDGE_CDT_LUT:
            if elem in tmp_rule:
                tmp_rule = tmp_rule.replace(elem, DOMAIN_KNOWLEDGE_CDT_LUT[elem])

        # Get the class of the rule
        match = RegEx.search(rgx_cls, str(rule_str))
        if match:
            rule_cls = match.group("cls").strip()

        # Get the stats of the rule
        match = RegEx.search(rgx_stats, rule_str)
        if match:
            rule_cvg = float(match.group("cvg"))
            rule_fp = float(match.group("fp"))

        # Match the rules conditions
        match = RegEx.search(rgx_rules, rule_str)
        if match:
            rule_cdt = match.group("rule").replace(' ', '')  # Remove all spaces

            # Replace the ands and ors by their symbols
            rule_cdt = rule_cdt.replace("and", "&")
            rule_cdt = rule_cdt.replace("or", "|")

            match = RegEx.findall(r'(\w+[><=!].{1,2}\d+)', rule_cdt)
            processed_match = list()
            for m in match:
                if m not in processed_match:
                    rule_cdt = rule_cdt.replace(m, "symbols('{}')".format(m))
                    processed_match.append(m)

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
            return Rule(other.expr)
        elif other.expr is None:
            return Rule(self.expr)
        else:
            return Rule(self.expr & other.expr)

    def __or__(self, other):
        if self.expr is None and other.expr is None:
            return self
        elif self.expr is None:
            return Rule(other.expr)
        elif other.expr is None:
            return Rule(self.expr)
        else:
            return Rule(self.expr | other.expr)

    def __invert__(self):
        if self.expr is None:
            return self
        else:
            return Rule(~self.expr)

    # ====== ( Overloading ) ===========================================================================================

    def __repr__(self):
        r_str = str(self.expr)
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
        # models = list(m for m in satisfiable(self.expr, all_models=True))
        # Return a sample of the rule
        # return random.sample(models, 1)[0]

        # for DNFs only
        def __clauses(expr) -> tuple:
            if not isinstance(expr, Or):
                return expr,
            return expr.args

        clauses = __clauses(to_dnf(self.expr))
        it_count = 0
        it_limit = 10 * len(clauses)
        model = None

        while (type(model) == bool or model is None) and it_count < it_limit:
            clause_set = random.sample(clauses, random.randint(1, len(clauses)))
            new_expr = None
            for clause in clause_set:
                if new_expr is None:
                    new_expr = clause
                else:
                    new_expr &= clause
            # End for

            model = satisfiable(new_expr)
            it_count += 1

        return model
    # End def apply

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
    if app_dict is None:
        raise ValueError("The rule \"{}\"cannot be translated to fuzzer action".format(r))

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
                               " nor the Bytes-as-Feature's LUT".format(c["field"]))

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