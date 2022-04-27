#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import datetime
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
from typing import Optional

from weka.core import jvm, packages

from rdfl_exp import setup
from rdfl_exp.drivers import FuzzerDriver, OnosDriver, RyuDriver
from rdfl_exp.experiment import Analyzer, Experimenter, FuzzMode, Learner, Model, RuleSet
from rdfl_exp.resources import scenarios
from rdfl_exp.stats import Stats
from rdfl_exp.utils import csv_ops, time_parse, utils
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
    "fuzz_mode"             : str(),

    # Iterations
    "nb_of_samples"         : int(),
    "it_limit"              : None,
    "time_limit"            : None,

    # Machine Learning
    "filter"                : str(),
    "algorithm"             : str(),
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

    parser.add_argument(
        '--no-clean',
        action='store_false',
        help="Do not perform cleaning actions on exit"
    )

    # ===== ( Experiment Positional Args ) =============================================================================

    # Positional argument to choose the target
    error_types = (
        'unknown_reason',
        'known_reason',
        'parsing_error',
        'non_parsing_error',
        'OFPBAC_BAD_OUT_PORT'
    )
    parser.add_argument(
        'target_class',
        metavar='ERROR_TYPE',
        type=str,
        choices=error_types,
        help="Choose the error type to detect. "
             "Allowed values are: {}".format(', '.join("\'{}\'".format(e) for e in error_types))
    )

    # Positional argument to choose the machine learning algorithm
    with resources.path(scenarios, '') as p:
        available_scenarios = list(sorted(f for f in os.listdir(p) if f not in ['__pycache__', '__init__.py']))
    parser.add_argument(
        'scenario',
        metavar='SCENARIO',
        type=str,
        choices=available_scenarios,
        help="Name of the scenario to be run. Allowed scenarios are: "
             "{}".format(', '.join("\'{}\'".format(scn) for scn in available_scenarios))
    )

    # Positional argument to choose the criterion
    # Break criterion positional argument in two names to circumvent a bug where a positional argument can't have
    # several kwargs defined (python issue 14074: https://bugs.python.org/issue14074)
    parser.add_argument(
        'criterion_name',
        metavar='CRITERION',
        type=str,
        help="Name of the criterion to be run"
    )

    parser.add_argument(
        'criterion_kwargs',
        metavar='kwargs',
        nargs='*',
        type=str,
        help="kwargs for the criterion (optional)"
    )

    # ===== ( Experiment args ) ========================================================================================

    # Argument to choose the reference name of the experiment
    parser.add_argument(
        '-R',
        '--reference',
        type=str,
        default=None,
        dest='reference',
        help="Name of the experiment"
    )

    # Argument to choose the number of sample to generate
    parser.add_argument(
        '-s',
        '--samples',
        type=int,
        default=300,
        dest='samples',
        help="Override the number of samples. (default: %(default)s)"
    )

    # Argument to choose the number of sample to generate
    parser.add_argument(
        '--it-limit',
        type=int,
        default=None,
        dest='it_limit',
        help="Stops the program after a given number of iterations. The current iteration will be finished however."
    )

    # Argument to choose the number of sample to generate
    parser.add_argument(
        '--time-limit',
        type=str,
        default=None,
        dest='time_limit',
        help="Stops the program after a given amount of time has elapsed. "
             "The current iteration will be finished however."
    )

    # ===== ( Machine Learning args ) ==================================================================================

    # Argument to choose the machine learning algorithm
    parser.add_argument(
        '-A,',
        '--algorithm',
        type=str,
        default='RIPPER',
        dest='algorithm',
        help="Select which machine algorithm to use. (default: \"%(default)s\")"
    )

    # Argument to choose the preprocessing strategy
    parser.add_argument(
        '-F',
        '--filter',
        type=str,
        default=None,
        dest='filter',
        help="Select which preprocessing strategy to use. (default: \"%(default)s\")"
    )

    # Argument to choose the number of cross validation folds
    parser.add_argument(
        '-c',
        '--cross-validation-folds',
        type=int,
        default=10,
        dest='cv_folds',
        help="Define the number of folds to use during cross-validation. (default: %(default)s)"
    )

    # ===== ( Fuzzing args ) ===========================================================================================

    # Argument to choose the experiment mode
    mode_choices = (
        'standard',
        'DELTA',
        'BEADS'
    )
    parser.add_argument(
        '--fuzz-mode',
        type=str,
        choices=mode_choices,
        default='fuzz_mode',
        dest='fuzz_mode',
        help="Select the mode of fuzzing. "
             "Allowed modes are: {}".format(', '.join("\'{}\'".format(mc) for mc in mode_choices))
    )

    # Argument to choose disable the mutation of additional fields
    parser.add_argument(
        '--disable-mutation',
        action='store_false',
        dest='enable_mutation',
        help="Disable the mutation of additional fields upon rule application."
    )

    # Argument to choose the mutation rate of additional fields
    parser.add_argument(
        '--mutation-rate',
        type=float,
        default=1.0,
        dest='mutation_rate',
        help="Sets the mutation rate of additional fields upon rule application. (default: %(default)s)"
    )

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

    # Format the date of time_limit
    if args.time_limit:
        args.time_limit = time_parse(args.time_limit)

    return args
# End def parse_arguments


