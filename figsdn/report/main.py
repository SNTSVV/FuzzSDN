#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main script for the report module
"""
from typing import Optional

from weka.core import jvm

from figsdn.common import nodes
from figsdn.report import experiment


def main(expt, node : str, ignore_existing : bool = False, test_on_data : Optional[str] = None):

    # First check if the node is the known hosts
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

    # Fetch the experiment
    print("Fetching experiment \"{}\" at {}@{}:{}".format(expt, user, hostname, port))

    experiment.create_folder_structure(expt)

    # Fetch the experiment files
    experiment.fetch_files(
        hostname=hostname,
        port=port,
        username=user,
        password=password,
        experiment=expt,
        ignore_existing=ignore_existing,
        quiet=False
    )

    if test_on_data:
        try:
            jvm.start(packages=True)
            experiment.reevaluate_against_test_data(expt, test_on_data)
        finally:
            jvm.stop()

    # Calculate the prediction accuracy of the rules
    experiment.calculate_generation_accuracy_per_rule(expt)

    # Calculate the metrics on data for the experiments
    experiment.calculate_metrics(
        expt,
        compute_n1=False,
        compute_ir=True,
        compute_density=False,
        compute_gd=False,
        compute_std=True
    )

    # Save the results
    print("Exporting the results as a CSV file...")
    experiment.generate_result_csv(expt)

    # Create the report
    print("Generating the report...")
    experiment.generate_report(expt)

    # Create the graph
    print("Generating the graphs...")
    experiment.generate_graphics(expt)

    # Create the confusion matrices
    print("Generating the confusion matrices...")
    experiment.generate_confusion_matrices(expt)

    # Print the information about the last experiment
    expt_info = experiment.get_info(expt)
    target_class = expt_info["context"]["target_class"]

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

    print("\t Geometric diversity: {}".format(expt_info['data']['geometric_diversity'][-1]))
    print("\t Imbalance Ratio: {}".format(expt_info['data']['imbalance'][-1]))

    print("Done")
# End def main
