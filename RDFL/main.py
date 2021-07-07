#!/usr/bin/env python3
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

import weka.core.jvm as jvm

import experiment.data as exp_data
import experiment.script as exp_script
import helper
import machine_learning.algorithms as ml_alg
import machine_learning.data as ml_data
from const import APP_DIR, APP_NAME, HOME_DIR, RUN_DIR
from machine_learning import rule as ml_rule
from utils import csv
from utils.terminal import Fore, Style

# ===== ( Parameters ) =========================================================

PYTHON_VERSION = '3.9'
LOG_LEVEL = logging.INFO
CLEANUP = True

# ===== ( Statistics Container ) ===============================================

STATS = {
    # Context of the test
    "context": {
        "pid"        : str(),
        "max_it"     : int(),
        "nb_of_it"   : int()
    },
    # Unused for now
    "data" : {},
    "time" : {
        "iteration" : list(),
        "learning"  : list()
    },
    # Information about the ml results
    "machine_learning": {
        "precision_score"   : list(),
        "recall_score"      : list(),
        "rules"             : list()
    }
}


# ===== ( Setup functions ) ====================================================

def parse_arguments():
    """
    Parse the arguments passed to the program.
    """
    parser = argparse.ArgumentParser(description="Run a feedback loop experiment")

    parser.add_argument('--debug',
                        action='store_true',
                        help="Enable debug mode for the logger")

    parser.add_argument('--no-clean',
                        action='store_false',
                        help="Do clean the PID file on exit")

    parser.add_argument('--console-output',
                        action='store_true',
                        help="Logs are also outputted in the sys.stdout")

    parser.add_argument('-s', '--samples', type=int, dest='samples', help="Override the number of samples")

    return parser.parse_args()
# End def parse_arguments


def check_app_dirs():
    """
    Check the availability of the run folder.
    """
    # First we check if the run folder already exists or we create one
    if not os.path.exists(RUN_DIR):
        try:
            os.mkdir(RUN_DIR)
        except Exception:
            raise SystemExit(Fore.RED + Style.BOLD + "Error" + Style.RESET
                             + ": Cannot create run direction under {}. ".format(RUN_DIR)
                             + "Please verify the script got root permissions")

    # Then check if the APP_DIR exists
    if not os.path.exists(APP_DIR):
        try:
            os.mkdir(APP_DIR)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create run direction under {}. ".format(APP_DIR)
            )

    # Set the permissions of the folder to the current user
    user = helper.get_user()
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(user).gr_gid
    os.chown(APP_DIR, uid, gid)


# End def create_run_dir


def configure_logger(level, folder_path):
    """
    Configure the logger.
    """
    if os.path.exists(folder_path) is not True:
        raise OSError("Path {} doesn't exist. Aborting".format(folder_path))

    if folder_path[-1] != '/':
        folder_path += '/'

    if level == logging.DEBUG:
        folder_path += "feedback_loop.debug.log"
    else:
        folder_path += "feedback_loop.log"

    # Setting up the logger
    logging.basicConfig(format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
                        filename=folder_path,
                        level=level)
# End def configure_logger


def check_pid():
    """
    Check the presence of a pid file and verify if another experiment isn't
    running.
    """

    if os.path.isfile("{}/pid".format(RUN_DIR)):
        # There is a PID
        with open("{}/pid".format(RUN_DIR), 'r') as pid_file:
            pid = int(pid_file.readline().rstrip())

        # If the pid is different, we exit the system and notify the user
        if pid != os.getpid():
            try:
                os.kill(pid, 0)
            except OSError:
                process_exists = False
            else:
                process_exists = True

            if process_exists is True:
                raise SystemExit(Fore.YELLOW + Style.BOLD + "Warning" + Style.RESET
                                 + ": Another experiment is already running with pid: {}.\n".format(pid)
                                 + "You can stop it manually with \"sudo kill {}\"".format(pid))
            else:
                print(Fore.YELLOW + Style.BOLD + "Warning" + Style.RESET
                      + ": Previous pid file wasn't cleaned correctly by process: {}.\n".format(pid)
                      + "Overwriting old pid_file.")
                os.remove("{}/pid".format(RUN_DIR))

    # If there is no pid we create one for this program
    with open("{}/pid".format(RUN_DIR), 'w') as pid_file:
        pid_file.write(str(os.getpid()))
        STATS["context"]["pid"] = str(os.getpid())
