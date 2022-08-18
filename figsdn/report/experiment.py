# -*- coding: utf-8 -*-
"""
"""

import datetime
import json
import math
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from os.path import join
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import numpy as np
import pandas as pd
import paramiko
import seaborn as sn
from matplotlib import pyplot as plt, ticker
from weka.classifiers import Classifier, Evaluation
from weka.core.converters import Loader

from figsdn.common import app_path
from figsdn.common.metrics import density, fraction_of_borderline_points, geometric_diversity, imbalance_ratio, standard_deviation
from figsdn.common.utils import terminal
from figsdn.common.utils.terminal import progress_bar
from figsdn.app.experiment import Model

print_evl_data  = True
display_graphs  = False


def calculate_metrics(experiment, compute_n1=True, compute_ir=True, compute_density=True, compute_gd=True, compute_std=True):

    # Get the info
    paths       = get_paths(experiment)
    expt_info   = get_info(experiment)

    iterations = expt_info['context']['iterations']

    density_ = [None] * iterations
    n1 = [None] * iterations
    gd = [None] * iterations
    ir = [None] * iterations
    std_ = [None] * iterations

    number_of_metrics = iterations
    ir_map = []
    gd_map = []
    n1_map = []
    density_map = []
    std_map = []

    # Create the parameters
    for i in range(iterations):
        param_ir        = (i, ir      , join(paths.data, 'it_{}.csv'.format(i)))
        param_gd        = (i, gd      , join(paths.data, 'it_{}.csv'.format(i)))
        param_n1        = (i, n1      , join(paths.data, 'it_{}.csv'.format(i)))
        param_density   = (i, density_, join(paths.data, 'it_{}.csv'.format(i)))
        param_std       = (i, std_    , join(paths.data, 'it_{}.csv'.format(i)))

        ir_map += [param_ir]
        gd_map += [param_gd]
        n1_map += [param_n1]
        density_map += [param_density]
        std_map += [param_std]

    # Create the calculation functions for parallelize the jobs
    def calculate_ir(item):
        df = pd.read_csv(join(item[2]))
        y = df['class'].values
        item[1][item[0]] = imbalance_ratio(y)

    def calculate_gd(item):
        df = pd.read_csv(join(item[2]))
        X = df.drop(columns=['class']).values
        item[1][item[0]] = geometric_diversity(X)

    def calculate_n1(item):
        df = pd.read_csv(join(item[2]))
        X = df.drop(columns=['class']).values
        y = df['class'].values
        item[1][item[0]] = fraction_of_borderline_points(X, y)

    def calculate_density(item):
        df = pd.read_csv(join(item[2]))
        X = df.drop(columns=['class']).values
        y = df['class'].values
        item[1][item[0]] = density(X, y)

    def calculate_std(item):
        df = pd.read_csv(join(item[2]))
        X = df.drop(columns=['class']).values
        item[1][item[0]] = standard_deviation(X, normalize=True)

    # Perform the calculations
    with ThreadPoolExecutor() as pool:
        if compute_ir is True:
            print("Calculating Imbalance ratio...")
            count = 0
            progress_bar(
                iteration=count,
                total=number_of_metrics,
                prefix='Progress',
                suffix='Complete {}/{}'.format(count, number_of_metrics)
            )
            for _ in pool.map(calculate_ir, ir_map):
                count += 1
                progress_bar(
                    iteration=count,
                    total=number_of_metrics,
                    prefix='\rProgress',
                    suffix='Complete {}/{}'.format(count, number_of_metrics),
                    print_end=""
                )

        if compute_gd is True:
            print("Calculating Geometric Diversity...")
            count = 0
            progress_bar(
                iteration=count,
                total=number_of_metrics,
                prefix='Progress',
                suffix='Complete {}/{}'.format(count, number_of_metrics)
            )
            for _ in pool.map(calculate_gd, gd_map):
                count += 1
                progress_bar(
                    iteration=count,
                    total=number_of_metrics,
                    prefix='\rProgress',
                    suffix='Complete {}/{}'.format(count, number_of_metrics),
                    print_end=""
                )

        if compute_n1 is True:
            print("Calculating N1 Score ratio...")
            count = 0
            progress_bar(
                iteration=count,
                total=number_of_metrics,
                prefix='Progress',
                suffix='Complete {}/{}'.format(count, number_of_metrics)
            )
            for _ in pool.map(calculate_n1, n1_map):
                count += 1
                progress_bar(
                    iteration=count,
                    total=number_of_metrics,
                    prefix='\rProgress',
                    suffix='Complete {}/{}'.format(count, number_of_metrics),
                    print_end=""
                )

        if compute_density is True:
            print("Calculating Density Score...")
            count = 0
            progress_bar(
                iteration=count,
                total=number_of_metrics,
                prefix='Progress',
                suffix='Complete {}/{}'.format(count, number_of_metrics)
            )
            for _ in pool.map(calculate_density, density_map):
                count += 1
                progress_bar(
                    iteration=count,
                    total=number_of_metrics,
                    prefix='\rProgress',
                    suffix='Complete {}/{}'.format(count, number_of_metrics),
                    print_end=""
                )

        if compute_std is True:
            print("Calculating Standard deviation...")
            count = 0
            progress_bar(
                iteration=count,
                total=number_of_metrics,
                prefix='Progress',
                suffix='Complete {}/{}'.format(count, number_of_metrics)
            )
            for _ in pool.map(calculate_std, std_map):
                count += 1
                progress_bar(
                    iteration=count,
                    total=number_of_metrics,
                    prefix='\rProgress',
                    suffix='Complete {}/{}'.format(count, number_of_metrics),
                    print_end=""
                )

    # Add the metrics to the data key of the expt_info dict
    if compute_ir is True:
        if 'imbalance' not in expt_info['data']:
            expt_info['data']['imbalance'] = list()
        expt_info['data']['imbalance'] = ir

    if compute_gd is True:
        if 'geometric_diversity' not in expt_info['data']:
            expt_info['data']['geometric_diversity'] = list()
        expt_info['data']['geometric_diversity'] = gd

    if compute_n1 is True:
        if 'N1_score' not in expt_info['data']:
            expt_info['data']['N1_score'] = list()
        expt_info['data']['N1_score'] = n1

    if compute_density is True:
        if 'density' not in expt_info['data']:
            expt_info['data']['density'] = list()
        expt_info['data']['density'] = density_

    if compute_std is True:
        if 'standard_deviation' not in expt_info['data']:
            expt_info['data']['standard_deviation'] = list()
        expt_info['data']['standard_deviation'] = std_

    # Re-save the updated stats.json file
    with open(join(paths.root, 'stats.json'), 'w') as f:
        json.dump(expt_info, f, indent=4, sort_keys=True)
