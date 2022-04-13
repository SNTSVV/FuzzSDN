#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import grp
import json
import logging
import math
import os
import pwd
import signal
import sys
import time
from importlib import resources
from os.path import join

from weka.core import jvm, packages

from rdfl_exp import setup
from rdfl_exp.drivers import FuzzerDriver, OnosDriver, RyuDriver
from rdfl_exp.experiment import Analyzer, Experimenter, FuzzMode, Learner, RuleSet
from rdfl_exp.resources import scenarios
from rdfl_exp.stats import Stats
from rdfl_exp.utils import csv_ops, utils
from rdfl_exp.utils.database import Database as SqlDb
from rdfl_exp.utils.exit_codes import ExitCode
from rdfl_exp.utils.terminal import Style

# ===== ( locals ) =====================================================================================================

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
    error_types = ('unknown_reason', 'known_reason', 'parsing_error', 'non_parsing_error', 'OFPBAC_BAD_OUT_PORT')
    parser.add_argument('target_class',
                        metavar='ERROR_TYPE',
                        type=str,
                        choices=error_types,
                        help="Choose the error type to detect. Allowed values are: {}".format(', '.join("\'{}\'".format(e) for e in error_types)))

    # Positional argument to choose the machine learning algorithm
    with resources.path(scenarios, '') as p:
        available_scenarios = list(sorted(f for f in os.listdir(p) if f not in ['__pycache__', '__init__.py']))
    parser.add_argument('scenario',
                        metavar='SCENARIO',
                        type=str,
                        choices=available_scenarios,
                        help="Name of the scenario to be run. Allowed scenarios are: {}".format(', '.join("\'{}\'".format(scn) for scn in available_scenarios)))

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

    # Argument to choose the experiment mode
    mode_choices = ('standard', 'no_learning')
    parser.add_argument('-m', '--mode',
                        type=str,
                        choices=mode_choices,
                        default='standard',
                        dest='mode',
                        help="Select the mode of operation. Allowed modes are: {}".format(', '.join("\'{}\'".format(mc) for mc in mode_choices)))

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
                        default=None,
                        dest='pp_strategy',
                        help="Select which preprocessing strategy to use. (default: \"%(default)s\")")

    # Argument to choose the number of cross validation folds
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

    elif args.target_class == "OFPBAC_BAD_OUT_PORT":
        args.other_class = "OTHER_REASON"

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
        'mode'              : args.mode,            # Experimentation mode
        'target_class'      : args.target_class,    # Class to predict
        'other_class'       : args.other_class,     # Class to predict

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
    it = 0  # iteration index

    # Initialize the rule set
    rule_set = RuleSet()
    rule_set.target_class = _context['target_class']
    rule_set.other_class  = _context['other_class']

    ## Get the criterion kwargs string
    if len(_context['criterion']['kwargs']) > 0:
        criterion_kwargs_str = " (kwargs: {})"
        criterion_kwargs_str.format(", ".join("{}=\'{}\'".format(key, _context['criterion']['kwargs'][key]) for key in
                                              _context['criterion']['kwargs'].keys()))
    else:
        criterion_kwargs_str = ''
    # Display header:
    print(Style.BOLD, "*** Scenario: {}".format(_context['scenario']), Style.RESET)
    print(Style.BOLD, "*** Criterion: {}{}".format(_context['criterion']['name'], criterion_kwargs_str), Style.RESET)
    print(Style.BOLD, "*** Mode: {}".format(_context['mode']), Style.RESET)
    print(Style.BOLD, "*** Target class: {}".format(_context['target_class']), Style.RESET)
    print(Style.BOLD, "*** Machine learning algorithm: {}".format(_context['ml_algorithm']), Style.RESET)
    print(Style.BOLD, "*** Preprocessing strategy: {}".format(_context['pp_strategy']), Style.RESET)
    print(Style.BOLD, "*** Mutation: {}".format(_context['enable_mutation']), Style.RESET)
    if _context['enable_mutation'] is True:
        print(Style.BOLD, "*** Mutation Rate: {}".format(_context['mutation_rate']), Style.RESET)

    # Set up the experimenter
    analyzer = Analyzer()

    # Set up the experimenter
    experimenter = Experimenter()
    experimenter.enable_mutation        = _context['enable_mutation']
    experimenter.mutation_rate          = _context['mutation_rate']
    experimenter.scenario               = _context['scenario']
    experimenter.criterion              = _context['criterion']['name'], _context['criterion']['kwargs']
    experimenter.samples_per_iteration  = _context['nb_of_samples']
    experimenter.analyzer               = analyzer

    # Setup the Learner
    learner = Learner()
    learner.set_classes(target_class=_context['target_class'], other_class=_context['other_class'])
    learner.set_learning_algorithm(_context['ml_algorithm'])
    learner.set_preprocessing_strategy(_context['pp_strategy'])
    learner.set_cross_validation_folds(_context['cv_folds'])

    while True:  # Infinite loop

        # Register timestamp at the beginning of the iteration and set a new iteration for the analyzer
        start_of_it = time.time()
        analyzer.new_iteration()

        # Write headers
        print(Style.BOLD, "*** Iteration {}".format(it + 1), Style.RESET)
        print(Style.BOLD, "*** Recall: {:.2f}".format(recall), Style.RESET)
        print(Style.BOLD, "*** Precision: {:.2f}".format(precision), Style.RESET)

        # 1. Generate new data from the rule set

        if not learner.has_rules() or _context['mode'] == 'no_learning':
            _log.info("No rules in set of rule. Generating random samples")
            experimenter.fuzz_mode  = FuzzMode.RANDOM
            experimenter.ruleset    = None
        else:
            experimenter.fuzz_mode  = FuzzMode.RULE
            experimenter.ruleset    = learner.get_rules()
            analyzer.set_ruleset_for_iteration(learner.get_rules())

        experimenter.run()

        # 2. Create the datasets
        data = experimenter.analyzer.get_dataset()
        data.to_csv(join(setup.exp_dir('data'), "it_{}_raw.csv".format(it)), index=False, encoding='utf-8')

        # Write the formatted data to the file
        data = experimenter.analyzer.get_dataset(error_class=_context['target_class'])
        data.to_csv(join(setup.exp_dir('data'), "it_{}.csv".format(it)), index=False, encoding='utf-8')

        # Write the debug dataset to the file
        data = experimenter.analyzer.get_dataset(error_class=_context['target_class'], debug=True)
        data.to_csv(join(setup.exp_dir('data'), "it_{}_debug.csv".format(it)), index=False, encoding='utf-8')

        # Convert the set to an arff file
        csv_ops.to_arff(
            csv_path=join(setup.exp_dir('data'), "it_{}.csv".format(it)),
            arff_path=join(setup.exp_dir('data'), "it_{}.arff".format(it)),
            csv_sep=',',
            relation='dataset_iteration_{}'.format(it)
        )

        # 3. Perform machine learning algorithms
        start_of_ml = time.time()
        try:

            learner.load_data(join(setup.exp_dir('data'), "it_{}.arff".format(it)))
            learner.learn()

            # Get recall and precision from the evaluator results
            ml_results = learner.get_results()
            recall    = ml_results['cross-validation'][_context['target_class']]['recall']
            precision = ml_results['cross-validation'][_context['target_class']]['precision']

            # Avoid cases where precision or recall are NaN values
            recall = 0.0 if math.isnan(recall) else recall
            precision = 0.0 if math.isnan(precision) else precision

            # Budget calculation
            target_cnt, other_cnt = learner.get_size_of_classes()
            class_ratio = target_cnt / (target_cnt + other_cnt)
            s_target = min(0.5 * (learner.get_dataset_size() + _context['nb_of_samples']) - class_ratio * learner.get_dataset_size(),
                           _context['nb_of_samples'])
            s_other = max(_context['nb_of_samples'] - s_target, 0)

            for i in range(len(learner.ruleset)):
                if learner.ruleset[i].get_class() == _context['target_class']:
                    learner.ruleset[i].set_budget(learner.ruleset.confidence(i, relative=True, relative_to_class=True) * s_target / _context['nb_of_samples'])
                else:  # other_class
                    learner.ruleset[i].set_budget(learner.ruleset.confidence(i, relative=True, relative_to_class=True) * s_other / _context['nb_of_samples'])

        except Exception:
            _log.exception("An exception occured while trying to create a models")
            _log.warning("Continuing with previous model")

        # End of iteration total time
        end_of_ml = time.time()
        end_of_it = time.time()

        # Update the timing statistics and classifier statistics statistics and save the statistics
        Stats.add_iteration_statistics(
            learning_time=end_of_ml - start_of_ml,
            iteration_time=end_of_it - start_of_it,
            experimenter=experimenter,
            analyzer=analyzer,
            learner=learner
        )
        Stats.save(join(setup.exp_dir(), 'stats.json'), pretty=True)

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

    if setup.config().general.cleanup is True:
        _log.info("Cleaning up rdfl_exp...")

        # Stop all the the drivers
        _log.debug("Stopping all the drivers...")
        try:
            FuzzerDriver.stop()
            OnosDriver.stop()
            RyuDriver.stop()

        except Exception:
            _log.exception("An exception occurred while stopping the SDN controllers...")
        finally:
            _log.debug("PID file has been removed.")

        # Ensure the cache, and data directories have the user's permissions
        _log.debug("Restoring ownership permissions to user {}...".format(setup.get_user()))
        uid = pwd.getpwnam(setup.get_user()).pw_uid
        gid = grp.getgrnam(setup.get_user()).gr_gid
        utils.recursive_chown(setup.app_dir().user_cache_dir, uid, gid)
        utils.recursive_chown(setup.app_dir().user_log_dir, uid, gid)
        utils.recursive_chown(setup.app_dir().user_data_dir, uid, gid)
        _log.debug("Permissions have been restored.")

        # Clean the temporary directory
        _log.debug("Cleaning up the temporary directory at \"{}\"...".format(setup.tmp_dir()))
        setup.tmp_dir(get_obj=True).cleanup()
        _log.debug("Temporary directory has been cleaned.")

        # Clean the pid file
        try:
            _log.debug("Cleaning up the PID file...")
            os.remove(join(setup.APP_DIR.user_cache_dir, "rdfl_exp.pid"))
        except FileNotFoundError:
            pass  # if the file is not found then it's ok
        finally:
            _log.debug("PID file has been removed.")

        # Check if the JVM is started and stop it otherwise
        if jvm.started:
            _log.debug("Stopping the JVM...")
            jvm.stop()
            _log.debug("JVM has been stopped.")

        if SqlDb.is_connected():
            SqlDb.disconnect()

    # Exit with code 0
    _log.info("Exiting rdfl_exp.")
    if _crashed is True:
        sys.exit(1)
    else:
        sys.exit(int(ExitCode.EX_OK))