# End def check_pid

# =====( Signals and cleanup functions )========================================


def cleanup(*args):
    """
    Clean up all file inside /var/run.
    """
    global CLEANUP

    if CLEANUP is True:
        helper.tmp_dir(get_obj=True).cleanup()

        file_list = os.listdir(RUN_DIR)
        # First remove the files
        for filename in file_list:
            os.remove("{}/{}".format(RUN_DIR, filename))
        # Then remove the directory
        os.rmdir(RUN_DIR)
    sys.exit(0)
# End def cleanup


# ====== (Setup Function) =======================================================

def setup(args):
    """
    Setup the program
    """
    # Imports the variables defined in this file
    global LOG_LEVEL
    global CLEANUP

    # Check that we have root permissions to run the program
    if os.geteuid() != 0:
        raise SystemExit(Fore.RED + Style.BOLD + "Error" + Style.RESET
                         + ": This program must be run with root permissions."
                         + " Try again using \"sudo\".")

    # Sets working directory. The code below will traverse the path upwards
    # until it finds the root folder of the project.
    workdir = re.sub(r"(?<={})[\w\W]*".format(APP_NAME), "", os.getcwd())
    os.chdir(workdir)

    # Check if another process is not already running and if a pid file has been
    # created under /var/run/<run_dir_name>/pid
    check_app_dirs()
    check_pid()

    # Assign the arguments
    CLEANUP = args.no_clean
    LOG_LEVEL = logging.DEBUG if args.debug is True else LOG_LEVEL

    # Configuring the logger
    try:
        configure_logger(level=LOG_LEVEL,
                         folder_path="/var/log")

        logger = logging.getLogger()
        if args.console_output:
            logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.info("logger started")

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise SystemExit(Fore.RED + Style.BOLD + "Error" + Style.RESET
                         + ": The logger couldn't be configured.\nAborting...")

    # Transfer the remote experiment file to the remote server


# ====== (Main Function) =======================================================

