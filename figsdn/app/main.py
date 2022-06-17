#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import traceback
from os.path import join
from typing import Iterable, Optional, Union

from scipy.stats import rankdata
from weka.core import jvm, packages

from figsdn.common import app_path
from figsdn.common.utils import csv_ops, utils, ExitCode
from figsdn.common.utils.database import Database as SqlDb
from figsdn.common.utils.terminal import Style
from figsdn import __app_name__, arguments, common
from figsdn.app import setup
from figsdn.arguments import Limit
from figsdn.app.drivers import FuzzerDriver, OnosDriver, RyuDriver
from figsdn.app.experiment import Analyzer, Experimenter, Method, Learner, Model, RuleSet
from figsdn.app.stats import Stats

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
    "method"                : str(),
    "budget"                : str(),

    # Iterations
    "nb_of_samples"         : int(),
    "it_limit"              : None,
    "time_limit"            : None,

    # Machine Learning
    "filter"                : str(),
    "algorithm"             : str(),
    "cv_folds"              : int(),

    # Rule Application
    "mutation_rate"         : float(),

    # Default fuzzer instructions
    'criteria'              : list(),
    'match_limit'           : int(),
    "default_actions"       : list(),
}


# ===== ( Run function ) ===============================================================================================

def run(
    mode='new',
    scenario : Optional[str] = None,
    criterion : Optional[str] = None,
    target_class : Optional[str] = None,
    other_class : Optional[str] = None,
    samples : Optional[int] = None,
    method : Optional[str] = None,
    budget : Optional[int] = None,
    ml_algorithm : Optional[str] = None,
    ml_filter : Optional[str] = None,
    ml_cv_folds : Optional[int] = None,
    mutation_rate : Optional[int] = None,
    criterion_kwargs : Optional[dict] = None,
    limit : Optional[Iterable] = None,
):

    global _context

    # Check if a valid mode has been selected
    if mode not in ('new', 'resume'):
        raise AttributeError("Run mode must be either \'run\' or \'resume\', not \'{}\'.".format(mode))

    if not setup.is_initialized():
        raise RuntimeError("'setup' module must be initialized before running the main function.")

    # Create variables used by the algorithm
    precision = 0  # Algorithm precision
    recall = 0  # Algorithm recall
    it = 0  # iteration index

    # Setup for new mode
    if mode == 'new':
        _log.info("Loading experiment context...")
        # Fill the context dictionary
        _context = {

            # Experiment
            'scenario'          : scenario,
            'criterion'         : {
                'name'          : criterion,
                'kwargs'        : criterion_kwargs
            },
            'method'            : method,          # Fuzzing method
            'budget'            : budget,          # Budget calculation method
            'target_class'      : target_class,    # Class to predict
            'other_class'       : other_class,     # Class to predict

            # Iterations
            'nb_of_samples'     : samples,
            'it_limit'          : int(limit[1]) if limit and limit[0] == Limit.ITERATION else None,
            'time_limit'        : int(limit[1]) if limit and limit[0] == Limit.TIME else None,

            # Machine Learning
            'algorithm'         : ml_algorithm ,
            'filter'            : ml_filter,
            'cv_folds'          : ml_cv_folds,

            # Rule Application
            "mutation_rate"     : mutation_rate,
        }
        _log.info("Experiment context loaded. context is: {}".format(json.dumps(_context)))

        ## Initialize the statistics
        Stats.init(_context)

        # Initialize the rule set
        rule_set = RuleSet()
        rule_set.target_class = _context['target_class']
        rule_set.other_class = _context['other_class']

    elif mode == 'resume':
        raise NotImplementedError("Resume function is not yet implemented")

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
    print(Style.BOLD, "*** Fuzzing Method: {}".format(_context['method']), Style.RESET)
    print(Style.BOLD, "*** Budget Calculation Method: {}".format(_context['budget']), Style.RESET)
    print(Style.BOLD, "*** Target class: {}".format(_context['target_class']), Style.RESET)
    print(Style.BOLD, "*** Machine Learning Algorithm: {}".format(_context['algorithm']), Style.RESET)
    print(Style.BOLD, "*** Machine Learning Filter: {}".format(_context['filter']), Style.RESET)
    print(Style.BOLD, "*** Mutation Rate: {}".format(_context['mutation_rate']), Style.RESET)
    if _context['time_limit'] is not None:
        print(Style.BOLD, "*** Time Limit: {}".format(str(datetime.timedelta(seconds=_context['time_limit']))), Style.RESET)
    if _context['it_limit'] is not None:
        print(Style.BOLD, "*** Iteration Limit: {}".format(_context['it_limit']), Style.RESET)

    # Set up the experimenter
    analyzer = Analyzer()

    # Set up the experimenter
    experimenter = Experimenter()
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
        if _context['method'] == arguments.Method.DEFAULT:
            if ml_model is None or not ml_model.has_rules:
                _log.info("No rules in set of rule. Generating random samples")
                experimenter.method = Method.RANDOM
                experimenter.ruleset = None
            else:
                experimenter.method = Method.RULE
                experimenter.ruleset = ml_model.ruleset
                analyzer.set_ruleset_for_iteration(ml_model.ruleset)

        elif _context['method'] == arguments.Method.DELTA:
            experimenter.method = Method.DELTA
            experimenter.ruleset = None

        elif _context['method'] == arguments.Method.BEADS:
            experimenter.method = Method.BEADS
            experimenter.ruleset = None

        # 1. Run the experiment
        experimenter.run()

        # 2. Create the datasets
        data = experimenter.analyzer.get_dataset()
        data.to_csv(join(app_path.exp_dir('data'), "it_{}_raw.csv".format(it)), index=False, encoding='utf-8')

        # Write the formatted data to the file
        data = experimenter.analyzer.get_dataset(error_class=_context['target_class'])
        data.to_csv(join(app_path.exp_dir('data'), "it_{}.csv".format(it)), index=False, encoding='utf-8')

        # Write the debug dataset to the file
        data = experimenter.analyzer.get_dataset(error_class=_context['target_class'], debug=True)
        data.to_csv(join(app_path.exp_dir('data'), "it_{}_debug.csv".format(it)), index=False, encoding='utf-8')

        # Convert the set to an arff file
        csv_ops.to_arff(
            csv_path=join(app_path.exp_dir('data'), "it_{}.csv".format(it)),
            arff_path=join(app_path.exp_dir('data'), "it_{}.arff".format(it)),
            csv_sep=',',
            relation='dataset_iteration_{}'.format(it)
        )

        # 3. Perform machine learning algorithms
        start_of_ml = time.time()
        try:
            learner.load_data(join(app_path.exp_dir('data'), "it_{}.arff".format(it)))
            ml_model = learner.learn()
        except Exception:
            _log.exception("An exception occurred while trying to create a models")
            _log.warning("Continuing with no model")
            ml_model = None
        finally:
            end_of_ml = time.time()

        if ml_model is not None:

            # Save the model
            model_path = join(app_path.exp_dir('models'), 'it_{}.model'.format(it))
            _log.debug('Saving model under {}'.format(model_path))
            ml_model.save(file_path=model_path)

            # Get recall and precision from the evaluator results
            precision = ml_model.info.precision[_context['target_class']]
            recall    = ml_model.info.recall[_context['target_class']]
            # Avoid cases where precision or recall are NaN values
            recall = 0.0 if math.isnan(recall) else recall
            precision = 0.0 if math.isnan(precision) else precision

            # budget calculation
            data_size   = learner.get_instances_count()
            calculate_budget(
                data_size=data_size['all'],
                samples=_context['nb_of_samples'],
                target=_context['target_class'],
                target_count=data_size[_context['target_class']],
                ruleset=ml_model.ruleset,
                method=_context['budget']
            )

        else:
            precision = 0.0
            recall = 0.0

        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics and classifier statistics and save them to a file
        Stats.add_iteration_statistics(
            learning_time=end_of_ml - start_of_ml,
            iteration_time=end_of_it - start_of_it,
            learner=learner,
            model=ml_model
        )
        Stats.save(join(app_path.exp_dir(), 'stats.json'), pretty=True)

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


