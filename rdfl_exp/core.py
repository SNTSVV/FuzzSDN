#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import math
import os
import shutil
import time
from os.path import join
# Local dependencies
from typing import List

import pandas as pd

import rdfl_exp.experiment.data as exp_data
import rdfl_exp.experiment.script as exp_script
import rdfl_exp.machine_learning.algorithms as ml_alg
import rdfl_exp.machine_learning.data as ml_data
from rdfl_exp import config
from rdfl_exp.machine_learning.rule import Rule, convert_to_fuzzer_actions
from rdfl_exp.stats import Stats
from rdfl_exp.utils import csv
from rdfl_exp.utils.terminal import Style, progress_bar

# ===== ( Globals ) ============================================================

_log = logging.getLogger("Core")
_is_init = False

_context = {
    # Thresholds
    "precision_th"          : 0,
    "recall_th"             : 0,
    "data_format_method"    : '',
    # Defaults
    "default_criteria"      : [],
    "default_match_limit"   : [],
    "default_actions"       : [],
    # Classes
    "target_class"          : None,
    "other_class"           : None,
    # Maximum iterations to do
    "it_max"                : 0,
    # Number of samples to generate per iterations
    "nb_of_samples"         : 0
}

_default_input = {
    "n_samples"             : 500,
    "max_iterations"        : 50,
    "precision_threshold"   : 0.99,
    "recall_threshold"      : 0.99,
    "data_format_method"    : 'faf',
    "target_class"          : "unknown_reason",
    "other_class"           : "known_reason",
    "fuzzer": {
        "default_match_limit": 1,
        "default_criteria" : [
                {
                    "packetType": "packet_in",
                    "ethType": "arp"
                }
            ],
        "default_actions": [
            {
                "intent": "mutate_packet",
                "all": False,
                "includeHeader": False,
                "fieldsToMutateCount": 1
            }
        ]
    },
    "initial_rules": []
}


# ===== ( init function ) ==============================================================================================

def init(args) -> None:
    
    global _context

    # Parse the input file
    if args.in_file:
        with open(args.in_file, "r") as in_file:
            input_data = json.load(in_file)
    else:
        input_data = _default_input
        _log.info("Using the default input")

    _log.info("Parsing the context")
    # Check that the data format method is known
    data_format_method = args.data_format if args.data_format else input_data["data_format_method"]
    if data_format_method not in ('faf', 'faf+dk', 'baf'):
        _log.error("data_format_method should be 'faf', 'faf+dk' or 'baf' (not {})".format(data_format_method))
        raise ValueError("data_format_method should be 'faf', 'faf+dk' or 'baf' (not {})".format(data_format_method))

    # Fill the context dictionary
    _context = {
        # Thresholds
        "precision_th"          : args.precision_th if args.precision_th else input_data["precision_threshold"],  # Precision Threshold
        "recall_th"             : args.recall_th if args.recall_th else input_data["recall_threshold"],  # Recall Threshold
        "data_format_method"    : input_data["data_format_method"],
        # Defaults
        "default_criteria"      : input_data["fuzzer"]["default_criteria"],
        "default_match_limit"   : input_data["fuzzer"]["default_match_limit"],
        "default_actions"       : input_data["fuzzer"]["default_actions"],
        # Classes
        "target_class"          : input_data["target_class"],  # Class to predict
        "other_class"           : input_data["other_class"],  # Class to predict
        # Maximum iterations to do
        "it_max"                : input_data["max_iterations"],
        # Number of samples to generate per iterations
        "nb_of_samples"         : args.samples if args.samples else input_data["n_samples"]
    }

    ## Initialize the statistics
    Stats.init(_context)
# End def init


# ===== ( RUN function ) ===============================================================================================

