#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import grp
import json
import logging
import math
import os
import pwd
import re
import shutil
import signal
import sys
import time
import traceback
from os.path import join

import pandas as pd
from weka.core import jvm, packages

from rdfl_exp import setup
from rdfl_exp.config import DEFAULT_CONFIG as CONFIG
from rdfl_exp.experiment import data as exp_data
from rdfl_exp.experiment.experimenter import Experimenter, FuzzMode
from rdfl_exp.machine_learning import algorithms as ml_alg
from rdfl_exp.machine_learning import data as ml_data
from rdfl_exp.machine_learning.rule import RuleSet
from rdfl_exp.stats import Stats
from rdfl_exp.utils import csv, file
from rdfl_exp.utils.terminal import Style

# ===== ( locals ) ============================================================

_log = logging.getLogger(__name__)
_is_init = False
_crashed = False

_context = {
    # Classifying
    "scenario"              : str(),
    "criterion"             : {
        "name"      : str(),
        "kwargs"    : dict()
    },
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


# ===== ( Setup functions ) ============================================================================================

def parse_arguments():
    """
    Parse the arguments passed to the program.
    """
    parser = argparse.ArgumentParser(description="Run a feedback loop experiment")

    # ===== ( Generic args ) ===========================================================================================

    parser.add_argument('--no-clean',
                        action='store_false',
                        help="Do not perform cleaning actions on exit")

    # ===== ( Experiment args ) ========================================================================================

    # Positional argument to choose the target
    error_types = ('unknown_reason', 'known_reason', 'parsing_error', 'non_parsing_error')
    parser.add_argument('target_class',
                        metavar='ERROR_TYPE',
                        choices=error_types,
                        help="Choose the error type to detect. Allowed values are: " + ', '.join(["\'{}\'".format(e) for e in error_types]))

    # Positional argument to choose the machine learning algorithm
    parser.add_argument('scenario',
                        metavar='SCENARIO',
                        type=str,
                        help="Name of the scenario to be run")

    # Positional argument to choose the criterion
    # Break criterion positional argument in two names to circumvent the bug where a positional argument can't have several
    # kwargs defines (python issue 14074: https://bugs.python.org/issue14074)
    parser.add_argument('criterion_name',
                        metavar='CRITERION',
                        type=str,
                        help="Name of the criterion to be run")

    parser.add_argument('criterion_kwargs',
                        metavar='kwargs',
                        nargs='*',
                        type=str,
                        help="kwargs for the criterion (optional)")

    # Argument to choose the number of sample to generate
    parser.add_argument('-s', '--samples',
                        type=int,
                        default=300,
                        dest='samples',
                        help="Override the number of samples. (default: %(default)s)")

    # ===== ( Machine Learning args ) ==================================================================================
    # Argument to choose the machine learning algorithm
    parser.add_argument('-M, --ml-algorithm',
                        type=str,
                        default='RIPPER',
                        dest='ml_algorithm',
                        help="Select which machine algorithm to use. (default: \"%(default)s\")")

    # Argument to choose the preprocessing strategy
    parser.add_argument('-P', '--preprocessing-strategy',
                        type=str,
                        default='SMOTE-5',
                        dest='pp_strategy',
                        help="Select which preprocessing strategy to use. (default: \"%(default)s\")")

    # Argument to choose disable the mutation of additional fields
    parser.add_argument('--cross-validation-folds',
                        type=int,
                        default=10,
                        dest='cv_folds',
                        help="Define the number of folds to use during cross-validation. (default: %(default)s)")

    # ===== ( Fuzzing args ) ===========================================================================================
    # Argument to choose disable the mutation of additional fields
    parser.add_argument('--disable-mutation',
                        action='store_false',
                        dest='enable_mutation',
                        help="Disable the mutation of additional fields upon rule application.")

    # Argument to choose the mutation rate of additional fields
    parser.add_argument('--mutation-rate',
                        type=float,
                        default=1.0,
                        dest='mutation_rate',
                        help="Sets the mutation rate of additional fields upon rule application. (default: %(default)s)")

    # Parse the arguments
    args = parser.parse_args()

    # Deduce the other_class
    setattr(args, 'other_class', None)

    if args.target_class == "known_reason":
        args.other_class = "unknown_reason"

    elif args.target_class == "unknown_reason":
        args.other_class = "known_reason"

    elif args.target_class == "parsing_error":
        args.other_class = "non_parsing_error"

    elif args.target_class == "non_parsing_error":
        args.other_class = "parsing_error"

    # Format the criterion
    if args.criterion_kwargs:
        kwargs = dict()
        for kwarg in args.criterion_kwargs:
            name, value = kwarg.split("=")
            kwargs[name] = value
        args.criterion_kwargs = kwargs
    else:
        args.criterion_kwargs = dict()

    return args
# End def parse_arguments


def init() -> None:

    global _context

    _log.info("Parsing arguments...")
    args = parse_arguments()

    _log.info("Loading experiment context...")
    # Fill the context dictionary
    _context = {

        # Experiment
        'scenario'          : args.scenario,
        'criterion'          : {
            'name'  : args.criterion_name,
            'kwargs': args.criterion_kwargs
        },
        'target_class'      : args.target_class,  # Class to predict
        'other_class'       : args.other_class,  # Class to predict

        # Iterations
        'it_max'            : 50,
        'nb_of_samples'     : args.samples,

        # Machine Learning
        'ml_algorithm'      : args.ml_algorithm ,
        'pp_strategy'       : args.pp_strategy,
        'cv_folds'          : args.cv_folds,

        # Rule Application
        "enable_mutation"   : args.enable_mutation,
        "mutation_rate"     : args.mutation_rate,
    }
    _log.info("Experiment context loaded. context is: {}".format(json.dumps(_context)))

    ## Initialize the statistics
    Stats.init(_context)
# End def init


# ===== ( Run function ) ===============================================================================================

def run() -> None:

    global _context

    # Create variables used by the algorithm
    precision = 0   # Algorithm precision
    recall = 0      # Algorithm recall
    dataset_path = join(setup.tmp_dir(), "dataset.csv")  # Create a file where the dataset will be stored
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
    experimenter.set_scenario(_context["scenario"])
    experimenter.set_criterion(_context['criterion']['name'], **_context['criterion']['kwargs'])

    while True:  # Infinite loop

        # Register timestamp at the beginning of the iteration
        start_of_it = time.time()

        # Write headers
        print(Style.BOLD, "*** Iteration {}".format(it + 1), Style.RESET)
        print(Style.BOLD, "*** recall: {:.2f}".format(recall), Style.RESET)
        print(Style.BOLD, "*** precision: {:.2f}".format(precision), Style.RESET)

        # 1. Generate mew data from the rule set

        if not rule_set.has_rules():
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
                        dst=join(setup.EXP_PATH, "datasets",
                                 "it_{}_raw.csv".format(it)))
            # Format the dataset
            ml_data.format_dataset(dataset_path,
                                   method="faf",
                                   target_error=_context['target_class'],
                                   csv_sep=';')
        else:
            # Fetch the data into a temporary dictionary
            tmp_dataset_path = join(setup.tmp_dir(), "temp_data.csv")
            exp_data.fetch(tmp_dataset_path)
            # Copy the raw version of the dataset to the exp folder
            shutil.copy(src=tmp_dataset_path,
                        dst=join(setup.EXP_PATH, "datasets",
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
            dst=join(setup.EXP_PATH, "datasets", "it_{}.csv".format(it))
        )

        # Convert the set to an arff file
        csv.to_arff(
            csv_path=dataset_path,
            arff_path=join(setup.tmp_dir(), "dataset.arff"),
            csv_sep=';',
            relation='dataset_iteration_{}'.format(it),
            exclude=['pkt_struct', 'fuzz_info', 'action']
        )

        # Save the arff dataset as well
        shutil.copy(
            src=join(setup.tmp_dir(), "dataset.arff"),
            dst=join(setup.EXP_PATH, "datasets", "it_{}.arff".format(it))
        )

        # 3. Perform machine learning algorithms
        start_of_ml = time.time()

        ml_results = ml_alg.learn(
            data_path=join(setup.tmp_dir(), "dataset.arff"),
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
        Stats.save(join(setup.EXP_PATH, 'stats.json'))

        # Canonicalize the rule set before the next iteration
        if rule_set.has_rules():
            rule_set.canonicalize()
        print(rule_set)

        # Increment the number of iterations
        it += 1
    # End of main loop
# End def run


# ===== ( Cleanup function ) ===============================================================================================

def cleanup(*args):
    """
    Clean up all file inside /var/run.
    """
    global _crashed

    if CONFIG.general.cleanup is True:
        _log.info("Cleaning up rdfl_exp...")
        # Ensure the cache, and data directories have the user's permissions
        _log.debug("Restoring ownership permissions to user {}...".format(setup.get_user()))
        uid = pwd.getpwnam(setup.get_user()).pw_uid
        gid = grp.getgrnam(setup.get_user()).gr_gid
        file.recursive_chown(setup.APP_DIRS.user_cache_dir, uid, gid)
        file.recursive_chown(setup.APP_DIRS.user_log_dir, uid, gid)
        file.recursive_chown(setup.APP_DIRS.user_data_dir, uid, gid)
        _log.debug("Permissions have been restored.")

        # Clean the temporary directory
        _log.debug("Cleaning up the temporary directory at \"{}\"...".format(setup.tmp_dir()))
        setup.tmp_dir(get_obj=True).cleanup()
        _log.debug("Temporary directory has been cleaned.")

        # Clean the pid file
        try:
            _log.debug("Cleaning up the PID file...")
            os.remove(join(setup.APP_DIRS.user_cache_dir, "rdfl_exp.pid"))
        except FileNotFoundError:
            pass  # if the file is not found then it's ok
        finally:
            _log.debug("PID file has been removed.")

        # Check if the JVM is started and stop it otherwise
        if jvm.started:
            _log.debug("Stopping the JVM...")
            jvm.stop()
            _log.debug("JVM has been stopped.")

    # Exit with code 0
    _log.info("Exiting rdfl_exp.")
    if _crashed is True:
        sys.exit(1)
    else:
        sys.exit(0)
# End def cleanup


# ===== ( Main Function ) ==============================================================================================

def main() -> None:

    global _crashed

    # Create cleanup signal
    for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM, signal.SIGQUIT):
        signal.signal(sig, cleanup)

    # Create configuration reload signal
    # signal.signal(signal.SIGHUP, None)

    # Run the setup configuration
    setup.init()

    try:
        # Configure java bridge logger
        jvm.logger.setLevel(logging.INFO)
        jvm.start(packages=True)  # Start the JVM

        # Install the required packages if necessary
        _log.info("Checking WEKA packages...")
        new_pkg_installed = False
        if not packages.is_installed("SMOTE"):
            _log.info("Installing weka package: \"SMOTE\" ...", end=' ')
            packages.install_package("SMOTE")
            new_pkg_installed = True
            _log.info("done")

        if new_pkg_installed is True:
            print("New WEKA packages have beend installed. Please restart rdfl_exp to complete installation.")
            jvm.stop()
            sys.exit(0)

        _log.debug("WEKA packages check has been done.")

        # Launch init function
        init()

        # Launch run function
        run()

    except KeyboardInterrupt:
        _log.info("rdfl_exp stopped by user.")

    except Exception as e:
        _log.exception("An uncaught exception happened while running rdfl_exp")
        print("An uncaught exception happened while running rdfl_exp")
        print(e)

        _crashed = True

    finally:
        _log.info("Closing rdfl_exp.")
        jvm.stop()  # Close the JVM
        cleanup()  # Clean up the program
# End def main
