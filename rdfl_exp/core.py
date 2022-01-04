#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import math
import os
import shutil
import time
from os.path import join

import pandas as pd
from iteround import saferound

import rdfl_exp.experiment.data as exp_data
import rdfl_exp.machine_learning.algorithms as ml_alg
import rdfl_exp.machine_learning.data as ml_data
from rdfl_exp import config
from rdfl_exp.experiment.experimenter import Experimenter, FuzzMode
from rdfl_exp.machine_learning.rule import CTX_PKT_IN_tmp, RuleSet, convert_to_fuzzer_actions
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
}


# ===== ( init function ) ==============================================================================================

def init(args) -> None:

    global _context

    #

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
        "enable_mutation"   : args.enable_mutation if args.enable_mutation is not None else input_data['enable_mutation'],
        "mutation_rate"     : args.mutation_rate if args.mutation_rate else input_data['mutation_rate'],
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

    # Set up the experimenter
    experimenter = Experimenter()
    experimenter.mutation_rate = _context['mutation_rate']
    experimenter.set_scenario("onos_2node_1ping")
    experimenter.set_criterion("first_arp_message")

    while True:  # Infinite loop

        # Register timestamp at the beginning of the iteration
        start_of_it = time.time()

        # Write headers
        print(Style.BOLD, "*** Iteration {}".format(it + 1), Style.RESET)
        print(Style.BOLD, "*** recall: {:.2f}".format(recall), Style.RESET)
        print(Style.BOLD, "*** precision: {:.2f}".format(precision), Style.RESET)

        # 1. Generate mew data from the rule set

        if not rule_set.has_rules():
            print("No rules in set of rule. Generating random samples")
            _log.info("No rules in set of rule. Generating random samples")
            experimenter.set_fuzzing_mode(FuzzMode.RANDOM)
            experimenter.set_rule_set(None)
            experimenter.run(_context['nb_of_samples'])
        else:
            experimenter.set_fuzzing_mode(FuzzMode.RULE)
            experimenter.set_rule_set(rule_set)
            experimenter.run(_context['nb_of_samples'])

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
            relation='dataset_iteration_{}'.format(it),
            exclude=['pkt_struct', 'fuzz_info', 'action']
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