# End def _calculate_data_metrics


def calculate_generation_accuracy_per_rule(experiment):

    # Get the experiment info and the paths
    expt_info = get_info(experiment)
    paths = get_paths(experiment)

    # Get the root path of the folder
    it_count = expt_info["context"]["iterations"]

    # Load the last debug file if it exists
    dataset = os.path.join(paths.data, "it_{}_debug.csv".format(it_count-1))
    rule_perf = dict()

    if os.path.exists(dataset):
        expt_info["context"]["has_rule_gen_info"] = True  # Put a flag to notify other functions that this data exists
        df = pd.read_csv(dataset)
        added_count = 0
        for _, row in df.iterrows():
            if not math.isnan(row["rule_id"]):
                added_count += 1
                rule_id = int(row["rule_id"])
                class_match_gen = row["classification"] == row["class"]

                if rule_id in rule_perf.keys():
                    rule_perf[rule_id]["count_gen"] += 1 if class_match_gen is True else 0
                    rule_perf[rule_id]["count_use"] += 1
                else:
                    rule_perf[rule_id] = dict()
                    rule_perf[rule_id]["count_gen"] = 1 if class_match_gen is True else 0
                    rule_perf[rule_id]["count_use"] = 1
        expt_info["context"]["has_rule_gen_info"] = added_count > 0

        # Add the information to the stats file data
        generator = (rl for rl in expt_info['learning']['rules'] if rl is not None)  # Skip the iterations with no rules
        for rule_list in generator:
            for rule in rule_list:
                if rule['id'] in rule_perf.keys():
                    rule.update(rule_perf[rule['id']])

        # Re-save the updated stats.json file
        with open(join(paths.root, 'stats.json'), 'w') as f:
            json.dump(expt_info, f, indent=4, sort_keys=True)

    else:
        expt_info["context"]["has_rule_gen_info"] = False
# End def calculate_prediction_accuracy_per_rule


def create_folder_structure(experiment, test_data : str = None):
    """Create the folder structure for an experiment

    The paths base folder are not overwritten if they already exists.

    Args:
        experiment (str): The name of the experiement
        test_data (str, optional): Optional name of the test data or its path.
            Generate the folder for the test as well. Also copy the test file
            to the root folder if a path is given.
    """
    paths = get_paths(experiment)

    # Create the folder structure:
    try:
        # Data path
        Path(app_path.report_dir()).mkdir(parents=True, exist_ok=True)
        Path(paths.root).mkdir(parents=True, exist_ok=True)
        Path(paths.data).mkdir(parents=False, exist_ok=True)
        Path(paths.models).mkdir(parents=False, exist_ok=True)
        Path(paths.graphs).mkdir(parents=False, exist_ok=True)
        Path(paths.cms).mkdir(parents=False, exist_ok=True)

        if test_data:
            test_paths = get_paths(experiment, test_data=test_data)
            Path(test_paths.root).mkdir(parents=True, exist_ok=True)
            Path(test_paths.data).mkdir(parents=True, exist_ok=True)
            Path(test_paths.graphs).mkdir(parents=False, exist_ok=True)
            Path(test_paths.cms).mkdir(parents=False, exist_ok=True)

    except Exception:
        print(traceback.format_exc())
        raise SystemExit("Cannot create experiment directories")

    return paths
# End def _create_folder_structure