def calculate_budget(data_size, samples, target, target_count, ruleset, method=arguments.Budget.CONFIDENCE):
    """"""
    # TODO: Move this calculation to the experimenter
    if method not in arguments.Budget.values():
        raise ValueError("Unknown method '{}'".format(method))
    _log.debug("Setting rule budget according to method \"{}\".".format(method))

    # Calculate the constants used in all methods
    class_ratio = target_count / data_size if target_count <= (data_size / 2) else (data_size - target_count)/data_size
    s_min = min(0.5 * (data_size + samples) - class_ratio * data_size, samples)
    s_maj = max(samples - s_min, 0)

    if method == arguments.Budget.CONFIDENCE_AND_RANK:
        rule_cnt = len(ruleset)
        rule_info = list()
        budgets = list()

        for i in range(rule_cnt):
            rule_info.append({
                "num"   : i,
                "cls"   : ruleset.rules[i].class_,
                "conf"  : ruleset.confidence(i, relative=True, relative_to_class=True),
                "sup"   : ruleset.support(i)
            })

        # Separate the two class in two different groups
        tgt_rules = [r for r in rule_info if r['cls'] == target]
        oth_rules = [r for r in rule_info if r['cls'] != target]

        # Perform the budget calculation on both the rules for the target class and the other classes
        for rules in (tgt_rules, oth_rules):
            # Rank the rules based on their support
            ranks = list(rankdata([r['sup'] for r in rules], method='max'))
            rank_sum = sum(ranks)

            # Calculate the budget according to the rank and the relative confidence
            bgts = [(ranks[i] / rank_sum) * rules[i]['conf'] for i in range(len(rules))]
            # Normalize the budget so their sum is equal to 1
            bgts = [b / sum(bgts) for b in bgts]
            # Multiply the budgets by either
            for i in range(len(rules)):
                if rules[i]['cls'] == target:
                    if target_count <= (data_size / 2):
                        b = bgts[i] * s_min
                    else:
                        b = bgts[i] * s_maj
                else:
                    if target_count <= (data_size / 2):
                        b = bgts[i] * s_maj
                    else:
                        b = bgts[i] * s_min
                # Add the budgets to the list
                budgets.append((rules[i]['num'], b))

        # Assign the budgets to the corresponding rules
        for i, budget in budgets:
            ruleset[i].set_budget(budget)
            _log.debug("Set a budget of {} for rule {}".format(ruleset[i].budget, i))

    elif method == arguments.Budget.CONFIDENCE:
        for i in range(len(ruleset)):
            confidence = ruleset.confidence(i, relative=True, relative_to_class=True)
            if ruleset[i].get_class() == target:
                if target_count <= (data_size / 2):
                    ruleset[i].set_budget(confidence * s_min)
                else:
                    ruleset[i].set_budget(confidence * s_maj)
            else:  # other_class
                if target_count <= (data_size / 2):
                    ruleset[i].set_budget(confidence * s_maj)
                else:
                    ruleset[i].set_budget(confidence * s_min)

            _log.debug("Set a budget of {} for rule {}".format(ruleset[i].budget, i))
