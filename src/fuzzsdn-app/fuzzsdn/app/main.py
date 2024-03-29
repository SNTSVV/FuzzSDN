#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import pwd
import random
import signal
import sys
from os.path import join
from typing import Iterable, Optional, Union

import grp
import math
from scipy.stats import rankdata
from timeit import default_timer as timer
from weka.core import jvm, packages

from fuzzsdn import __app_name__, arguments
from fuzzsdn.app import setup
from fuzzsdn.app.drivers import FuzzerDriver, OnosDriver, RyuDriver
from fuzzsdn.app.experiment import Analyzer, Experimenter, Learner, Method, Model, RuleSet
from fuzzsdn.app.stats import Stats
from fuzzsdn.arguments import Limit
from fuzzsdn.common import app_path
from fuzzsdn.common.utils import ExitCode, csv_ops, utils
from fuzzsdn.common.utils.database import Database as SqlDb
from fuzzsdn.common.utils.terminal import Style

# ===== ( locals ) =====================================================================================================

_log = logging.getLogger(__name__)
_is_init = False
_crashed = False

_context = {
    # Classifying
    "scenario"              : str(),
    'scenario_options'      : dict(),
    "criterion"             : {
        "name"      : str(),
        "kwargs"    : dict()
    },
    "fut"                   : str(),
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
    failure_under_test : Optional[str] = None,
    samples : Optional[int] = None,
    method : Optional[str] = None,
    budget : Optional[int] = None,
    ml_algorithm : Optional[str] = None,
    ml_filter : Optional[str] = None,
    ml_cv_folds : Optional[int] = None,
    mutation_rate : Optional[int] = None,
    criterion_kwargs : Optional[dict] = None,
    scenario_options : Optional[dict] = None,
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
            'scenario_options'  : scenario_options,
            'criterion'         : {
                'name'          : criterion,
                'kwargs'        : criterion_kwargs
            },
            'method'            : method,               # Fuzzing method
            'budget'            : budget,               # Budget calculation method
            'fut'               : failure_under_test,   # Failure tested

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
        rule_set.target_class   = 'FAIL'  # Always '''FAIL'''
        rule_set.other_class    = 'PASS'  # and '''PASS'''

    elif mode == 'resume':
        raise NotImplementedError("Resume function is not yet implemented")

    ## Get the scenario kwargs string
    if len(_context['scenario_options']) > 0:
        scenario_options_str = " (options: {})".format(
            ", ".join("{}=\'{}\'".format(key, _context['scenario_options'][key])
                      for key in _context['scenario_options'].keys())
        )
    else:
        scenario_options_str = ''

    ## Get the criterion kwargs string
    if len(_context['criterion']['kwargs']) > 0:
        criterion_kwargs_str = " (kwargs: {})".format(
            ", ".join("{}=\'{}\'".format(key, _context['criterion']['kwargs'][key])
                      for key in _context['criterion']['kwargs'].keys())
        )

    else:
        criterion_kwargs_str = ''

    # Display header:
    print(Style.BOLD, "*** Scenario: {}{}".format(_context['scenario'], scenario_options_str), Style.RESET)
    print(Style.BOLD, "*** Criterion: {}{}".format(_context['criterion']['name'], criterion_kwargs_str), Style.RESET)
    print(Style.BOLD, "*** Fuzzing Method: {}".format(_context['method']), Style.RESET)
    print(Style.BOLD, "*** Budget Calculation Method: {}".format(_context['budget']), Style.RESET)
    print(Style.BOLD, "*** Failure under test: {}".format(_context['fut']), Style.RESET)
    print(Style.BOLD, "*** Machine Learning Algorithm: {}".format(_context['algorithm']), Style.RESET)
    print(Style.BOLD, "*** Machine Learning Filter: {}".format(_context['filter']), Style.RESET)
    print(Style.BOLD, "*** Mutation Rate: {}".format(_context['mutation_rate']), Style.RESET)
    if _context['time_limit'] is not None:
        print(Style.BOLD, "*** Time Limit: {}".format(str(datetime.timedelta(seconds=_context['time_limit']))), Style.RESET)
    if _context['it_limit'] is not None:
        print(Style.BOLD, "*** Iteration Limit: {}".format(_context['it_limit']), Style.RESET)

    # Set up the Analyzer
    analyzer = Analyzer()
    analyzer.save_logs = False

    # Set up the experimenter
    experimenter = Experimenter()
    experimenter.mutation_rate          = _context['mutation_rate']
    experimenter.scenario               = _context['scenario'], _context['scenario_options']
    experimenter.criterion              = _context['criterion']['name'], _context['criterion']['kwargs']
    experimenter.samples_per_iteration  = _context['nb_of_samples']
    experimenter.analyzer               = analyzer

    # Setup the Learner
    learner = Learner()
    learner.target_class    = 'FAIL'  # Always '''FAIL'''
    learner.other_class     = 'PASS'  # and '''PASS'''
    learner.algorithm       = _context['algorithm']
    learner.filter          = _context['filter']
    learner.cv_folds        = _context['cv_folds']

    # Setup the model to be used
    ml_model : Optional[Model] = None

    # Starts the main loop
    start_timestamp = timer()
    keep_running = True

    while keep_running:

        # Register timestamp at the beginning of the iteration and set a new iteration for the analyzer
        start_of_it = timer()
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
        data = experimenter.analyzer.get_dataset(failure_under_test=_context['fut'])
        data.to_csv(join(app_path.exp_dir('data'), "it_{}.csv".format(it)), index=False, encoding='utf-8')

        # Write the debug dataset to the file
        data = experimenter.analyzer.get_dataset(failure_under_test=_context['fut'], debug=True)
        data.to_csv(join(app_path.exp_dir('data'), "it_{}_debug.csv".format(it)), index=False, encoding='utf-8')

        # Convert the set to an arff file
        csv_ops.to_arff(
            csv_path=join(app_path.exp_dir('data'), "it_{}.csv".format(it)),
            arff_path=join(app_path.exp_dir('data'), "it_{}.arff".format(it)),
            csv_sep=',',
            relation='dataset_iteration_{}'.format(it)
        )

        # 3. Perform machine learning algorithms
        start_of_ml = timer()
        try:
            learner.load_data(join(app_path.exp_dir('data'), "it_{}.arff".format(it)))
            ml_model = learner.learn()
        except Exception:
            _log.exception("An exception occurred while trying to create a models")
            _log.warning("Continuing with no model")
            ml_model = None
        finally:
            end_of_ml = timer()

        st_of_plan    = timer()  # Start planning measurement
        if ml_model is not None:

            # Save the model
            model_path = join(app_path.exp_dir('models'), 'it_{}.model'.format(it))
            _log.debug('Saving model under {}'.format(model_path))
            ml_model.save(file_path=model_path)

            # Get recall and precision from the evaluator results
            precision = ml_model.info.precision['FAIL']
            recall    = ml_model.info.recall['FAIL']
            # Avoid cases where precision or recall are NaN values
            recall = 0.0 if math.isnan(recall) else recall
            precision = 0.0 if math.isnan(precision) else precision

            # budget calculation
            st_of_plan = timer()
            data_size   = learner.get_instances_count()
            calculate_budget(
                data_size=data_size['all'],
                samples=_context['nb_of_samples'],
                failure_count=data_size['FAIL'],
                ruleset=ml_model.ruleset,
                method=_context['budget']
            )
            time_plan_end = timer()

        else:
            precision = 0.0
            recall = 0.0
        end_of_plan = timer()  # End of planning measurement

        # End of iteration total time
        end_of_it = timer()

        # Update the timing statistics and classifier statistics and save them to a file
        Stats.add_iteration_statistics(
            testing_time=sum(experimenter.run_time),  # Aggregate the testing time
            fuzzing_time=sum(analyzer.fuzz_time),
            learning_time=end_of_ml - start_of_ml,
            planning_time=(end_of_plan - st_of_plan),
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
            if timer() - start_timestamp >= _context['time_limit']:
                keep_running = False
    # End of main loop
# End def run


def calculate_budget(data_size, samples, failure_count, ruleset, method=arguments.Budget.CONFIDENCE):
    """"""
    # TODO: Move this calculation to the experimenter
    if method not in arguments.Budget.values():
        raise ValueError("Unknown method '{}'".format(method))
    _log.debug("Setting rule budget according to method \"{}\".".format(method))

    if method == arguments.Budget.CONFIDENCE_AND_RANK:
        # Calculate
        class_ratio = failure_count / data_size if failure_count <= (data_size / 2) else (data_size - failure_count) / data_size
        s_min = min(0.5 * (data_size + samples) - class_ratio * data_size, samples)
        s_maj = max(samples - s_min, 0)

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
        tgt_rules = [r for r in rule_info if r['cls'] == 'FAIL']
        oth_rules = [r for r in rule_info if r['cls'] != 'FAIL']

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
                if rules[i]['cls'] == 'FAIL':
                    if failure_count <= (data_size / 2):
                        b = bgts[i] * s_min
                    else:
                        b = bgts[i] * s_maj
                else:
                    if failure_count <= (data_size / 2):
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
        class_ratio = failure_count / data_size if failure_count <= (data_size / 2) else (data_size - failure_count) / data_size
        s_min = min(0.5 * (data_size + samples) - class_ratio * data_size, samples)
        s_maj = max(samples - s_min, 0)

        for i in range(len(ruleset)):
            confidence = ruleset.confidence(i, relative=True, relative_to_class=True)
            if ruleset[i].get_class() == 'FAIL':
                if failure_count <= (data_size / 2):
                    ruleset[i].set_budget(confidence * s_min)
                else:
                    ruleset[i].set_budget(confidence * s_maj)
            else:  # other_class
                if failure_count <= (data_size / 2):
                    ruleset[i].set_budget(confidence * s_maj)
                else:
                    ruleset[i].set_budget(confidence * s_min)

            _log.debug("Set a budget of {} for rule {}".format(ruleset[i].budget, i))

    elif method == arguments.Budget.RANDOM:

        # Handle the case where there is no rules
        if len(ruleset) == 0:
            return

        # Calculate the number of rules in each class
        n_fail_rules = len([r for r in ruleset if r.get_class() == 'FAIL'])
        n_pass_rules = len([r for r in ruleset if r.get_class() == 'PASS'])

        # This should never happen
        if n_fail_rules == 0 and n_pass_rules == 0:
            return

        # Assign the budget to each class
        if n_fail_rules == 0:
            fail_budget = 0
            pass_budget = 1
        elif n_pass_rules == 0:
            fail_budget = 1
            pass_budget = 0
        else:
            fail_budget = random.random()
            pass_budget = 1 - fail_budget

        # Distribute the budget to each rule
        fail_budget_list = list()
        pass_budget_list = list()
        if n_fail_rules > 0:
            fail_budget_list = [random.random() for _ in range(n_fail_rules)]
            while sum(fail_budget_list) == 0: # Avoid division by zero
                fail_budget_list = [random.random() for _ in range(n_fail_rules)]
            fail_budget_list = [
                (float(x) / float(sum(fail_budget_list))) * float(fail_budget) * samples for x in fail_budget_list
            ]

        if n_pass_rules > 0:
            pass_budget_list = [random.random() for _ in range(n_pass_rules)]
            while sum(pass_budget_list) == 0: # Avoid division by zero
                pass_budget_list = [random.random() for _ in range(n_pass_rules)]
            pass_budget_list = [
                (float(x) / float(sum(pass_budget_list))) * float(pass_budget) * samples for x in pass_budget_list
            ]

        # Assign the budget to each rule
        for i in range(len(ruleset)):
            if ruleset[i].get_class() == 'FAIL':
                ruleset[i].set_budget(fail_budget_list.pop())
            else:
                ruleset[i].set_budget(pass_budget_list.pop())
            _log.debug("Set a budget of {} for rule {}".format(ruleset[i].budget, i))

    elif method == arguments.Budget.RANDOM_UNIFORM:
        # Create a random budget for each rule
        n_rules = len(ruleset)
        budget_list = [random.random() for _ in range(n_rules)]
        budget_list = [(float(x) / float(sum(budget_list))) * float(samples) for x in budget_list]
        # Round the budget so that the sum is equal to count
        for i in range(n_rules):
            ruleset[i].set_budget(budget_list[i])
            _log.debug("Set a budget of {} for rule {}".format(ruleset[i].budget, i))

    elif method == arguments.Budget.RANDOM_BIN:
        n_rules = len(ruleset)
        budget_list = [float(0) for _ in range(n_rules)]
        for i in range(samples):
            budget_list[random.randint(0, n_rules - 1)] += 1.0
        for i in range(n_rules):
            ruleset[i].set_budget(budget_list[i])
            _log.debug("Set a budget of {} for rule {}".format(ruleset[i].budget, i))

    elif method == arguments.Budget.RANDOM_CONSTANT:
        # calculate the ratio of each class
        if failure_count > (data_size / 2):
            fail_budget = failure_count / data_size
            pass_budget = 1 - fail_budget
        else:
            pass_budget = (data_size - failure_count) / data_size
            fail_budget = 1 - pass_budget

        # calculate the number of rules in each class
        n_fail_rules = len([r for r in ruleset if r.get_class() == 'FAIL'])
        n_pass_rules = len([r for r in ruleset if r.get_class() == 'PASS'])

        # This should never happen
        if n_fail_rules == 0 and n_pass_rules == 0:
            return

        # Assign the budget to each class
        if n_fail_rules == 0:
            fail_budget = 0
            pass_budget = 1
        if n_pass_rules == 0:
            fail_budget = 1
            pass_budget = 0

        # Distribute the budget to each rule
        fail_budget_list = list()
        pass_budget_list = list()
        if n_fail_rules > 0:
            fail_budget_list = [random.random() for _ in range(n_fail_rules)]
            while sum(fail_budget_list) == 0:  # Avoid division by zero
                fail_budget_list = [random.random() for _ in range(n_fail_rules)]
            fail_budget_list = [
                (float(x) / float(sum(fail_budget_list))) * float(fail_budget) * samples for x in fail_budget_list
            ]

        if n_pass_rules > 0:
            pass_budget_list = [random.random() for _ in range(n_pass_rules)]
            while sum(pass_budget_list) == 0:  # Avoid division by zero
                pass_budget_list = [random.random() for _ in range(n_pass_rules)]
            pass_budget_list = [
                (float(x) / float(sum(pass_budget_list))) * float(pass_budget) * samples for x in pass_budget_list
            ]

        # Assign the budget to each rule
        for i in range(len(ruleset)):
            if ruleset[i].get_class() == 'FAIL':
                ruleset[i].set_budget(fail_budget_list.pop())
            else:
                ruleset[i].set_budget(pass_budget_list.pop())
            _log.debug("Set a budget of {} for rule {}".format(ruleset[i].budget, i))
# End def calculate_budget


# ===== ( Cleanup function ) ===========================================================================================

def cleanup(*args):
    """
    Clean up all file inside /var/run.
    """
    global _crashed

    if setup.config().general.cleanup is True:
        _log.info("Cleaning up fuzzsdn...")

        # Stop all the drivers
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
    _log.info("Exiting fuzzsdn.")
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
        failure_under_test,
        samples,
        method,
        budget,
        ml_algorithm,
        ml_filter,
        ml_cv_folds,
        mutation_rate,
        scenario_options : Optional[dict] = None,
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
            print("New WEKA packages have been installed. Please restart fuzzsdn to complete installation.")
            jvm.stop()
            sys.exit(0)

        _log.debug("WEKA packages check has been done.")

        # Launch run function
        run(
            mode='new',
            scenario=scenario,
            criterion=criterion,
            failure_under_test=failure_under_test,
            samples=samples,
            method=method,
            budget=budget,
            ml_algorithm=ml_algorithm,
            ml_filter=ml_filter,
            ml_cv_folds=ml_cv_folds,
            mutation_rate=mutation_rate,
            scenario_options=scenario_options,
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
