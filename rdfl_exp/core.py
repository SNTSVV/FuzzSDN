#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
import os
import shutil
import time
from os.path import join

# Local dependencies
import rdfl_exp.experiment.data as exp_data
import rdfl_exp.experiment.script as exp_script
import rdfl_exp.machine_learning.algorithms as ml_alg
import rdfl_exp.machine_learning.data as ml_data
from rdfl_exp import config
from rdfl_exp.machine_learning.rule import Rule
from rdfl_exp.utils import csv
from rdfl_exp.utils.terminal import Style

# ===== ( Dicts ) ==============================================================

STATS = {
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
        "precision_score"   : list(),
        "recall_score"      : list(),
        "rules"             : list(),
    }
}

DEFAULT_INPUT = {
    "n_samples": 500,
    "max_iterations": 50,
    "precision_threshold": 0.85,
    "recall_threshold": 0.85,
    "class_to_predict": "non_parsing_error",
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


# ===== ( RUN function ) =======================================================

def run(args) -> None:

    # Parse the input file
    if args.in_file:
        with open(args.in_file, "r") as in_file:
            input_data = json.load(in_file)
    else:
        input_data = DEFAULT_INPUT
    # Run the main loop

    # Variables initialization
    rules = list()  # List of rules
    precision = 0   # Algorithm precision
    recall = 0      # Algorithm recall
    dataset_path = join(config.tmp_dir(), "dataset.csv")  # Create a file where the dataset will be stored

    # Get some variables from the input json file
    precision_th = input_data["precision_threshold"]  # Precision Threshold
    recall_th = input_data["recall_threshold"]  # Recall Threshold
    default_criteria = input_data["fuzzer"]["default_criteria"]
    default_match_limit = input_data["fuzzer"]["default_match_limit"]
    default_actions = input_data["fuzzer"]["default_actions"]
    class_to_predict = input_data["class_to_predict"]  # Class to predict
    ## Maximum number of iteration
    it_max = input_data["max_iterations"]
    STATS["context"]["max_it"] = it_max
    ## Number of samples to generate per iterations
    n_samples = args.samples if args.samples else input_data["n_samples"]

    ## Get the initial rules
    rules = input_data["initial_rules"] if "initial_rules" in input_data else rules

    # Display header:
    it = 0  # iteration index
    while ((it < it_max) and
           (recall < recall_th or precision < precision_th)):

        # Register timestamp at the beginning of the iteration
        start_of_it = time.time()

        # Write headers
        print(Style.BOLD
              + "*** Iteration {}/{}".format(it + 1, it_max)
              + Style.RESET)
        print(Style.BOLD
              + "*** recall: {}/{}".format(recall, recall_th)
              + Style.RESET)
        print(Style.BOLD
              + "*** precision: {}/{}".format(precision, precision_th)
              + Style.RESET)

        # If no rules where generated, we use the default fuzzer action and
        # generate the required amount of data
        if len(rules) <= 0:
            fuzz_instr = {
                "criteria": default_criteria,
                "matchLimit": default_match_limit,
                "actions": default_actions
            }

            # Build the fuzzer instruction and Collect 'nb_of_samples' data
            exp_script.run(
                count=n_samples,
                instructions=json.dumps({"instructions": [fuzz_instr]}),
                clear_db=True
                # Clear the database before the experiment on the first iteration
            )

        # Otherwise, we parse the rules and generate data accordingly
        else:
            for rule_it in range(len(rules)):
                # Get Rule properties
                rule = Rule.from_dict(rules[rule_it])
                print(Style.BOLD + "*** Applying rule: {}".format(
                    rule) + Style.RESET)

                # Calculate the number of times the experiment should be run with the rule
                nb_of_samples = int(math.floor(float(n_samples) / len(rules)))

                # Build the fuzzer instruction and Collect 'nb_of_samples' data
                fuzz_instr = {
                    "criteria": default_criteria,
                    "matchLimit": default_match_limit,
                    "actions": rule.to_fuzzer_actions()
                }

                exp_script.run(
                    count=nb_of_samples,
                    instructions=json.dumps({"instructions": [fuzz_instr]}),
                    clear_db=True if (rule_it == 0) else False
                    # Clear the database before the experiment if it is the first rule
                )

        # Fetch the experiment data
        if not os.path.exists(dataset_path):
            # Fetch the dataset
            exp_data.fetch(dataset_path)
            # Copy the raw version of the dataset to the exp folder
            shutil.copy(src=dataset_path,
                        dst=join(config.EXP_DIR, "datasets",
                                 "it_{}_raw.csv".format(it)))
            # Format the dataset
            ml_data.format_csv(dataset_path, sep=';')
        else:
            # Fetch the data into a temporary dictionary
            tmp_dataset_path = join(config.tmp_dir(), "temp_data.csv")
            exp_data.fetch(tmp_dataset_path)
            # Copy the raw version of the dataset to the exp folder
            shutil.copy(src=tmp_dataset_path,
                        dst=join(config.EXP_DIR, "datasets",
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
                    dst=join(config.EXP_DIR, "datasets", "it_{}.csv".format(it)))

        # Convert the set to an arff file
        csv.to_arff(
            csv_path=dataset_path,
            arff_path=join(config.tmp_dir(), "dataset.arff"),
            csv_sep=';',
            relation='dataset_iteration_{}'.format(it)
        )

        # Perform machine learning algorithms
        start_of_ml = time.time()

        out_rules, precision, recall = ml_alg.standard(
            join(config.tmp_dir(), "dataset.arff"),
            tt_split=70.0,
            cv_folds=10,
            seed=12345
        )
        end_of_ml = time.time()

        # Avoid cases where precision or recall are NaN values
        if math.isnan(recall):
            recall = 0.0
        if math.isnan(precision):
            precision = 0.0

        # Assign results from machine learning
        rules = list()  # Reset the rules
        for rule in out_rules:
            # Add the rules that match the class to predict and that have at least
            # one condition
            if (rule.get_class() == class_to_predict and
                    len(rule.get_conditions()) > 0):
                rules += [rule.to_dict()]  # Assign the new rule to the rules

        # End of iteration total time
        end_of_it = time.time()

        # Update the timing statistics
        STATS["time"]["iteration"] += [str(end_of_it - start_of_it)]
        STATS["time"]["learning"] += [str(end_of_ml - start_of_ml)]
        # Update the ml statistics
        STATS["machine_learning"]["precision_score"] += [precision]
        STATS["machine_learning"]["recall_score"] += [recall]
        STATS["machine_learning"]["rules"] += [
            [str(r) for r in out_rules]] if len(out_rules) > 0 else [[]]
        # Update the context statistics
        STATS["context"]["nb_of_it"] = it + 1

        # Save the statistics to the stats
        with open(join(config.EXP_DIR, 'stats.json'), 'w') as stats_file:
            json.dump(STATS, stats_file)

        # Increment the number of iterations
        it += 1

    # Print statistics
    print("Number of iterations:", it)
    print("Final Recall:", recall)
    print("Final Precision:", precision)
    print("Final Rules:", rules)