def run() -> None:

    # Run the main loop
    rules = list()  # List of rules
    precision = 0   # Algorithm precision
    recall = 0      # Algorithm recall
    dataset_path = join(config.tmp_dir(), "dataset.csv")  # Create a file where the dataset will be stored
    it = 0  # iteration index
    target_class_ratio = 0.0

    ## Get the initial rules
    # rules = input_data["initial_rules"] if "initial_rules" in input_data else rules
    # Display header:
    print(Style.BOLD, "*** Precision Threshold: {}".format(_context["precision_th"]), Style.RESET)
    print(Style.BOLD, "*** Recall Threshold: {}".format(_context["recall_th"]), Style.RESET)
    print(Style.BOLD, "*** Target class: {}".format(_context["target_class"]), Style.RESET)

    while (it < _context["it_max"]) and (recall < _context["recall_th"] or precision < _context["precision_th"]):

        # Register timestamp at the beginning of the iteration
        start_of_it = time.time()

        # Write headers
        print(Style.BOLD, "*** Iteration {}/{}".format(it + 1, _context["it_max"]), Style.RESET)
        print(Style.BOLD, "*** recall: {:.2f}/{:.2f}".format(recall, _context["recall_th"]), Style.RESET)
        print(Style.BOLD, "*** precision: {:.2f}/{:.2f}".format(precision, _context["precision_th"]), Style.RESET)

        generate_rules(rules, it, target_class_ratio)

        # Fetch the experiment data
        if not os.path.exists(dataset_path):
            # Fetch the dataset
            exp_data.fetch(dataset_path)
            # Copy the raw version of the dataset to the exp folder
            shutil.copy(src=dataset_path,
                        dst=join(config.EXP_PATH, "datasets",
                                 "it_{}_raw.csv".format(it)))
            # Format the dataset
            ml_data.format_dataset(dataset_path,
                                   method=_context["data_format_method"],
                                   target_error=_context['target_class'],
                                   csv_sep=';')
        else:
            # Fetch the data into a temporary dictionary
            tmp_dataset_path = join(config.tmp_dir(), "temp_data.csv")
            exp_data.fetch(tmp_dataset_path)
            # Copy the raw version of the dataset to the exp folder
            shutil.copy(src=tmp_dataset_path,
                        dst=join(config.EXP_PATH, "datasets",
                                 "it_{}_raw.csv".format(it)))
            # Format the dataset
            ml_data.format_dataset(tmp_dataset_path,
                                   method=_context["data_format_method"],
                                   target_error=_context['target_class'],
                                   csv_sep=';')
            # Merge the data into the previous dataset
            csv.merge(csv_in=[tmp_dataset_path, dataset_path],
                      csv_out=dataset_path,
                      out_sep=';',
                      in_sep=[';', ';'])
            # Get the ratio of target_class
            df = pd.read_csv(dataset_path, sep=";")
            # Get the class count
            classes_count = df['class'].value_counts()
            total = classes_count[_context['target_class']] + classes_count[_context['other_class']]
            target_class_ratio = float(float(classes_count[_context['target_class']]) / total)

        # Save the dataset to the experience folder
        shutil.copy(src=dataset_path,
                    dst=join(config.EXP_PATH, "datasets", "it_{}.csv".format(it)))

        # Convert the set to an arff file
        csv.to_arff(
            csv_path=dataset_path,
            arff_path=join(config.tmp_dir(), "dataset.arff"),
            csv_sep=';',
            relation='dataset_iteration_{}'.format(it)
        )

        # Perform machine learning algorithms
        start_of_ml = time.time()

        out_rules, evl_result = ml_alg.standard(
            join(config.tmp_dir(), "dataset.arff"),
            tt_split=70.0,
            cv_folds=10,
            seed=12345,
            classes=(_context["target_class"], _context["other_class"])
        )
        end_of_ml = time.time()

        # Get recall and precision from the evaluator results
        recall    = evl_result[_context["target_class"]]['recall']
        precision = evl_result[_context["target_class"]]['precision']

        # Avoid cases where precision or recall are NaN values
        if math.isnan(recall):
            recall = 0.0
        if math.isnan(precision):
            precision = 0.0

        print("Recall: {:.2f}%, Precision: {:.2f}%".format(recall*100, precision*100))

        # Get the rules that correspond to the target class
        rules = [r for r in out_rules if r.get_class() == _context["target_class"]]

        # Create a new rule which will be a the negation of all the rules for the other class
        # example: For R1 = a and b, R2 = c and d, we'll have a new rule R = ~R1 and ~R2 = (a or b) and (c or d)
        other_rule = None
        for r in [r for r in out_rules if r.get_class() != _context["target_class"]]:
            if other_rule is None:
                other_rule = ~r
            else:
                other_rule = other_rule & ~r

        if other_rule is not None:
            other_rule.set_class(_context['target_class'])
            rules.append(other_rule)

        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics and classifier statistics statistics and save the statistics
        Stats.add_iteration_statistics(learning_time=end_of_ml - start_of_ml,
                                       iteration_time=end_of_it - start_of_it,
                                       clsf_res=evl_result,
                                       rules=out_rules)  # Add out_rules instead of rules
        Stats.save(join(config.EXP_PATH, 'stats.json'))

        # Increment the number of iterations
        it += 1

    # Print statistics
    print("Number of iterations:", it)
    print("Final Recall:", recall)
    print("Final Precision:", precision)
    print("Final Rules:", rules)
