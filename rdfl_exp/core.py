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
from rdfl_exp.machine_learning.rule import Rule, RuleSet, convert_to_fuzzer_actions
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
    "precision_threshold"   : 1,
    "recall_threshold"      : 1,
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
                "includeHeader": False
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

    # Create variables used by the algorithm
    precision = 0   # Algorithm precision
    recall = 0      # Algorithm recall
    dataset_path = join(config.tmp_dir(), "dataset.csv")  # Create a file where the dataset will be stored
    it = 0  # iteration index
    target_class_ratio = 0.0

    # Initialize the rule set
    rule_set = RuleSet()
    rule_set.target_class = _context["target_class"]
    rule_set.other_class  = _context["other_class"]

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

        # 1. Generate mew data from the rule set
        generate_data_from_ruleset(rule_set, _context["nb_of_samples"])

        # 2. Fetch the dataset
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

        # 3. Perform machine learning algorithms
        start_of_ml = time.time()

        out_rules, evl_result = ml_alg.ripper_cross_validation(
            join(config.tmp_dir(), "dataset.arff"),
            cv_folds=10,
            seed=12345,
            classes=(_context["target_class"], _context["other_class"]))
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

        # Add the rule to the rule set
        rule_set.clear()
        for r in out_rules:
            rule_set.add_rule(r)

        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics and classifier statistics statistics and save the statistics
        Stats.add_iteration_statistics(learning_time=end_of_ml - start_of_ml,
                                       iteration_time=end_of_it - start_of_it,
                                       clsf_res=evl_result,
                                       rule_set=rule_set)  # Add rule_set
        Stats.save(join(config.EXP_PATH, 'stats.json'))

        # Canonicalize the rule set before the next iteration
        if rule_set.has_rules():
            rule_set.canonicalize()
        print(rule_set)

        # Increment the number of iterations
        it += 1

    # Print statistics
    print("Number of iterations:", it)
    print("Final Recall:", recall)
    print("Final Precision:", precision)
    print("Final RuleSet:", rule_set)
# End def run


def generate_data_from_ruleset(rule_set : RuleSet, sample_size : int):

    # If no rules where generated, we use the default fuzzer action and
    # generate the required amount of data
    if not rule_set.has_rules():
        print("No rules in set of rule. Generating random samples")
        _log.info("No rules in set of rule. Generating random samples")

        fuzz_instr = {
            "criteria"  : _context["default_criteria"],
            "matchLimit": _context["default_match_limit"],
            "actions"   : _context["default_actions"]
        }

        # Build the fuzzer instruction and collect 'nb_of_samples' data
        exp_script.run(
            count=sample_size,
            instructions=json.dumps({"instructions": [fuzz_instr]}),
            clear_db=True  # Clear the database before the experiment on the first iteration
        )

    else:

        # Otherwise, we parse the rules and generate data accordingly
        clear_db = True
        for i in range(len(rule_set)):

            # 1. Get the budget for the rule
            budget = math.floor(rule_set.budget(i) * sample_size)

            # 2. Print information
            print(Style.BOLD, "Generating {} samples for Rule {}: ({})".format(budget, i+1, rule_set[i]), Style.RESET)
            progress_bar(0, budget,
                         prefix='Progress:',
                         suffix='Complete ({}/{})'.format(0, budget),
                         length=100)

            # 3. Build the fuzzer instruction
            fuzz_instr = {
                "instructions": [
                    {
                        "criteria"      : _context["default_criteria"],
                        "matchLimit"    : _context["default_match_limit"],
                        "actions"       : [convert_to_fuzzer_actions(rule_set[i])]
                    }
                ]
            }

            # 4. generate the data for the calculated rule
            _log.debug("Fuzzer instructions {}".format(json.dumps(fuzz_instr)))

            for it_ind in range(budget):
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
                progress_bar(it_ind + 1, budget,
                             prefix='Progress:',
                             suffix='Complete ({}/{})'.format(it_ind + 1, budget),
                             length=100)
# End def generate_data_from_ruleset