# End def calculate_budget


# ===== ( Cleanup function ) ===========================================================================================

def cleanup(*args):
    """
    Clean up all file inside /var/run.
    """
    global _crashed

    if setup.config().general.cleanup is True:
        _log.info("Cleaning up figsdn...")

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
        utils.recursive_chown(app_path.data_dir(), uid, gid)
        utils.recursive_chown(app_path.log_dir(), uid, gid)
        utils.recursive_chown(app_path.config_dir(), uid, gid)
        _log.debug("Permissions have been restored.")

        # Clean the temporary directory
        _log.debug("Cleaning up the temporary directory at \"{}\"...".format(app_path.tmp_dir()))
        app_path.tmp_dir(get_obj=True).cleanup()
        _log.debug("Temporary directory has been cleaned.")

        # Clean the pid file
        try:
            _log.debug("Removing the PID file...")
            os.remove(setup.pid_path())
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
    _log.info("Exiting figsdn.")
    if _crashed is True:
        sys.exit(1)
    else:
        sys.exit(int(ExitCode.EX_OK))
# End def cleanup


# ===== ( Main Function ) ==============================================================================================

# TODO: Check for sudo permissions otherwise ask for password
def main(
        scenario,
        criterion,
        target_class,
        other_class,
        samples,
        method,
        budget,
        ml_algorithm,
        ml_filter,
        ml_cv_folds,
        mutation_rate,
        criterion_kwargs : Optional[dict] = None,
        limit : Optional[Iterable] = None,
        reference : Optional[Union[str, int, float]] = None
) -> None:

    global _crashed

    # Create cleanup signal
    for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM, signal.SIGQUIT):
        signal.signal(sig, cleanup)

    # Create configuration reload signal
    # signal.signal(signal.SIGHUP, None)

    # initialize the setup module
    setup.init(reference)

    try:

        # Configure java-bridge
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
            print("New WEKA packages have been installed. Please restart figsdn to complete installation.")
            jvm.stop()
            sys.exit(0)

        _log.debug("WEKA packages check has been done.")

        # Launch run function
        run(
            mode='new',
            scenario=scenario,
            criterion=criterion,
            target_class=target_class,
            other_class=other_class,
            samples=samples,
            method=method,
            budget=budget,
            ml_algorithm=ml_algorithm,
            ml_filter=ml_filter,
            ml_cv_folds=ml_cv_folds,
            mutation_rate=mutation_rate,
            criterion_kwargs=criterion_kwargs,
            limit=limit
        )

    except KeyboardInterrupt:
        _log.info("{} stopped by user.".format(__app_name__))

    except Exception as e:
        _log.exception("An uncaught exception happened while running {}".format(__app_name__))
        print("An uncaught exception happened while running {}: {}".format(__app_name__, e))
        print("Check the logs at \"{}\" for more information.".format(os.path.join(app_path.log_dir(), setup.EXP_REF + ".log")))
        _crashed = True

    finally:
        _log.info("Closing {}.".format(__app_name__))
        jvm.stop()  # Close the JVM
        cleanup()  # Clean up the program
# End def main
