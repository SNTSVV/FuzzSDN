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

import rdfl_exp.experiment.data as exp_data
import rdfl_exp.experiment.script as exp_script
import rdfl_exp.machine_learning.algorithms as ml_alg
import rdfl_exp.machine_learning.data as ml_data
from rdfl_exp import config
from rdfl_exp.machine_learning.rule import Rule, convert_to_fuzzer_actions
from rdfl_exp.utils import csv
from rdfl_exp.utils.terminal import Style, progress_bar

# ===== ( Globals ) ============================================================

_log = logging.getLogger("Core")
_is_init = False

_context = {
    # Thresholds
    "precision_th"          : 0,
    "recall_th"             : 0,
    # Defaults
    "default_criteria"      : [],
    "default_match_limit"   : [],
    "default_actions"       : [],
    # Classes
    "class_to_predict"      : None,
    "class_other"           : None,
    # Maximum iterations to do
    "it_max"                : 0,
    # Number of samples to generate per iterations
    "nb_of_samples"         : 0
}
_stats = {
    # Context of the test
    "context": {
        "pid"        : str(),
        "max_it"     : int(),
        "nb_of_it"   : int()
    },
    "time" : {
        "iteration" : list(),
        "learning"  : list()
    },
    # Information about the ml results
    "machine_learning": {
        "nb_of_instances"   : list(),
        "accuracy"          : list(),
        "tp_rate"           : list(),
        "fp_rate"           : list(),
        "precision_score"   : list(),
        "recall_score"      : list(),
        "f_measure"         : list(),
        "mcc"               : list(),
        "roc"               : list(),
        "prc"               : list(),
        "rules"             : list(),
    }
}

_default_input = {
    "n_samples":            500,
    "max_iterations":       50,
    "precision_threshold":  0.85,
    "recall_threshold":     0.85,
    "class_to_predict":     "non_parsing_error",
    "class_other":          "parsing_error",
    "fuzzer": {
        "default_criteria" : [
                {
                    "packetType": "packet_in",
                    "ethType": "arp"
                }
            ],
        "default_match_limit": 1,
        "default_actions": [
            {
                "action": "messagePayloadAction",
                "type": "scramble",
                "percentage": 0.2
            }
        ]
    },
    "initial_rules": []
}


# ===== ( init function ) ==============================================================================================

def init(args) -> None:
    global _log
    global _context
    global _default_input

    # Parse the input file
    if args.in_file:
        with open(args.in_file, "r") as in_file:
            input_data = json.load(in_file)
    else:
        input_data = _default_input
        _log.info("Using the default input")

    _log.info("Parsing the context")
    _context = {
        # Thresholds
        "precision_th"          : input_data["precision_threshold"],  # Precision Threshold
        "recall_th"             : input_data["recall_threshold"],  # Recall Threshold
        # Defaults
        "default_criteria"      : input_data["fuzzer"]["default_criteria"],
        "default_match_limit"   : input_data["fuzzer"]["default_match_limit"],
        "default_actions"       : input_data["fuzzer"]["default_actions"],
        # Classes
        "class_to_predict"      : input_data["class_to_predict"],  # Class to predict
        "class_other"           : input_data["class_other"],  # Class to predict
        # Maximum iterations to do
        "it_max"                : input_data["max_iterations"],
        # Number of samples to generate per iterations
        "nb_of_samples"         : args.samples if args.samples else input_data["n_samples"]
    }

    ## Initialize the statistics
    _stats["context"]["max_it"] = _context["it_max"]

# End def init


# ===== ( RUN function ) ===============================================================================================

