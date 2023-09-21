#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main script for the report module
"""
from distutils import dir_util, file_util
import logging
import os
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import Optional

from weka.core import jvm

from fuzzsdn.common import app_path, nodes
from fuzzsdn.common.utils import ExitCode
from fuzzsdn.report import experiment


def main(expt, node : Optional[str] = None, disable_fetching : bool = False, ignore_existing : bool = False, test_on_data : Optional[str] = None):

    if node is not None:
        # First check if the node is the known hosts
        if not disable_fetching :
            saved_nodes_list = nodes.list_saved_nodes()
            found_node = False
            user, hostname, port, password = None, None, None, None

            if saved_nodes_list is not None:
                saved_nodes = list(saved_nodes_list.values())
                for saved_node in saved_nodes:
                    # Update the arguments
                    if saved_node['hostname'] == node:
                        hostname    = node
                        port        = saved_node['ssh_port']
                        user        = saved_node['username']
                        password    = saved_node['password']
                        found_node  = True
                        break

            if not found_node:
                raise ValueError("No node registered with name or hostname \'{}\'".format(node))

            # Ensure the test structure is created
            experiment.create_folder_structure(expt, test_data=test_on_data)

            # Fetch the experiment data
            print("Fetching experiment \"{}\" at {}@{}:{}".format(expt, user, hostname, port))
            experiment.fetch_experiment_data(
                hostname=hostname,
                port=port,
                username=user,
                password=password,
                experiment=expt,
                ignore_existing=ignore_existing,
                quiet=False
            )
    elif node is None and not disable_fetching:

        # Make the app path relative to the experiment
        app_path.set_experiment_reference(expt)
        if os.path.exists(app_path.exp_dir()):
            # Ensure the test structure is created for the test data
            experiment.create_folder_structure(expt, test_data=test_on_data)
            report_path = experiment.get_paths(expt)
            # Copy stats.json
            file_util.copy_file(
                src=os.path.join(app_path.exp_dir('root'), 'stats.json'),
                dst=os.path.join(report_path.root, 'stats.json'),
                update=True
            )
            # Copy datasets
            dir_util.copy_tree(
                src=os.path.join(app_path.exp_dir('data')),
                dst=os.path.join(report_path.data),
                update=True,
            )
            # Copy models
            dir_util.copy_tree(
                src=os.path.join(app_path.exp_dir('models')),
                dst=os.path.join(report_path.models),
                update=True,
            )
        else:
            print("No experiment \"{}\" found locally.".format(expt), file=sys.stderr)
            raise SystemExit(ExitCode.EX_DATAERR)

    # Else verify that the experiment exist
    elif os.path.exists(os.path.join(app_path.report_dir(), expt)):
        # Ensure the test structure is created for the test data
        experiment.create_folder_structure(expt, test_data=test_on_data)

    else:
        raise ValueError('There is no report folder for \"{}\" found locally'.format(expt))

    # Calculate the prediction accuracy of the rules
    try:
        experiment.calculate_generation_accuracy_per_rule(expt)
    except JSONDecodeError:
        pass  # It is not possible to calculate the generation accuracy per rule

    # Calculate the metrics on data for the experiments
    experiment.calculate_metrics(
        expt,
        compute_n1=False,
        compute_ir=True,
        compute_density=False,
        compute_gd=False,
        compute_std=True
    )

    if test_on_data:
        print("Evaluating the models against \"{}\"".format(Path(test_on_data).stem))
        try:
            jvm.logger.setLevel(logging.ERROR)
            jvm.start(packages=True)
            jvm.logger = None
            experiment.reevaluate_against_test_data(expt, test_on_data)
        finally:
            jvm.stop()

    # Save the results
    print("Exporting the results as a CSV file...")
    experiment.generate_result_csv(expt)
    if test_on_data:
        experiment.generate_result_csv(expt, test_data=test_on_data)

    # Create the report
    print("Generating the report...")
    experiment.generate_report(expt)

    # Create the graph
    print("Generating the graphs...")
    experiment.generate_graphics(expt)
    if test_on_data:
        experiment.generate_graphics(expt, test_data=test_on_data)

    # Create the confusion matrices
    print("Generating the confusion matrices...")
    experiment.generate_confusion_matrices(expt)
    if test_on_data:
        print("Generating the confusion matrices for test against \"{}\"...".format(os.path.basename(test_on_data)))
        experiment.generate_confusion_matrices(expt, test_data=test_on_data)

    # Print the information about the last experiment
    expt_info = experiment.get_info(expt)
    target_class = expt_info["context"]["target_class"]

    # Print the results about the last data
    print("Results at last iteration for {}:".format(target_class))
    print(
        "\t Precision: {}{}".format(
            expt_info['learning'][target_class]['precision'][-1],
            ' ({})'.format(expt_info['test_evl'][target_class]['precision'][-1] if 'test_evl' in expt_info else '')
        )
    )
    print(
        "\t Recall: {}{}".format(
            expt_info['learning'][target_class]['recall'][-1],
            ' ({})'.format(expt_info['test_evl'][target_class]['recall'][-1] if 'test_evl' in expt_info else '')
        )
    )

    print("\t Imbalance Ratio: {}".format(expt_info['data']['imbalance'][-1]))
    if 'geometric_diversity' in expt_info['data']:
        print("\t Geometric diversity: {}".format(expt_info['data']['geometric_diversity'][-1]))

    print("Done")
# End def main