# End def cleanup


# ===== ( Main Function ) ==============================================================================================

# TODO: Check for sudo permissions otherwise ask for password
def main() -> None:

    global _crashed

    # Create cleanup signal
    for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM, signal.SIGQUIT):
        signal.signal(sig, cleanup)

    # Create configuration reload signal
    # signal.signal(signal.SIGHUP, None)

    try:

        # Run the setup configuration
        setup.init()

        # Launch init function
        init()

        # Configure java-bridge logger
        jvm.logger.setLevel(logging.INFO)
        jvm.start(packages=True)  # Start the JVM

        # Install the required packages if necessary
        _log.info("Checking WEKA packages...")
        new_pkg_installed = False
        if not packages.is_installed("SMOTE"):
            _log.info("Installing weka package: \"SMOTE\" ...")
            packages.install_package("SMOTE")
            new_pkg_installed = True
            _log.info("done")

        if new_pkg_installed is True:
            print("New WEKA packages have been installed. Please restart rdfl_exp to complete installation.")
            jvm.stop()
            sys.exit(0)

        _log.debug("WEKA packages check has been done.")

        # Launch run function
        run()

    except KeyboardInterrupt:
        _log.info("rdfl_exp stopped by user.")

    except Exception as e:
        _log.exception("An uncaught exception happened while running rdfl_exp")
        print("An uncaught exception happened while running rdfl_exp: {}".format(e))
        print("Check the logs at \"{}\" for more information.".format(os.path.join(setup.app_dir().user_log_dir,
                                                                                   setup.config().logging.filename)))
        _crashed = True

    finally:
        _log.info("Closing rdfl_exp.")
        jvm.stop()  # Close the JVM
        cleanup()  # Clean up the program
# End def main