def fetch_experiment_data(hostname, port, username, password, experiment, ignore_existing=False, quiet=False):

    dest_root = join(app_path.report_dir(), experiment)
    dest_data = join(dest_root, "data")
    dest_models = join(dest_root, "models")

    # Define the paths for the experiment
    Path(dest_root).mkdir(parents=True, exist_ok=True)
    Path(dest_models).mkdir(parents=True, exist_ok=True)
    Path(dest_data).mkdir(parents=True, exist_ok=True)

    # Create the ssh connection
    if quiet is not True:
        print("Establishing SSH connection to {}@{}:{}".format(username, hostname, port))

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=hostname,
        port=port,
        username=username,
        password=password
    )

    # Get the user home directory of the node
    _, stdout, _ = ssh.exec_command("eval echo ~$USER")
    usr_home = stdout.readlines()[0].strip()

    # TODO: Find a way to automatically infer the path instead of using hardcoded values
    #       Maybe get them from the configuration file ?
    remote_exp_dir = os.path.join(usr_home, ".local/share/figsdn/experiments")

    # Get the file from the experiment we want to fetch
    with paramiko.Transport((hostname, port)) as transport:
        transport.connect(username=username, password=password)

        with paramiko.SFTPClient.from_transport(transport) as sftp:
            if quiet is not True:
                print("Fetching stats.json..")
            sftp.get(
                os.path.join(remote_exp_dir, experiment, "stats.json"),
                os.path.join(dest_root, "stats.json")
            )

            # Listing all the file in the data directory
            data_list = sftp.listdir(
                os.path.join(remote_exp_dir, experiment, "data")
            )

            # Listing all the files in the model directory
            try:
                model_list = sftp.listdir(
                    os.path.join(remote_exp_dir, experiment, "models")
                )
            except Exception as e:
                print("Cannot load models for exp: {}".format(e))
                model_list = []

    #
    local_data      = os.listdir(dest_data)
    local_models    = os.listdir(dest_models)

    # Create a list of files to download
    files_to_download = []
    data_root   = os.path.join(remote_exp_dir, experiment, "data")
    model_root  = os.path.join(remote_exp_dir, experiment, "models")
    for data in data_list:
        if data not in local_data or ignore_existing is False:
            remote  = os.path.join(data_root, data)
            local   = os.path.join(dest_data, data)
            files_to_download += [(remote, local)]

    for model in model_list:
        if model not in local_models or ignore_existing is False:
            remote = os.path.join(model_root, model)
            local = os.path.join(dest_models, model)
            files_to_download += [(remote, local)]

    # Function to be run in parallel which download the files
    def download(item):
        # print("Downloading item: {}".format(item))
        transport = None
        sftp = None
        try:
            transport = paramiko.Transport((hostname, port))
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get(
                remotepath=item[0],
                localpath=item[1]
            )
        finally:
            if transport:
                transport.close()
            if sftp:
                sftp.close()

    # Execute the downloads
    if len(files_to_download) > 0:
        download_count = 0
        if quiet is not True:
            terminal.progress_bar(
                iteration=download_count,
                total=len(files_to_download),
                prefix='Progress',
                suffix='Complete {}/{}'.format(download_count, len(files_to_download))
            )
        with ThreadPoolExecutor(max_workers=10) as pool:
            for _ in pool.map(download, files_to_download):
                download_count += 1
                if quiet is not True:
                    terminal.progress_bar(
                        iteration=download_count,
                        total=len(files_to_download),
                        prefix='\rProgress',
                        suffix='Complete {}/{}'.format(download_count, len(files_to_download)),
                        print_end=""
                    )
    else:
        print("No new files to fetch")
# End def fetch_experiment_data


def generate_confusion_matrices(experiment : str, test_data : Optional[str] = None):
    """Generate the confusion matrices

    Args:
        experiment (str): Name of the experiment
        test_data (str): The test data
    """
    # TODO: Parallelize the process
    # Get the paths and info
    paths       = get_paths(experiment, test_data=test_data)
    expt_info   = get_info(experiment, test_data=test_data)

    target_class = expt_info["context"]["target_class"]
    other_class = expt_info["context"]["other_class"]
    params_map = []
    for i in range(expt_info["context"]["iterations"]):
        # Confusion matrix for experiment
        if not test_data:
            params_map.append({
                'it': i,
                'data': 'learning',
                'target': target_class,
                'other': other_class,
                'title': "Confusion Matrix - Iteration {}".format(i),
                'path': os.path.join(paths.cms, 'cm_it_{}.png'.format(i))
            })

        # Confusion matrix for test
        elif 'test_evl' in expt_info:
            params_map.append({
                'it': i,
                'data': 'test_evl',
                'target': target_class,
                'other': other_class,
                'title': "Confusion Matrix - Iteration {}".format(i),
                'path': os.path.join(paths.cms, 'cm_it_{}.png'.format(i))
            })
        # Error: no the evaluation as not been performed beforehand
        else:
            raise RuntimeError("No evaluation data found for test \"{}\"".format(Path(test_data).stem))

    def plot_cms(args):

        fig, ax = plt.subplots(1, 1, figsize=(10, 9), dpi=96)
        args = SimpleNamespace(**args)

        # Generate the heat map arrays
        tp = expt_info[args.data][args.target]["num_tp"][args.it]
        fp = expt_info[args.data][args.target]["num_fp"][args.it]
        tn = expt_info[args.data][args.target]["num_tn"][args.it]
        fn = expt_info[args.data][args.target]["num_fn"][args.it]
        tp = 0 if tp is None else tp
        fp = 0 if fp is None else fp
        tn = 0 if tn is None else tn
        fn = 0 if fn is None else fn

        array = [[tp, fp],
                 [fn, tn]]

        df_cm = pd.DataFrame(array, range(2), range(2))

        # Generate the heatmap
        sn.set(font_scale=1.4)  # for label size
        sn.heatmap(
            df_cm,
            annot=True,
            fmt='d',
            annot_kws={"size": 16},
            xticklabels=[args.target, args.other],
            yticklabels=[args.target, args.other]
        )

        ax.set_title(args.title)
        ax.set_xlabel("True Class")
        ax.set_ylabel("Predicted Class")

        # Save the figure
        fig.savefig(args.path)
        plt.close(fig)
    # End def plot_cms

    # Perform the plotting
    count = 0
    progress_bar(
        iteration=count,
        total=len(params_map),
        prefix='Progress',
        suffix='Complete {}/{}'.format(count, len(params_map))
    )
    for p in params_map:
        plot_cms(p)
        count += 1
        progress_bar(
            iteration=count,
            total=len(params_map),
            prefix='\rProgress',
            suffix='Complete {}/{}'.format(count, len(params_map)),
            print_end=""
        )