def init() -> None:

    global _context

    _log.info("Parsing arguments...")
    args = parse_arguments()

    # initialize the setup module
    setup.init(args)

    _log.info("Loading experiment context...")
    # Fill the context dictionary
    _context = {

        # Experiment
        'scenario'          : args.scenario,
        'criterion'         : {
            'name'          : args.criterion_name,
            'kwargs'        : args.criterion_kwargs
        },
        'fuzz_mode'         : args.fuzz_mode,       # Experimentation mode
        'target_class'      : args.target_class,    # Class to predict
        'other_class'       : args.other_class,     # Class to predict

        # Iterations
        'nb_of_samples'     : args.samples,
        'it_limit'          : args.it_limit,
        'time_limit'        : args.time_limit,

        # Machine Learning
        'algorithm'         : args.algorithm ,
        'filter'            : args.filter,
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
    precision = 0  # Algorithm precision
    recall    = 0  # Algorithm recall
    it        = 0  # iteration index

    # Initialize the rule set
    rule_set              = RuleSet()
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
    print(Style.BOLD, "*** Fuzzing Mode: {}".format(_context['fuzz_mode']), Style.RESET)
    print(Style.BOLD, "*** Target class: {}".format(_context['target_class']), Style.RESET)
    print(Style.BOLD, "*** Machine Learning Algorithm: {}".format(_context['algorithm']), Style.RESET)
    print(Style.BOLD, "*** Machine Learning Filter: {}".format(_context['filter']), Style.RESET)
    print(Style.BOLD, "*** Mutation: {}".format(_context['enable_mutation']), Style.RESET)
    if _context['enable_mutation'] is True:
        print(Style.BOLD, "*** Mutation Rate: {}".format(_context['mutation_rate']), Style.RESET)
    if _context['time_limit'] is not None:
        print(Style.BOLD, "*** Time Limit: {}".format(str(datetime.timedelta(seconds=_context['time_limit']))), Style.RESET)
    if _context['it_limit'] is not None:
        print(Style.BOLD, "*** Iteration Limit: {}".format(_context['it_limit']), Style.RESET)

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
    learner.target_class    = _context['target_class']
    learner.other_class     = _context['other_class']
    learner.algorithm       = _context['algorithm']
    learner.filter          = _context['filter']
    learner.cv_folds        = _context['cv_folds']

    # Setup the model to be used
    ml_model : Optional[Model] = None

    # Starts the main loop
    start_timestamp = time.time()
    keep_running = True

    while keep_running:

        # Register timestamp at the beginning of the iteration and set a new iteration for the analyzer
        start_of_it = time.time()
        analyzer.new_iteration()

        # Write headers
        print(Style.BOLD, "*** Iteration {}".format(it + 1), Style.RESET)
        print(Style.BOLD, "*** Recall: {:.2f}".format(recall), Style.RESET)
        print(Style.BOLD, "*** Precision: {:.2f}".format(precision), Style.RESET)

        # 0. Configure the experiment depending on the ML model and Fuzz Mode
        if _context['fuzz_mode'] == 'standard':
            if ml_model is None or not ml_model.has_rules:
                _log.info("No rules in set of rule. Generating random samples")
                experimenter.fuzz_mode = FuzzMode.RANDOM
                experimenter.ruleset = None
            else:
                experimenter.fuzz_mode = FuzzMode.RULE
                experimenter.ruleset = ml_model.ruleset
                analyzer.set_ruleset_for_iteration(ml_model.ruleset)

        elif _context['fuzz_mode'] == 'DELTA':
            experimenter.fuzz_mode = FuzzMode.DELTA
            experimenter.ruleset = None

        elif _context['fuzz_mode'] == 'BEADS':
            experimenter.fuzz_mode = FuzzMode.BEADS
            experimenter.ruleset = None

        # 1. Run the experiment
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
            ml_model = learner.learn()
        except Exception:
            _log.exception("An exception occurred while trying to create a models")
            _log.warning("Continuing with no model")
            ml_model = None
        finally:
            end_of_ml = time.time()

        if ml_model is not None:

            # Save the model
            model_path = join(setup.exp_dir('models'), 'it_{}.model'.format(it))
            _log.debug('Saving model under {}'.format(model_path))
            ml_model.save(file_path=model_path)

            # Get recall and precision from the evaluator results
            precision = ml_model.info.precision[_context['target_class']]
            recall    = ml_model.info.recall[_context['target_class']]
            # Avoid cases where precision or recall are NaN values
            recall = 0.0 if math.isnan(recall) else recall
            precision = 0.0 if math.isnan(precision) else precision

            # Budget calculation
            data_size   = learner.get_instances_count()
            all_cnt     = data_size['all']
            target_cnt  = data_size[_context['target_class']]
            class_ratio = target_cnt / all_cnt

            s_target    = min(0.5 * (all_cnt + _context['nb_of_samples']) - class_ratio * all_cnt, _context['nb_of_samples'])
            s_other     = max(_context['nb_of_samples'] - s_target, 0)

            for i in range(len(ml_model.ruleset)):
                confidence = ml_model.ruleset.confidence(i, relative=True, relative_to_class=True)
                if ml_model.ruleset[i].get_class() == _context['target_class']:
                    ml_model.ruleset[i].set_budget(confidence * s_target / _context['nb_of_samples'])
                else:  # other_class
                    ml_model.ruleset[i].set_budget(confidence * s_other / _context['nb_of_samples'])

        else:
            precision = 0.0
            recall = 0.0

        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics and classifier statistics statistics and save the statistics
        Stats.add_iteration_statistics(
            learning_time=end_of_ml - start_of_ml,
            iteration_time=end_of_it - start_of_it,
            learner=learner,
            model=ml_model
        )
        Stats.save(join(setup.exp_dir(), 'stats.json'), pretty=True)

        # Increment the number of iterations
        it += 1

        # Check if the stopping conditions are met
        if _context['it_limit'] is not None:
            if it >= _context['it_limit']:
                keep_running = False
        if _context['time_limit'] is not None:
            if time.time() - start_timestamp >= _context['time_limit']:
                keep_running = False
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

        # Initialize the tool
        init()

        # Configure javabridge
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
