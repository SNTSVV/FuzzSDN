#!/usr/bin/env python3
# coding: utf-8
import itertools
import operator
import random
from copy import deepcopy
import re as RegEx
from datetime import datetime
from typing import List

import sympy
from sympy import *
from z3 import z3

from rdfl_exp.utils import smt

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


# TODO: Calculate ctx when parsing a packet from the input data
CTX_PKT_IN_tmp = {
    # Fields for Fields as feature
    "of_version"    : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "of_type"       : {"min": 0, "max": int(pow(2, 8*1) - 1)},
    "length"        : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "xid"           : {"min": 0, "max": int(pow(2, 8*4) - 1)},
    "buffer_id"     : {"min": 0, "max": int(pow(2, 8*4) - 1)},
    "total_len"     : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "reason"        : {"min": 0, "max": int(pow(2, 8*1) - 1)},
    "table_id"      : {"min": 0, "max": int(pow(2, 8*1) - 1)},
    "cookie"        : {"min": 0, "max": int(pow(2, 8*8) - 1)},
    "match_type"    : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "match_length"  : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "match_pad"     : {"min": 0, "max": int(pow(2, 8*4) - 1)},
    "oxm_0_class"   : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "oxm_0_field"   : {"min": 0, "max": int(pow(2, 7)   - 1)},
    "oxm_0_has_mask": {"min": 0, "max": 1},
    "oxm_0_length"  : {"min": 0, "max": int(pow(2, 8*1) - 1)},
    "oxm_0_value"   : {"min": 0, "max": int(pow(2, 8*4) - 1)},
    "pad"           : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "eth_dst"       : {"min": 0, "max": int(pow(2, 8*6) - 1)},
    "eth_src"       : {"min": 0, "max": int(pow(2, 8*6) - 1)},
    "ethertype"     : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "arp_htype"     : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "arp_ptype"     : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "arp_hlen"      : {"min": 0, "max": int(pow(2, 8*1) - 1)},
    "arp_plen"      : {"min": 0, "max": int(pow(2, 8*1) - 1)},
    "arp_oper"      : {"min": 0, "max": int(pow(2, 8*2) - 1)},
    "arp_sha"       : {"min": 0, "max": int(pow(2, 8*6) - 1)},
    "arp_spa"       : {"min": 0, "max": int(pow(2, 8*4) - 1)},
    "arp_tha"       : {"min": 0, "max": int(pow(2, 8*6) - 1)},
    "arp_tpa"       : {"min": 0, "max": int(pow(2, 8*4) - 1)},
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

    def budget(self, idx, method: int = 0):
        to_return = None
        if method == 0:
            absolute_budget = self.support(idx) * (1 - self.confidence(idx, True))
            budget_sum = sum(self.support(j) * (1 - self.confidence(j, True)) for j in range(len(self)))
            to_return = absolute_budget / budget_sum

        elif method == 1:
            absolute_budget = self.support(idx) * (self.confidence(idx, True))
            budget_sum = sum(self.support(j) * (self.confidence(j, True)) for j in range(len(self)))
            to_return = absolute_budget / budget_sum

        return to_return
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
        bold_rule_id = None

        for rule in self:
            if rule.expr is None:
                bold_rule = rule
                bold_rule_id = rule.id
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

            bold_rule.id = bold_rule_id

            self.rules.clear()
            for r in std_rules:
                self.rules.append(r)
            self.rules.append(bold_rule)
    # End def __canonicalize
# End class RuleSet

# ===== ( Rule class ) =================================================================================================


class Rule(object):

    new_id = itertools.count()

    # ===== ( Constructor ) ====================================================

    def __init__(self, expr, class_=None, cvg: float = 0.0, fp: float = 0.0, _id=None):
        self.expr = expr
        self.class_ = class_
        self.coverage = cvg
        self.false_positives = fp

        if _id is None:
            self.id = next(Rule.new_id)
        else:
            self.id = _id
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

            match = RegEx.findall(r'(\w+[><=!]{1,2}\d+)', rule_cdt)
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
            return other
        elif other.expr is None:
            return Rule(self.expr)
        else:
            return Rule(self.expr & other.expr)

    def __or__(self, other):
        if self.expr is None and other.expr is None:
            return self
        elif self.expr is None:
            return other
        elif other.expr is None:
            return Rule(self.expr)
        else:
            return Rule(self.expr | other.expr)

    def __invert__(self):
        if self.expr is None:
            return self
        else:
            return Rule(~self.expr)
    # End def __invert__

    # ====== ( Overloading ) ===========================================================================================

    def __repr__(self):
        return "Rule@{:05d}: {} => class={} ({}/{})".format(self.id, str(self.expr), self.class_, self.coverage, self.false_positives)
    # End def __repr__

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
    # End def __apply_v1

    def get_models(self, n, ctx=None) -> List[dict]:

        z3.set_option('smt.arith.random_initial_value', True)

        # Convert rule to cnf form
        cnf_expr = to_cnf(self.expr)

        # Compile the regex use for finding symble
        rgx_sym         = RegEx.compile(r'(?P<symbol>\w+) *(?P<operator>[><=!]{1,2}) *(?P<value>\d+)')
        rgx_sym_and_not = RegEx.compile(r'(?P<symbol>~*\w+) *(?P<operator>[><=!]{1,2}) *(?P<value>\d+)')
        # match = RegEx.findall(rgx_sym, cnf_expr)

        # Create a list of symbols present in the equation
        matches = [m.groupdict() for m in rgx_sym.finditer(str(cnf_expr))]
        symbols = {}
        for m in matches:
            symbols[m['symbol']] = z3.Int(m['symbol'])

        def cnf_clauses(expr) -> tuple:
            if not isinstance(expr, sympy.And):
                return expr,
            return expr.args

        # List the operator
        ops = {
            '>'  : operator.gt,
            '>=' : operator.ge,
            '<'  : operator.lt,
            '<=' : operator.le,
            '!=' : operator.ne,
            '='  : operator.eq,
            '==' : operator.eq,
        }

        # Build the z3 formula
        z3_formula = []
        ands = []
        for cl in cnf_clauses(cnf_expr):
            matches = [m.groupdict() for m in rgx_sym_and_not.finditer(str(cl))]
            ors = []
            for m in matches:
                if m['symbol'].startswith('~'):  # Not symbol
                    symbol = m['symbol'].replace('~', '')
                    ors += [z3.Not(ops[m['operator']](symbols[symbol], int(m['value'])))]
                else:
                    ors += [ops[m['operator']](symbols[m['symbol']], int(m['value']))]
            ands += [z3.Or(*ors)]

        z3_formula += [z3.And(*ands)]

        # Add the context to the formula
        if ctx is not None:
            for field in ctx.keys():
                if field in symbols.keys():
                    z3_formula += [symbols[field] >= ctx[field]['min']]
                    z3_formula += [symbols[field] <= ctx[field]['max']]

        models = []
        # use a random seed so the same model is not generated twice
        z3.set_option('auto_config', False)
        z3.set_option('smt.arith.random_initial_value', True)
        z3.set_option('smt.random_seed', datetime.now().microsecond)
        z3.set_option('smt.phase_selection', 5)
        z3_models = smt.get_model(z3_formula, n, exact=True)  # Get z3 models
        # Build the dictionary
        for z3_model in z3_models:
            model = dict()
            for k in symbols.keys():
                model[k] = z3_model[symbols[k]].as_long()
            models.append(model)

        return models
    # End def get models
# End class Rule


# ===== ( Methods ) =================================================================================================

# TODO: handle poorly defined conditions, like "(field > value) and (field < value - 1)" (which is impossible)
def convert_to_fuzzer_actions(rule: Rule,
                              n: int = 1,
                              include_header: bool = False,
                              enable_mutation: bool = True,
                              mutation_rate: float = 1.0,
                              ctx: dict = None):
    """ Transform the rules into a set of fuzzer interpretable actions """

    # Verify arguments
    if n < 1:
        raise ValueError("\"n\" must be >= 1 (got: {})".format(n))

    # Prepare actions
    fuzzer_actions = list()
    # The fuzzer action to be generated
    single_action = {
        "intent" : "MUTATE_PACKET_RULE",
        "target" : "OF_PACKET",
        "includeHeader": include_header,
        "enableMutation": enable_mutation,
        "rule": {
            "id": rule.id,
            "clauses": list()
        }
    }

    if enable_mutation:
        single_action['mutationRateMultiplier'] = mutation_rate

    # get the Models
    models = rule.get_models(n, ctx)

    for model in models:
        action = deepcopy(single_action)
        for field in model.keys():
            action['rule']["clauses"].append(
                {
                    'field': field,
                    'value': model[field]
                }
            )
        fuzzer_actions.append(action)

    return fuzzer_actions
# End def convert_to_fuzzer_actions