# End def _generate_confusion_matrices


def generate_graphics(experiment, test_data : Optional[str] = None, display: bool = False):
    """Generate the graphics from the data

    Args:
        experiment (str): The name of the experiment
        test_data (str, optional): The name of the test to generate the graphics for
        display (bool): If set to True, the graphs are displayed using plt
    """
    # Get the paths and experiment information
    paths       = get_paths(experiment, test_data=test_data)
    expt_info   = get_info(experiment, test_data=test_data)

    # Get some constant variables from the experiment info
    it_ax           = list(range(expt_info["context"]["iterations"]))
    rules           = expt_info['learning']['rules']
    target_class    = expt_info["context"]["target_class"]
    other_class     = expt_info["context"]["other_class"]

    # update the font size
    plt.rcParams.update({'font.size': 22})

    # ===== 1st Graph: Number of rules per iteration ===================================================================
    if not test_data:
        nb_of_rules = [0 if rules[i] is None else len(rules[i]) for i in it_ax]
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the number of rules graph
        ax.plot(it_ax,
                nb_of_rules,
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ### Draw the regression line for the number of rules generated
        x = np.array(range(expt_info["context"]["iterations"]))
        y = np.array(nb_of_rules)
        try:
            coef = np.polyfit(x, y, 1)
            ax.plot(x,
                    coef[0] * x + coef[1],
                    ls='--',
                    color='orange')
            ax.locator_params(axis="x", integer=True, tight=True)
            ax.legend(loc="best", fontsize=10)
            ax.set_title("Number of rules per iteration")
            plt.tight_layout()
            plt.plot()
            if display is True:
                plt.show()
            fig.savefig(os.path.join(paths.graphs, 'nb_rules_graph.png'))
            plt.close(fig)
        except Exception as e:
            print("Couldn't plot number of rules per iteration graph. Reason: {}".format(e), file=sys.stderr)

    # ====== 2nd Graph: Average rule usage accuracy per iteration ======================================================

    # proceed only if the information is available
    if not test_data:
        if expt_info["context"]["has_rule_gen_info"] is True:
            avg_gen_acc = []
            rule_lists = expt_info["learning"]["rules"]
            for rule_list in rule_lists:
                tot_gen = 0
                tot_use = 0
                if rule_list is None:
                    avg_gen_acc.append(None)
                    continue
                for rule in rule_list:
                    if 'count_gen' in rule:
                        tot_gen += rule['count_gen']
                        tot_use += rule['count_use']
                if tot_use > 0:
                    avg_gen_acc.append(float(tot_gen) / float(tot_use))
                else:
                    avg_gen_acc.append(0)

            fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
            ax.plot(it_ax, avg_gen_acc, ls='-', marker='x', color='blue')
            ax.set_ylim([0, 1])
            ax.set_title('Average rule generation accuracy per iteration')

            plt.tight_layout()
            plt.plot()
            if display is True:
                plt.show()
            fig.savefig(os.path.join(paths.graphs, 'avg_rule_gen_acc_graph.png'))
            plt.close(fig)

    # ===== 3rd Graph: Accuracy ========================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ### Draw the accuracy graph
    if not test_data:
        ax.plot(it_ax,
                expt_info['learning']['accuracy'],
                ls='-',
                marker='x',
                color='blue',
                label="accuracy_score")
    else:
        ax.plot(it_ax,
                expt_info['learning']['accuracy'],
                ls='-',
                marker='x',
                color='blue',
                label="accuracy-learning")
        ax.plot(it_ax,
                expt_info['test_evl']['accuracy'],
                ls='-',
                marker='x',
                color='blue',
                label="accuracy-test")

    ax.set_ylim([0, 100])
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="best", fontsize=10)
    ax.set_title('Classifier Accuracy per iteration')

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()

    if test_data:
        fig.savefig(os.path.join(paths.graphs, 'accuracy_graph.png'))
    plt.close(fig)

    # ===== 3rd Graph TP/FP/TN/FN for target_class, TP/FP rate for other class ==========================================

    fig, ax = plt.subplots(1, 1, figsize=(21, 7), dpi=96)

    for outcome in ('TP', 'FP', 'TN', 'FN'):
        ax.plot(it_ax,
                expt_info['learning'][target_class]["num_{}".format(outcome.lower())],
                ls='-',
                marker='x',
                label=outcome if not test_data else "learning-{}".format(outcome))
        if test_data:
            ax.plot(it_ax,
                    expt_info['test_evl'][target_class]["num_{}".format(outcome.lower())],
                    ls='-',
                    marker='x',
                    label="test-{}".format(outcome))
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="best", fontsize=10)
    ax.set_title('Number of TP/FP/TN/FN for {} per iteration'.format(target_class))

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()
    fig.savefig(os.path.join(paths.graphs, 'distribution_graph.png'))
    plt.close(fig)

    # ===== 4th graph: Precision =======================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ### Draw the precision graph
    y = [0 if p is None else p for p in expt_info['learning'][target_class]["precision"]]
    y = [0 if math.isnan(p) else p for p in y]
    ax.plot(it_ax,
            y,
            ls='-',
            marker='x',
            color='blue',
            label='precision'.format(target_class) if not test_data else 'learning precision')
    if test_data:
        y = [0 if p is None else p for p in expt_info['test_evl'][target_class]["precision"]]
        y = [0 if math.isnan(p) else p for p in y]
        ax.plot(it_ax,
                y,
                ls='--',
                marker='x',
                color='orange',
                label='test precision')
    ax.set_ylim([0, 1])
    ax.set_xlabel("iteration")
    ax.set_ylabel("precision")
    ax.xaxis.label.set_color('dimgrey')
    ax.yaxis.label.set_color('dimgrey')
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="best", fontsize=10)
    ax.set_title('Precision per iteration')

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()
    fig.savefig(os.path.join(paths.graphs, 'precision_graph.png'))
    plt.close(fig)

    # ===== 5th graph: Recall ==========================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    y = [0 if p is None else p for p in expt_info['learning'][target_class]["recall"]]
    y = [0 if math.isnan(p) else p for p in y]
    ax.plot(it_ax,
            y,
            ls='-',
            marker='x',
            color='blue',
            label='recall' if not test_data else 'learning recall')
    if test_data:
        y = [0 if p is None else p for p in expt_info['test_evl'][target_class]["recall"]]
        y = [0 if math.isnan(p) else p for p in y]
        ax.plot(it_ax,
                y,
                ls='--',
                marker='x',
                color='orange',
                label='test recall')
    ax.set_ylim([0, 1])
    ax.set_xlabel("iteration")
    ax.set_ylabel("recall")
    ax.xaxis.label.set_color('dimgrey')
    ax.yaxis.label.set_color('dimgrey')
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="best", fontsize=10)
    ax.set_title('Recall per iteration')

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()
    fig.savefig(os.path.join(paths.graphs, 'recall_graph.png'))
    plt.close(fig)

    # ===== 6th graph: F1-Score ========================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ### Draw the F1-Score graph
    ax.plot(it_ax,
            expt_info['learning'][target_class]['f_measure'],
            ls='-',
            marker='x',
            color='blue',
            label='F1 Score' if not test_data else 'Learning F1 Score')
    if test_data:
        ax.plot(it_ax,
                expt_info['test_evl'][target_class]['f_measure'],
                ls='--',
                marker='^',
                color='orange',
                label='Test F1 Score')
    ax.set_ylim([0, 1])
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="best", fontsize=10)
    ax.set_title('F1-Score per iteration')

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()
    fig.savefig(os.path.join(paths.graphs, 'f1_graph.png'))
    plt.close(fig)

    # ===== 7th graph: Area under ROC ==================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ax.plot(it_ax,
            expt_info['learning'][target_class]["auroc"],
            ls='-',
            marker='x',
            color='blue',
            label='AUROC' if not test_data else 'Learning AUROC')
    if test_data:
        ax.plot(it_ax,
                expt_info['learning'][target_class]["auroc"],
                ls='-',
                color='orange',
                label='Test AUROC')
        ax.legend(loc="best", fontsize=10)
    ax.set_ylim([0, 1])
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.set_title('Area under ROC per iteration')

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()
    fig.savefig(os.path.join(paths.graphs, 'auc_roc_graph.png'))
    plt.close(fig)

    # ===== 8th graph: Area under PRC ==================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ax.plot(it_ax,
            expt_info['learning'][target_class]["auprc"],
            ls='-',
            marker='x',
            color='blue',
            label='AUPRC' if not test_data else 'Learning AUPRC')
    if test_data:
        ax.plot(it_ax,
                expt_info['learning'][target_class]["auprc"],
                ls='-',
                marker='x',
                color='orange',
                label='Test AUPRC')
        ax.legend(loc="best", fontsize=10)
    ax.set_ylim([0, 1])
    ax.set_xlabel("iteration")
    ax.set_ylabel("prc in %")
    ax.xaxis.label.set_color('dimgrey')
    ax.yaxis.label.set_color('dimgrey')
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.set_title('Area under PRC per iteration')

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()
    fig.savefig(os.path.join(paths.graphs, 'auc_prc_graph.png'))
    plt.close(fig)

    # ===== 9th graph: MCC =============================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    min_mcc = min_ax = math.inf
    max_mcc = max_ax = -math.inf

    if test_data:
        evl_methods = ['learning', 'test_evl']
    else:
        evl_methods = ['learning']

    for method in evl_methods:
        min_mcc = math.inf
        max_mcc = -math.inf
        for v in expt_info[method][target_class]["mcc"]:
            if v is None:  # Important to test before math.isnan
                min_mcc = min(min_mcc, 0)
                max_mcc = max(max_mcc, 0)
            elif math.isnan(v):
                continue
            else:
                min_mcc = min(min_mcc, v)
                max_mcc = max(max_mcc, v)
        min_ax = min(0 if min_mcc > 0 else min_mcc - 0.25, min_ax)
        max_ax = max(1 if max_mcc > 0.5 else max_mcc + 0.25, max_ax)
        ax.plot(
            it_ax,
            expt_info[method][target_class]["mcc"],
            ls='-',
            marker='x',
            color='blue',
            label='MCC' if not test_data else '{} MCC'.format(method)
        )
    try:
        ax.set_ylim([min_ax, max_ax])
    except Exception:
        print("Couldn't determine mcc best y-axis, using the default one", file=sys.stderr)
        ax.set_ylim([-1, 1])
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="best", fontsize=10)
    ax.set_title('MCC score per iteration')

    plt.tight_layout()
    plt.plot()
    if display is True:
        plt.show()
    fig.savefig(os.path.join(paths.graphs, 'mcc_graph.png'))
    plt.close(fig)

    # ===== 10th graph: ratio of class and other class instances =======================================================

    if not test_data and 'imbalance' in expt_info['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.set_ylim([0, 1])
        ax.plot(it_ax,
                expt_info['data']['imbalance'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="best", fontsize=10)
        ax.set_title("Imbalance per iteration")

        plt.tight_layout()
        plt.plot()
        if display is True:
            plt.show()
        fig.savefig(os.path.join(paths.graphs, 'imbalance_graph.png'))
        plt.close(fig)

    # ===== 11th graph: Geometric Diversity ==================================================================

    if not test_data and 'geometric_diversity' in expt_info['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.plot(it_ax,
                expt_info['data']['geometric_diversity'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="best", fontsize=10)
        ax.set_title("Geometric Diversity")

        plt.tight_layout()
        plt.plot()
        if display is True:
            plt.show()
        fig.savefig(os.path.join(paths.graphs, 'gd_score_graph.png'))
        plt.close(fig)

    # ===== 12th graph: N1 Score ==================================================================

    if not test_data and'N1_score' in expt_info['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.plot(it_ax,
                expt_info['data']['N1_score'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="best", fontsize=10)
        ax.set_title("N1 Score")

        plt.tight_layout()
        plt.plot()
        if display is True:
            plt.show()
        fig.savefig(os.path.join(paths.graphs, 'n1_score_graph.png'))
        plt.close(fig)

    # ===== 13th graph: Standard Deviation =============================================================================

    if not test_data and 'standard_deviation' in expt_info['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.plot(it_ax,
                expt_info['data']['standard_deviation'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="best", fontsize=10)
        ax.set_title("Standard Deviation per Iteration")

        plt.tight_layout()
        plt.plot()
        if display is True:
            plt.show()
        fig.savefig(os.path.join(paths.graphs, 'std_graph.png'))
        plt.close(fig)
# End def _generate_graphics


def generate_report(experiment : str):
    """
    Generate a written report for an experiment
    :param experiment: Name of the experiment.
    :type experiment: str
    """
    
    # Get the paths and info
    paths       = get_paths(experiment)
    expt_info   = get_info(experiment)
    # Get the rules and the target_class
    rules = expt_info['learning']['rules']
    target_class = expt_info['context']['target_class']

    # Write about the context
    if len(expt_info['context']['criterion']['kwargs']) > 0:
        criterion_kwargs = ", ".join('{}: {}'.format(key, expt_info['context']['criterion']['kwargs'][key]) for key in expt_info['context']['criterion']['kwargs'].keys())
        criterion_kwargs = "({})".format(criterion_kwargs)
    else:
        criterion_kwargs = ''

    lines = [
        "======== Context ========\n",
        "\n",
        "Scenario: {}\n".format(expt_info['context']['scenario']),
        "Criterion: {} {}\n".format(expt_info['context']['criterion']['name'], criterion_kwargs),
        "Error Type: \"{}\"\n".format(expt_info['context']['target_class']),
        "Method: \"{}\"\n".format(expt_info['context']['method'] if 'method' in 'context' else '?'),
        "Samples per iteration: {}\n".format(expt_info['context']['samples_per_iteration']),
        "Mutation rate: {}\n".format(expt_info['context']['mutation_rate']),
        "\n",
        "======== Iteration Summary ========\n\n"
    ]

    for i in range(expt_info["context"]["iterations"]):
        # First compute the rule string
        rule_str = ""
        nb_of_rules = 0
        if rules[i] is not None:
            for rule in rules[i]:
                nb_of_rules += 1
                conditions = (
                    expt_info["context"]["has_rule_gen_info"] is True,
                    "count_gen" in rule,
                    "count_use" in rule
                )
                if all(conditions):
                    rule_str += "\t\tID: {} | CON: {:.5f} | REL_CON: {:.5f} | BGT: {:.5f} | GEN_ACC: {}/{} ({:.2f}%) | REPR: {}\n".format(
                        rule['id'],
                        rule['confidence'],
                        rule['relative_confidence'],
                        rule['budget'],
                        rule["count_gen"],
                        rule["count_use"],
                        float(rule["count_gen"]) / float(rule["count_use"]) * 100.0,
                        rule['repr']
                    )

                else:
                    rule_str += "\t\tID: {} | CON: {:.5f} | REL_CON: {:.5f} | BGT: {:.5f} | REPR: {}\n".format(
                        rule['id'],
                        rule['confidence'],
                        rule['relative_confidence'],
                        rule['budget'],
                        rule['repr']
                    )

        # Iteration header
        lines.append("=> iteration {}:\n\n".format(i))

        # Write the precision and recall stats achieved
        # if 'pp_filter' in stats['learning']['context'][i]:
        #     lines.append("\tBalancing: {}\n".format(stats['learning']['context'][i]["pp_filter"]["strategy"]))
        #     lines.append("\t\tStrategy: {}\n".format(stats['learning']['context'][i]["pp_filter"]["strategy"]))
        #     lines.append("\t\tNeighbors: {}\n".format(stats['learning']['context'][i]["pp_filter"]["neighbors"]))
        #     lines.append("\t\tPercentage: {}\n".format(stats['learning']['context'][i]["pp_filter"]["factor"]))
        # lines.append("\tcross-val metrics:\n")
        lines.append("\t\tPrecision for target class: {}\n".format(expt_info['learning'][target_class]["precision"][i]))
        lines.append("\t\tRecall for target class: {}\n\n".format(expt_info['learning'][target_class]["recall"][i]))

        # Write the time used per iteration:
        iteration_time = str(datetime.timedelta(seconds=float(expt_info["timing"]["iteration"][i])))
        learning_time = str(datetime.timedelta(seconds=float(expt_info["timing"]["learning"][i])))
        lines.append("\tTime taken to finish the iteration: {}\n".format(iteration_time))
        lines.append("\ttime taken to generate the classifier: {}\n\n".format(learning_time))

        # Add the rules
        lines.append("\tNumber of Rules generated: {}\n".format(nb_of_rules))
        if nb_of_rules > 0:
            lines.append("\tRules:\n")
            lines.append(rule_str)
        lines.append("\n")

    # Write the lines to the report file
    with open(os.path.join(paths.root, "report.txt"), 'w') as f:
        f.writelines(lines)
# End def _generate_report


def generate_result_csv(experiment : str, test_data : Optional[str] = None):
    """Generate a csv file that list all the metrics

    Args:
        experiment (str): Name of the experiment
        test_data (str): The name of the test data.
    """
    # Get the paths and experiment information
    paths = get_paths(experiment, test_data=test_data)
    expt_info = get_info(experiment, test_data=test_data)

    it_cnt = expt_info['context']['iterations']
    tgt_cls = expt_info['context']['target_class']

    df = pd.DataFrame()

    # Add the columns to the dataframe:
    df['accuracy']     = expt_info['learning']["accuracy"]
    df['precision']    = expt_info['learning'][tgt_cls]["precision"]
    df['recall']       = expt_info['learning'][tgt_cls]["recall"]
    df['mcc']          = expt_info['learning'][tgt_cls]["mcc"]
    df['auroc']        = expt_info['learning'][tgt_cls]["auroc"]
    df['auprc']        = expt_info['learning'][tgt_cls]["auprc"]

    # Add the data for the tests
    if 'test_evl' in expt_info and test_data:
        df['test_accuracy']     = expt_info['test_evl']["accuracy"]
        df['test_precision']    = expt_info['test_evl'][tgt_cls]["precision"]
        df['test_recall']       = expt_info['test_evl'][tgt_cls]["recall"]
        df['test_mcc']          = expt_info['test_evl'][tgt_cls]["mcc"]
        df['test_auroc']        = expt_info['test_evl'][tgt_cls]["auroc"]
        df['test_auprc']        = expt_info['test_evl'][tgt_cls]["auprc"]

    df['data_imbalance']        = expt_info['data']["imbalance"]
    if 'geometric_diversity' in expt_info['data']:
        df['data_geom_div']         = expt_info['data']["geometric_diversity"]

    # Save the CSV file
    df.to_csv(
        path_or_buf=os.path.join(paths.root, "results.csv"),
        index=True,
        index_label="iteration",
        sep=",",
    )
# End def generate_result_csv


def get_info(expt, test_data : str = None):
    """Get the information for an experiment

    Args:
        expt (str): The experiment name
        test_data (str, optional): The name of the test data

    Returns:
        (dict) The dictionary containing all the experiment information
    """
    # Get the statistics
    with open(os.path.join(get_paths(expt, test_data=test_data).root, "stats.json"), 'r') as f:
        return json.load(f)
# End def get_info


def get_paths(expt : str, test_data : str = None):
    """Get the information for an experiment

    Args:
        expt (str): The experiment name
        test_data (str, optional): The path of the test data

    Returns:
        (SimpleNamespace) A namespace with all the standard paths for the report
    """
    if not test_data:
        root_dir    = join(app_path.report_dir(), expt)
        data_dir    = join(root_dir, "data")
        model_dir   = join(root_dir, "models")
        graph_dir   = join(root_dir, "graphs")
        cm_dir      = join(root_dir, "confusion_matrices")
    else:
        # Generic paths
        data_dir    = join(app_path.report_dir(), expt, 'data')
        model_dir   = join(app_path.report_dir(), expt, 'models')  # Models are stock in the

        # Test specific paths
        test_data_stem  = Path(test_data).stem
        root_dir        = join(app_path.report_dir(), expt, 'test', test_data_stem)
        graph_dir       = join(root_dir, "graphs")
        cm_dir          = join(root_dir, "confusion_matrices")

    # Create the file dictionary:
    paths = {
        'root'  : root_dir,
        'data'  : data_dir,
        'models': model_dir,
        'graphs': graph_dir,
        'cms'   : cm_dir
    }

    return SimpleNamespace(**paths)
# End def get info


def reevaluate_against_test_data(experiment, test_data_path):
    # TODO: Parallelize the process
    
    # Get the paths and experiment infos
    paths       = get_paths(experiment)
    expt_info   = get_info(experiment)
    test_name   = Path(test_data_path).stem

    # Create the test data directory !
    test_result_path = Path(os.path.join(paths.root, 'test', test_name))
    test_result_path.mkdir(parents=True, exist_ok=True)

    # Get the target and other class
    target_class = expt_info['context']['target_class']
    other_class = expt_info['context']['other_class']

    iterations = expt_info['context']['iterations']

    # First, add the data_evaluation metrics to the expt_info
    expt_info['test_evl']                = dict()
    expt_info['test_evl']['accuracy']    = list()
    expt_info['test_evl']['confidence']  = list()
    expt_info['test_evl']['rules']       = list()
    expt_info['test_evl'][target_class]  = dict()
    expt_info['test_evl'][other_class]   = dict()

    for class_ in (target_class, other_class):
        expt_info['test_evl'][class_]["num_tp"]      = list()
        expt_info['test_evl'][class_]["num_fp"]      = list()
        expt_info['test_evl'][class_]["num_tn"]      = list()
        expt_info['test_evl'][class_]["num_fn"]      = list()
        expt_info['test_evl'][class_]["precision"]   = list()
        expt_info['test_evl'][class_]["recall"]      = list()
        expt_info['test_evl'][class_]["f_measure"]   = list()
        expt_info['test_evl'][class_]["mcc"]         = list()
        expt_info['test_evl'][class_]["auroc"]       = list()
        expt_info['test_evl'][class_]["auprc"]       = list()

    print("Evaluating the generated models against the test data \"{}\"".format(test_name))
    # Load the data
    loader = Loader("weka.core.converters.ArffLoader")
    dataset = loader.load_file(test_data_path)
    dataset.class_is_last()

    progress_bar(
        iteration=0,
        total=iterations,
        prefix='\rProgress',
        suffix='Complete {}/{}'.format(0, iterations),
        print_end=''
    )
    for i in range(iterations):

        model = None
        model_path = join(paths.models, 'it_{}.model'.format(i))
        if os.path.exists(model_path):
            # Deserialize the model
            classifier, data = Classifier.deserialize(model_path)
            # Evaluate it against the test data
            evaluation = Evaluation(dataset)
            evaluation.test_model(classifier, dataset)
            # Create the model object
            model = Model(
                classifier=classifier,
                evaluator=evaluation,
                class_label={
                    0: dataset.attribute(dataset.class_index).value(0),
                    1: dataset.attribute(dataset.class_index).value(1)
                }
            )
        if model is not None:
            expt_info['test_evl']["accuracy"]   += [model.info.accuracy]
            if model.ruleset is not None:
                expt_info['test_evl']['confidence'] += [model.ruleset.confidence()]
            else:
                expt_info['test_evl']['confidence'] += [None]
        else:
            expt_info['test_evl']["accuracy"]   += [None]
            expt_info['test_evl']['confidence'] += [None]

        # Add the rules and their statistics at each iteration
        rules_info = list()
        try:
            for j in range(len(model.ruleset)):
                rule_dict = dict()
                rule_dict['id']                     = model.ruleset[j].id
                rule_dict['class']                  = model.ruleset[j].get_class()
                rule_dict['support']                = model.ruleset.support(j)
                rule_dict['confidence']             = model.ruleset.confidence(j, relative=False)
                rule_dict['relative_confidence']    = model.ruleset.confidence(j, relative=True)
                rule_dict['budget']                 = model.ruleset[j].get_budget()
                rule_dict['repr']                   = str(model.ruleset[j])
                rules_info += [rule_dict]
        except (TypeError, AttributeError):
            # Then rule_set is empty
            rules_info = None
        finally:
            expt_info['test_evl']['rules'] += [rules_info]

        for class_ in (target_class, other_class):
            if model is not None and class_ in model.info.classes:
                expt_info['test_evl'][class_]['num_tp']      += [model.info.num_tp[class_]]
                expt_info['test_evl'][class_]['num_fp']      += [model.info.num_fp[class_]]
                expt_info['test_evl'][class_]['num_tn']      += [model.info.num_tn[class_]]
                expt_info['test_evl'][class_]['num_fn']      += [model.info.num_fn[class_]]
                expt_info['test_evl'][class_]['precision']   += [model.info.precision[class_]]
                expt_info['test_evl'][class_]['recall']      += [model.info.recall[class_]]
                expt_info['test_evl'][class_]['f_measure']   += [model.info.f_measure[class_]]
                expt_info['test_evl'][class_]['mcc']         += [model.info.mcc[class_]]
                expt_info['test_evl'][class_]['auroc']       += [model.info.auroc[class_]]
                expt_info['test_evl'][class_]['auprc']       += [model.info.auprc[class_]]
            else:
                expt_info['test_evl'][class_]['num_tp']      += [None]
                expt_info['test_evl'][class_]['num_fp']      += [None]
                expt_info['test_evl'][class_]['num_tn']      += [None]
                expt_info['test_evl'][class_]['num_fn']      += [None]
                expt_info['test_evl'][class_]['precision']   += [None]
                expt_info['test_evl'][class_]['recall']      += [None]
                expt_info['test_evl'][class_]['f_measure']   += [None]
                expt_info['test_evl'][class_]['mcc']         += [None]
                expt_info['test_evl'][class_]['auroc']       += [None]
                expt_info['test_evl'][class_]['auprc']       += [None]

        progress_bar(
            iteration=i+1,
            total=iterations,
            prefix='\rProgress',
            suffix='Complete {}/{}'.format(i+1, iterations),
            print_end=''
        )

        # Re-save the updated stats.json file
        # TODO: Save the updated one only in the corresponding test folder
        with open(os.path.join(paths.root, 'stats.json'), 'w') as f:
            json.dump(expt_info, f, indent=4, sort_keys=True)

        # Re-save the updated stats.json file to the corresponding test folder
        with open(os.path.join(paths.root, 'test', test_name, 'stats.json'), 'w') as f:
            json.dump(expt_info, f, indent=4, sort_keys=True)
# End def reevaluate_against_test_data