def main(args):

    # Initialize variables
    rules = list()  # List of rules
    precision = 0   # Algorithm precision
    recall = 0      # Algorithm recall
    dataset_path = os.path.join(helper.tmp_dir(), "dataset.csv")  # Create a file where the dataset will be stored

    # Get Parameters from the input files
    with open("./data/input.json", "r") as json_input_file:
        input_json = json.load(json_input_file)

    # Get some variables from the input json file
    base_instruction = input_json["fuzzer_base_instruction"]
    precision_th = input_json["precision_threshold"]     # Precision Threshold
    recall_th = input_json["recall_threshold"]           # Recall Threshold
    class_to_predict = input_json["class_to_predict"]    # Class to predict

    ## Maximum number of iteration
    it_max = input_json["max_iterations"]
    STATS["context"]["max_it"] = it_max
    ## Number of samples to generate per iterations
    n_samples = args.samples if args.samples else input_json["n_samples"]

    it = 0  # iteration index
    while (it < it_max) and (recall < recall_th or precision < precision_th):

        # Register timestamp at the beginning of the iteration
        start_of_it = time.time()

        # Write headers
        print(Style.BOLD + "*** Iteration {}/{}".format(it+1, it_max) + Style.RESET)
        print(Style.BOLD + "*** recall: {}/{}".format(recall, recall_th) + Style.RESET)
        print(Style.BOLD + "*** precision: {}/{}".format(precision, precision_th) + Style.RESET)

        # If no rules where generated, use the initial rules
        if len(rules) <= 0:
            rules = input_json["initial_rules"]

        # Start data collection:
        for rule in rules:
            # Get Rule properties
            rule_probability = rule["probability"]
            rule = ml_rule.from_dict(rule)
            print(Style.BOLD + "*** Applying rule: {}".format(rule) + Style.RESET)

            # Calculate the number of times the experiment should be run with the rule
            nb_of_samples = int(math.floor(float(n_samples) / len(rules)))

            # Build the fuzzer instruction and Collect 'nb_of_samples' data
            base_instruction["actions"] = rule.to_fuzzer_actions()
            exp_script.run(
                count=nb_of_samples,
                instructions=json.dumps({"instructions": [base_instruction]}),
                clear_db=True if (it == 0) else False  # Clear the database before the experiment on the first iteration
            )

            print(Style.BOLD + "*** Fetching data for rule: {}".format(rule) + Style.RESET)

            # Fetch the experiment data
            if not os.path.exists(dataset_path):
                exp_data.fetch(dataset_path)
                ml_data.format_csv(dataset_path, sep=';')
            else:
                # Fetch the data into a temporary dictionary
                tmp_dataset_path = os.path.join(helper.tmp_dir(), "temp_data.csv")
                exp_data.fetch(tmp_dataset_path)
                ml_data.format_csv(tmp_dataset_path, sep=';')
                # Merge the data into the dataset
                csv.merge(csv_in=[tmp_dataset_path, dataset_path],
                          csv_out=dataset_path,
                          out_sep=';',
                          in_sep=[';', ';'])

        # Save the dataset to a non-temporary folder
        shutil.copyfile(dataset_path, os.path.join(HOME_DIR, "dataset.csv"))

        # Convert the set to an arff file
        csv.to_arff(
            csv_path=dataset_path,
            arff_path=os.path.join(helper.tmp_dir(), "dataset.arff"),
            csv_sep=';',
            relation='dataset_iteration_{}'.format(it)
        )

        # Perform machine learning algorithms
        start_of_ml = time.time()
        tmp_rules, precision, recall = ml_alg.standard(os.path.join(helper.tmp_dir(), "dataset.arff"),
                                                       tt_split=70.0,
                                                       seed=12345)
        end_of_ml = time.time()
        # Assign results from machine learning
        rules = list()  # Reset the rules
        for rule in tmp_rules:
            if rule.get_class() == class_to_predict:
                rules += [{'probability': 1, 'rule': str(rule)}]      # Assign the new rule to the rules

        # # normalize the probabilities
        # total_probability = sum([r["probability"] for r in rules])
        # for rules in rules:
        #     rule["probability"] /= total_probability

        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics
        STATS["time"]["iteration"]  += [str(end_of_it - start_of_it)]
        STATS["time"]["learning"]   += [str(end_of_ml - start_of_ml)]
        # Update the ml statistics
        STATS["machine_learning"]["precision_score"]    += [precision]
        STATS["machine_learning"]["recall_score"]       += [recall]
        STATS["machine_learning"]["rules"]              += [[rule["rule"] for rule in rules]]
        # Update the context statistics
        STATS["context"]["nb_of_it"] = it+1

        # Save the statistics to the stats
        with open(os.path.join(APP_DIR, 'stats.json'), 'w') as stats_file:
            json.dump(STATS, stats_file)

        # Increment the number of iterations
        it += 1

    # Print statistics
    print("Number of iterations:", it)
    print("Final Recall:", recall)
    print("Final Precision:", precision)
    print("Final Rules:", rules)


# ====== (Main) ================================================================

if __name__ == '__main__':

    # Create cleanup signal
    for sig in (signal.SIGABRT, signal.SIGILL, signal.SIGINT, signal.SIGSEGV, signal.SIGTERM):
        signal.signal(sig, cleanup)

    # Create configuration reload signal
    # signal.signal(signal.SIGHUP, None)

    # parse arguments
    args = parse_arguments()

    # Setup the program
    setup(args)

    # Run the main loop
    try:
        jvm.start()  # Start the JVM
        main(args)
    except (Exception,):  # using '(Exception,)' instead of 'Exception' to trick PEP8
        print(traceback.format_exc())
    finally:
        jvm.stop()  # Close the JVM
        cleanup()   # Clean up the program