# End def run


def generate_rules(rules: List[Rule], it_ind, target_class_ratio) -> None:

    # If no rules where generated, we use the default fuzzer action and
    # generate the required amount of data
    if len(rules) <= 0:

        print("No rules in set of rule. Generating random samples")
        _log.info("No rules in set of rule. Generating random samples")

        fuzz_instr = {
            "criteria"  : _context["default_criteria"],
            "matchLimit": _context["default_match_limit"],
            "actions"   : _context["default_actions"]
        }

        # Build the fuzzer instruction and collect 'nb_of_samples' data
        exp_script.run(
            count=_context["nb_of_samples"],
            instructions=json.dumps({"instructions": [fuzz_instr]}),
            clear_db=True  # Clear the database before the experiment on the first iteration
        )

    # Otherwise, we parse the rules and generate data accordingly
    else:

        nb_of_rules = len(rules)
        rules_weight = [[r, int(math.floor(_context["nb_of_samples"] / len(rules)))] for r in rules]

        # If the ratio of the target_class is above 0.5, generate half of the data with rule and the other half using
        # the opposite of the rules. For that we negate each rule and add it to the list of rules
        print("target_class_ratio:", target_class_ratio)

        if target_class_ratio > 0.5:

            _log.info("target_class_ratio ratio is above 50%")
            print("target_class_ratio ratio is above 50%")

            target_class_rules = [rule for rule in rules if rule.get_class() == _context['target_class']]
            # other_class_rules = [rule for rule in rules if rule.get_class() == _context['other_class']]

            opposite_rule = None

            # Negate the rules for the target class
            if len(target_class_rules) > 0:
                _log.debug("Negating the rules for the target class...")

                for tcr in target_class_rules:
                    opposite_rule = ~tcr if opposite_rule is None else opposite_rule | ~tcr
                opposite_rule.set_class(_context['other_class'])

            # Print log messages with all the rules to be applied
            _log.debug("Negated rules:")
            if _log.isEnabledFor(logging.DEBUG):
                _log.debug("Opposite Rule: {}".format(opposite_rule))

            # # First, negate all the rules
            # negated_rules = []
            # for rule in rules:
            #     rule_copy = deepcopy(rule)
            #     not_rule = ~rule_copy
            #     # Optional step: Invert the target
            #     if rule.get_class() == _context['target_class']:
            #         not_rule.set_class(_context['other_class'])
            #     else:
            #         not_rule.set_class(_context['target_class'])
            #     negated_rules.append(not_rule)
            # # Add the negated rules to the current set of rules
            # rules.extend(negated_rules)

            target_ratio = 0.5
            x_factor = int(
                math.floor(
                    target_ratio * _context["nb_of_samples"] * (it_ind + 1) - (_context["nb_of_samples"] * it_ind * target_class_ratio)
                )
            )

            target_nb_samples = 0
            if x_factor <= 0:
                target_nb_samples = 0
                other_nb_samples = _context["nb_of_samples"]

            elif x_factor > _context["nb_of_samples"]:
                target_nb_samples = _context["nb_of_samples"]
                other_nb_samples = 0

            else:
                target_nb_samples = x_factor
                other_nb_samples = int(_context["nb_of_samples"] - x_factor)

            for rule in rules_weight:
                rule[1] = int(math.floor(target_nb_samples / len(rules_weight)))

            # Add the negated rules to the current set of rules
            rules_weight.append([opposite_rule, other_nb_samples])

        info_str = "Rules to be applied:"
        for i in range(len(rules_weight)):
            info_str += "\n\tRules {}: {}, nb_of_samples: {} ".format(i + 1, rules_weight[i][0], rules_weight[i][1])
        print(info_str)
        _log.info(info_str)

        # Calculate the number of times the experiment should be run with the rule
        # samples_per_rule = int(math.floor(float(_context["nb_of_samples"]) / len(rules)))
        clear_db = True

        rule_it = 0  # rule iteration counter
        # weight_sum = sum([item[1] for item in rules_weight])  # Sum of all the weights
        for rule, nb_of_samples in rules_weight:

            # Skip all those steps if no samples need to be generated
            if nb_of_samples == 0:
                continue

            _log.debug("{} samples to be generated for rule {}".format(nb_of_samples, rule_it+1))

            # Get Rule properties
            print(Style.BOLD, "Generating {} samples for Rule {}: ({})".format(nb_of_samples, rule_it+1, rule), Style.RESET)
            progress_bar(0, nb_of_samples,
                         prefix='Progress:',
                         suffix='Complete ({}/{})'.format(0, nb_of_samples),
                         length=100)

            # If a rule is of the class to predict,  we apply the rule
            # and run the experiment for "nb_of_samples" times
            if rule.get_class() == _context["target_class"]:
                fuzz_instr = {
                    "instructions": [
                        {
                            "criteria"      : _context["default_criteria"],
                            "matchLimit"    : _context["default_match_limit"],
                            "actions"       : convert_to_fuzzer_actions(rule)
                        }
                    ]
                }
            # If a rule not of the class to predict, we get the opposite fuzzer actions
            # and we get a sample of the opposite fuzzer actions and generate 1 data point.
            # 'nb_of_samples' times
            else:
                fuzz_instr = {
                    "instructions": [
                        {
                            "criteria"      : _context["default_criteria"],
                            "matchLimit"    : _context["default_match_limit"],
                            "actions"       : [*_context["default_actions"], *convert_to_fuzzer_actions(rule)]
                        }
                    ]
                }
            # End if_else rule.get_class()

            # generate the rules
            _log.debug("Fuzzer instructions {}".format(json.dumps(fuzz_instr)))
            for it_ind in range(nb_of_samples):
                # Run the script
                exp_script.run(
                    count=1,
                    instructions=json.dumps(fuzz_instr),
                    clear_db=clear_db,
                    quiet=True
                    # Clear the database before the experiment if it is the first rule
                )
                clear_db = False  # disable the clearing of the database
                # Update the progress bar
                progress_bar(it_ind + 1, nb_of_samples,
                             prefix='Progress:',
                             suffix='Complete ({}/{})'.format(it_ind + 1, nb_of_samples),
                             length=100)
            # Increment the rule iteration counter
            rule_it += 1
        # End for rule in rules
    # End if_else len(rule)
# End def generate_rules
