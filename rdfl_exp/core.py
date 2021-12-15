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
from iteround import saferound

import rdfl_exp.experiment.data as exp_data
import rdfl_exp.experiment.script as exp_script
import rdfl_exp.machine_learning.algorithms as ml_alg
import rdfl_exp.machine_learning.data as ml_data
from rdfl_exp import config
from rdfl_exp.machine_learning.rule import CTX_PKT_IN_tmp, Rule, RuleSet, convert_to_fuzzer_actions
from rdfl_exp.stats import Stats
from rdfl_exp.utils import csv
from rdfl_exp.utils.terminal import Style, progress_bar

# ===== ( Globals ) ============================================================

_log = logging.getLogger(__name__)
_is_init = False

_context = {
    # Classifying
    "target_class"          : str(),
    "other_class"           : str(),

    # Iterations
    "nb_of_samples"         : int(),
    "it_max"                : int(),

    # Machine Learning
    "pp_strategy"           : str(),
    "ml_algorithm"          : str(),
    "cv_folds"              : int(),

    # Rule Application
    "enable_mutation"       : bool(),
    "mutation_rate"         : float(),

    # Default fuzzer instructions
    'criteria'              : list(),
    'match_limit'           : int(),
    "default_actions"       : list(),
}

_default_input = {

    # Classifying
    "target_class"          : "unknown_reason",
    "other_class"           : "known_reason",

    # Iterations
    "n_samples"             : 500,
    "max_iterations"        : 50,

    # Machine Learning
    "pp_strategy"           : None,
    "ml_algorithm"          : 'RIPPER',
    "cv_folds"              : 10,

    # Rule Application
    "enable_mutation"       : True,
    "mutation_rate"         : 1.0,

    # Default fuzzer instructions
    "criteria" : [
                {
                    "packetType": "packet_in",
                    "ethType": "arp"
                }
            ],
    "match_limit": 1,
    "default_actions": [
        {
            "intent": "mutate_packet",
            "includeHeader": False
        }
    ]
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

    _log.info("Building experiment context")
    # Fill the context dictionary
    _context = {

        # Classifying
        'target_class'      : input_data['target_class'],  # Class to predict
        'other_class'       : input_data['other_class'],  # Class to predict

        # Iterations
        'it_max'            : input_data['max_iterations'],
        'nb_of_samples'     : args.samples if args.samples else input_data['n_samples'],

        # Machine Learning
        'ml_algorithm'      : args.ml_algorithm if args.ml_algorithm else input_data['ml_algorithm'],
        'pp_strategy'       : args.pp_strategy if args.pp_strategy else input_data['pp_strategy'],
        'cv_folds'          : input_data['cv_folds'],

        # Rule Application
        "enable_mutation"   : args.enable_mutation if args.enable_mutation else input_data['enable_mutation'],
        "mutation_rate"     : args.mutation_rate if args.mutation_rate else input_data['mutation_rate'],

        # Fuzzer Actions
        'criteria'          : input_data['criteria'],
        'match_limit'       : input_data['match_limit'],
        'default_actions'   : input_data['default_actions'],

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

    # Initialize the rule set
    rule_set = RuleSet()
    rule_set.target_class = _context['target_class']
    rule_set.other_class  = _context['other_class']

    ## Get the initial rules
    # rules = input_data["initial_rules"] if "initial_rules" in input_data else rules
    # Display header:
    print(Style.BOLD, "*** Target class: {}".format(_context['target_class']), Style.RESET)
    print(Style.BOLD, "*** Machine learning algorithm: {}".format(_context['ml_algorithm']), Style.RESET)
    print(Style.BOLD, "*** Preprocessing strategy: {}".format(_context['pp_strategy']), Style.RESET)
    print(Style.BOLD, "*** Mutation: {}".format(_context['enable_mutation']), Style.RESET)
    if _context['enable_mutation'] is True:
        print(Style.BOLD, "*** Mutation Rate: {}".format(_context['mutation_rate']), Style.RESET)

    while True:  # Infinite loop

        # Register timestamp at the beginning of the iteration
        start_of_it = time.time()

        # Write headers
        print(Style.BOLD, "*** Iteration {}".format(it + 1), Style.RESET)
        print(Style.BOLD, "*** recall: {:.2f}".format(recall), Style.RESET)
        print(Style.BOLD, "*** precision: {:.2f}".format(precision), Style.RESET)

        # 1. Generate mew data from the rule set
        generate_data_from_ruleset(rule_set, _context['nb_of_samples'])

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
                                   method="faf",
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
                                   method="faf",
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

        # Save the dataset to the experience folder
        shutil.copy(
            src=dataset_path,
            dst=join(config.EXP_PATH, "datasets", "it_{}.csv".format(it))
        )

        # Convert the set to an arff file
        csv.to_arff(
            csv_path=dataset_path,
            arff_path=join(config.tmp_dir(), "dataset.arff"),
            csv_sep=';',
            relation='dataset_iteration_{}'.format(it)
        )

        # Save the arff dataset as well
        shutil.copy(
            src=join(config.tmp_dir(), "dataset.arff"),
            dst=join(config.EXP_PATH, "datasets", "it_{}.arff".format(it))
        )

        # 3. Perform machine learning algorithms
        start_of_ml = time.time()

        ml_results = ml_alg.learn(
            data_path=join(config.tmp_dir(), "dataset.arff"),
            algorithm=_context['ml_algorithm'],
            preprocess_strategy=_context['pp_strategy'],
            n_folds=_context['cv_folds'],
            seed=12345,
            classes=(_context['target_class'], _context["other_class"])
        )
        end_of_ml = time.time()

        # Get recall and precision from the evaluator results
        recall    = ml_results['cross-validation'][_context['target_class']]['recall']
        precision = ml_results['cross-validation'][_context['target_class']]['precision']

        # Avoid cases where precision or recall are NaN values
        recall = 0.0 if math.isnan(recall) else recall
        precision = 0.0 if math.isnan(precision) else precision
        print("Recall: {:.2f}%, Precision: {:.2f}%".format(recall*100, precision*100))

        # Add the rule to the rule set
        rule_set.clear()
        for r in ml_results['rules']:
            rule_set.add_rule(r)

        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics and classifier statistics statistics and save the statistics
        Stats.add_iteration_statistics(
            learning_time=end_of_ml - start_of_ml,
            iteration_time=end_of_it - start_of_it,
            ml_results=ml_results,
            rule_set=rule_set
        )
        Stats.save(join(config.EXP_PATH, 'stats.json'))

        # Canonicalize the rule set before the next iteration
        if rule_set.has_rules():
            rule_set.canonicalize()
        print(rule_set)

        # Increment the number of iterations
        it += 1
    # End of main loop
# End def run


def generate_data_from_ruleset(rule_set : RuleSet, sample_size : int):
    """
    Instructs the fuzzer to generate given amount of data depending on the composition of a ruleset.

    If the rule_set is empty, then the data will be generated randomly.

    :param rule_set: The RuleSet to be used
    :param sample_size: the number of samples to be generated
    """

    # If no rules where generated, we use the default fuzzer action and
    # generate the required amount of data
    if not rule_set.has_rules():
        print("No rules in set of rule. Generating random samples")
        _log.info("No rules in set of rule. Generating random samples")

        fuzz_instr = {
            "criteria"  : _context['criteria'],
            "matchLimit": _context['match_limit'],
            "actions"   : _context['default_actions']
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
        # calculate the budgets
        budget_list = [int(x) for x in saferound([rule_set.budget(i, method=0) * sample_size for i in range(len(rule_set))], places=0)]

        for i in range(len(rule_set)):
            # 1. Get the budget for the rule
            budget = budget_list[i]
            # 2. Print information
            if budget <= 0:
                print(Style.BOLD, "Budget for Rule {}: ({}) is equal to 0".format(i + 1, rule_set[i]),
                      Style.RESET)
                print("skipping the rule...")
                continue

            print(Style.BOLD, "Generating {} samples for Rule {}: ({})".format(budget, i+1, rule_set[i]), Style.RESET)
            progress_bar(0, budget,
                         prefix='Progress:',
                         suffix='Complete ({}/{})'.format(0, budget),
                         length=100)

            # 3. Get all the actions to apply
            # Build a new instruction at each generation
            try:
                action_list = convert_to_fuzzer_actions(rule_set[i],
                                                        include_header=False,
                                                        enable_mutation=_context['enable_mutation'],
                                                        mutation_rate=_context['mutation_rate'],
                                                        n=budget,
                                                        ctx=CTX_PKT_IN_tmp)
            except ValueError as e:
                # Happens if the rule is invalid or impossible to satisfy
                _log.warning("Generation of actions failed with error: {}".format(str(e)))
                _log.warning("Skipping the rule. Less data will be generated.")
                continue

            # 4. Build the fuzzer instruction
            for it_ind in range(len(action_list)):
                fuzz_instr = {
                    "instructions": [
                        {
                            "criteria": _context['criteria'],
                            "matchLimit": _context['match_limit'],
                            "actions": [action_list[it_ind]]
                        }
                    ]
                }

                # 4. generate the data for the calculated rule
                _log.debug("Fuzzer instructions {}".format(json.dumps(fuzz_instr)))

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