def run() -> None:

    global _log
    global _context

    # Run the main loop

    rules = list()  # List of rules
    precision = 0   # Algorithm precision
    recall = 0      # Algorithm recall
    dataset_path = join(config.tmp_dir(), "dataset.csv")  # Create a file where the dataset will be stored

    ## Get the initial rules
    # rules = input_data["initial_rules"] if "initial_rules" in input_data else rules

    # Display header:
    it = 0  # iteration index
    while (it < _context["it_max"]) and (recall < _context["recall_th"] or precision < _context["precision_th"]):

        # Register timestamp at the beginning of the iteration
        start_of_it = time.time()

        # Write headers
        print(Style.BOLD, "*** Iteration {}/{}".format(it + 1, _context["it_max"]), Style.RESET)
        print(Style.BOLD, "*** recall: {}/{}".format(recall, _context["recall_th"]), Style.RESET)
        print(Style.BOLD, "*** precision: {}/{}".format(precision, _context["precision_th"]), Style.RESET)

        generate_rules(rules)

        # Fetch the experiment data
        if not os.path.exists(dataset_path):
            # Fetch the dataset
            exp_data.fetch(dataset_path)
            # Copy the raw version of the dataset to the exp folder
            shutil.copy(src=dataset_path,
                        dst=join(config.EXP_PATH, "datasets",
                                 "it_{}_raw.csv".format(it)))
            # Format the dataset
            ml_data.format_csv(dataset_path, sep=';')
        else:
            # Fetch the data into a temporary dictionary
            tmp_dataset_path = join(config.tmp_dir(), "temp_data.csv")
            exp_data.fetch(tmp_dataset_path)
            # Copy the raw version of the dataset to the exp folder
            shutil.copy(src=tmp_dataset_path,
                        dst=join(config.EXP_PATH, "datasets",
                                 "it_{}_raw.csv".format(it)))
            # Format the dataset
            ml_data.format_csv(tmp_dataset_path, sep=';')
            # Merge the data into the previous dataset
            csv.merge(csv_in=[tmp_dataset_path, dataset_path],
                      csv_out=dataset_path,
                      out_sep=';',
                      in_sep=[';', ';'])

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
            classes=(_context["class_to_predict"], _context["class_other"])
        )
        end_of_ml = time.time()

        # Avoid cases where precision or recall are NaN values
        if math.isnan(evl_result[_context["class_to_predict"]]['recall']):
            recall = 0.0
        if math.isnan(evl_result[_context["class_to_predict"]]['precision']):
            precision = 0.0

        # Assign results from machine learning if it has at least one condition
        print("out_rules:", out_rules)
        rules = [r for r in out_rules if r.get_class() == _context["class_to_predict"]]
        print("final_rules:", rules)
        other_rule = None
        for r in rules:
            if r.get_class() == _context["class_to_predict"]:
                if other_rule is None:
                    other_rule = ~r
                else:
                    other_rule = other_rule & ~r

        print(other_rule)
        if other_rule is not None:
            rules.append(other_rule)

        print(rules)
        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics
        _stats["time"]["iteration"] += [str(end_of_it - start_of_it)]
        _stats["time"]["learning"] += [str(end_of_ml - start_of_ml)]
        # Update the ml statistics
        cls_to_predict = _context["class_to_predict"]
        accuracy = evl_result['correctly_classified'] / evl_result['total_num_instances']
        _stats["machine_learning"]['nb_of_instances']    += [evl_result['total_num_instances']]
        _stats["machine_learning"]["accuracy"]           += [accuracy]
        _stats["machine_learning"]["tp_rate"]            += [evl_result[cls_to_predict]['tp_rate']]
        _stats["machine_learning"]["fp_rate"]            += [evl_result[cls_to_predict]['fp_rate']]
        _stats["machine_learning"]["precision_score"]    += [evl_result[cls_to_predict]['precision']]
        _stats["machine_learning"]["recall_score"]       += [evl_result[cls_to_predict]['recall']]
        _stats["machine_learning"]["f_measure"]          += [evl_result[cls_to_predict]['f_measure']]
        _stats["machine_learning"]["mcc"]                += [evl_result[cls_to_predict]['mcc']]
        _stats["machine_learning"]["roc"]                += [evl_result[cls_to_predict]['roc']]
        _stats["machine_learning"]["prc"]                += [evl_result[cls_to_predict]['prc']]

        _stats["machine_learning"]["rules"] += [[str(r) for r in out_rules]]
        # Update the context statistics
        _stats["context"]["nb_of_it"] = it + 1

        # Save the statistics to the stats
        with open(join(config.EXP_PATH, 'stats.json'), 'w') as stats_file:
            json.dump(_stats, stats_file)

        # Increment the number of iterations
        it += 1

    # Print statistics
    print("Number of iterations:", it)
    print("Final Recall:", recall)
    print("Final Precision:", precision)
    print("Final Rules:", rules)
# End def run


def generate_rules(rules: List[Rule]) -> None:

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
            print_progress_bar=True,
            clear_db=True  # Clear the database before the experiment on the first iteration
        )

    # Otherwise, we parse the rules and generate data accordingly
    else:
        # Calculate the number of times the experiment should be run with the rule
        samples_per_rule = int(math.floor(float(_context["nb_of_samples"]) / len(rules)))
        clear_db = True

        for rule in rules:
            # Get Rule properties
            print(Style.BOLD, "Applying rule: {}".format(rule), Style.RESET)
            progress_bar(0, samples_per_rule,
                         prefix='Progress:',
                         suffix='Complete ({}/{})'.format(0, samples_per_rule),
                         length = 100)

            # If a rule is of the class to predict,  we apply the rule
            # and run the experiment for "nb_of_samples" times
            if rule.get_class() == _context["class_to_predict"]:
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
                            "criteria": _context["default_criteria"],
                            "matchLimit": _context["default_match_limit"],
                            "actions": [
                                _context["default_actions"],
                                *convert_to_fuzzer_actions(rule)
                            ]
                        }
                    ]
                }
            # End if_else rule.get_class()

            # generate the rules
            for i in range(samples_per_rule):
                # Run the script
                exp_script.run(
                    count=1,
                    instructions=json.dumps(fuzz_instr),
                    clear_db=clear_db,
                    print_progress_bar=False
                    # Clear the database before the experiment if it is the first rule
                )
                clear_db = False  # disable the clearing of the database
                # Update the progress bar
                progress_bar(i+1, samples_per_rule,
                             prefix='Progress:',
                             suffix='Complete ({}/{})'.format(i+1, samples_per_rule),
                             length=100)

        # End for rule in rules
    # End if_else len(rule)
# End def generate_rules
