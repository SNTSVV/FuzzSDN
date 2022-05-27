# -*- coding: utf-8 -*-
"""
"""

import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor
from os import listdir
from os.path import isfile, join
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sn
from matplotlib import pyplot as plt
from weka.classifiers import Classifier, Evaluation
from weka.core import jvm
from weka.core.converters import Loader

from common import app_path
from common.metrics import density, fraction_of_borderline_points, geometric_diversity, imbalance_ratio, \
    standard_deviation
from common.utils import csv_ops
from common.utils.terminal import progress_bar
from figsdn.experiment import Model
from figsdn_report import nodes

print_evl_data  = True
display_graphs  = False

_COMPUTE_GD         = True
_COMPUTE_N1         = False
_COMPUTE_IR         = True
_COMPUTE_DENSITY    = False
_COMPUTE_STD        = True

use_test_dataset = True
test_data = "/Users/raphael.ollando/OneDrive - University of Luxembourg/04 - papers/00 - paper-1/01 - resources/test_dataset/onos_unkrea_dflt+beads+delta_24000.arff"
# test_data = "/Users/raphael.ollando/OneDrive - University of Luxembourg/04 - papers/00 - paper-1/01 - resources/test_dataset/ryu_unkrea_dflt+beads+delta_24000.arff"
# test_data = "/Users/raphael.ollando/OneDrive - University of Luxembourg/04 - papers/00 - paper-1/01 - resources/test_dataset/onos_unknown_reason_test_dataset.arff"
# test_data = "/Users/raphael.ollando/OneDrive - University of Luxembourg/04 - papers/00 - paper-1/01 - resources/test_dataset/ryu_unknown_reason_test_dataset.arff"

RDFL_REMOTE_EXP_DIR = "/home/{}/.local/share/figsdn/experiments"
RDFL_REPORT_DIR     = os.path.expanduser("~/.figsdn/report")


# ===== ( Helper functions ) ===========================================================================================

def _calculate_data_metrics(stats: dict, local_path, compute_n1=True, compute_ir=True, compute_density=True,
                            compute_gd=True, compute_std=True):
    iterations = stats['context']['iterations']

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
        param_ir = (i, ir, join(local_path['data'], 'it_{}.csv'.format(i)))
        param_gd = (i, gd, join(local_path['data'], 'it_{}.csv'.format(i)))
        param_n1 = (i, n1, join(local_path['data'], 'it_{}.csv'.format(i)))
        param_density = (i, density_, join(local_path['data'], 'it_{}.csv'.format(i)))
        param_std = (i, std_, join(local_path['data'], 'it_{}.csv'.format(i)))

        ir_map += [param_ir]
        gd_map += [param_gd]
        n1_map += [param_n1]
        density_map += [param_density]
        std_map += [param_std]

    # Create the calculation functions for parallelizing the jobs
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

    # Add the metrics to the data key of the stats dict
    if compute_ir is True:
        if 'imbalance' not in stats['data']:
            stats['data']['imbalance'] = list()
        stats['data']['imbalance'] = ir

    if compute_gd is True:
        if 'geometric_diversity' not in stats['data']:
            stats['data']['geometric_diversity'] = list()
        stats['data']['geometric_diversity'] = gd

    if compute_n1 is True:
        if 'N1_score' not in stats['data']:
            stats['data']['N1_score'] = list()
        stats['data']['N1_score'] = n1

    if compute_density is True:
        if 'density' not in stats['data']:
            stats['data']['density'] = list()
        stats['data']['density'] = density_

    if compute_std is True:
        if 'standard_deviation' not in stats['data']:
            stats['data']['standard_deviation'] = list()
        stats['data']['standard_deviation'] = std_

    # Re-save the updated stats.json file
    with open(join(local_path['root'], 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=4, sort_keys=True)
# End def _calculate_data_metrics


def _create_folder_structure(exp):
    #
    # # Create root and report folder
    # dirs = ["{}/.figsdn/".format(os.path.expanduser("~")), report_dir]

    exp_root_dir    = join(app_path.report_dir(), "{}-{}".format(exp, datetime.datetime.now().strftime('%Y%m%d_%H%M%S')))
    exp_data_dir    = join(exp_root_dir, "data")
    exp_model_dir   = join(exp_root_dir, "models")
    exp_graph_dir   = join(exp_root_dir, "graphs")
    exp_cm_dir      = join(exp_root_dir, "confusion_matrices")

    # Create the file dictionary:
    paths = {
        'root'      : app_path.report_dir(),
        'data'      : exp_data_dir,
        'models'    : exp_model_dir,
        'graphs'    : exp_graph_dir,
        'cms'       : exp_cm_dir
    }

    # Create the folder structure:
    try:
        # Data path
        Path(app_path.report_dir()).mkdir(parents=True, exist_ok=True)
        Path(exp_root_dir).mkdir(parents=True, exist_ok=False)
        Path(exp_data_dir).mkdir(parents=False, exist_ok=False)
        Path(exp_model_dir).mkdir(parents=False, exist_ok=False)
        Path(exp_graph_dir).mkdir(parents=False, exist_ok=False)
        Path(exp_cm_dir).mkdir(parents=False, exist_ok=False)
    except Exception:
        raise SystemExit("Cannot create experiment directories")

    return paths
# End def _create_folder_structure


def _generate_confusion_matrices(stats: dict, local_path):
    # TODO: Parallelize the process
    target_class = stats["context"]["target_class"]
    other_class = stats["context"]["other_class"]

    for i in range(stats["context"]["iterations"]):

        plt.clf()

        # Generate the heat map arrays

        tp = stats['learning'][target_class]["num_tp"][i]
        fp = stats['learning'][target_class]["num_fp"][i]
        tn = stats['learning'][target_class]["num_tn"][i]
        fn = stats['learning'][target_class]["num_fn"][i]
        tp = 0 if tp is None else tp
        fp = 0 if fp is None else fp
        tn = 0 if tn is None else tn
        fn = 0 if fn is None else fn

        array = [[tp, fp],
                 [tn, fn]]

        df_cm = pd.DataFrame(array, range(2), range(2))

        # Generate the heatmap
        sn.set(font_scale=1.4)  # for label size
        svm = sn.heatmap(
            df_cm,
            annot=True,
            annot_kws={"size": 16},
            xticklabels=[target_class, other_class],
            yticklabels=[target_class, other_class]
        )

        plt.title("confusion matrix iteration {}".format(i))
        plt.xlabel("predicted")
        plt.ylabel("actual")

        # Save the figure
        fig = svm.get_figure()
        fig.savefig(os.path.join(local_path['cms'], 'cm_it_{}.png'.format(i)))
# End def _generate_confusion_matrices


def _generate_graphics(stats: dict, local_path, show: bool = False):
    """Generate the graphics for the report
    :param stats: The statistics dictionary
    :param show: If set to True, the graphs are display using plt
    """

    it_ax = list(range(stats["context"]["iterations"]))
    rules = stats['learning']['rules']
    target_class = stats["context"]["target_class"]
    other_class = stats["context"]["other_class"]

    # update the font size
    plt.rcParams.update({'font.size': 22})

    # ===== 1st Graph: Number of rules per iteration ===================================================================

    nb_of_rules = [0 if rules[i] is None else len(rules[i]) for i in range(stats["context"]["iterations"])]
    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ### Draw the number of rules graph
    ax.plot(it_ax,
            nb_of_rules,
            ls='-',
            marker='x',
            color='blue',
            label=target_class)
    ### Draw the regression line for the number of rules generated
    x = np.array(range(stats["context"]["iterations"]))
    y = np.array(nb_of_rules)
    coef = np.polyfit(x, y, 1)
    ax.plot(x,
            coef[0] * x + coef[1],
            ls='--',
            color='orange')
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title("Number of rules per iteration")
    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'nb_rules_graph.png'))

    # ===== 2nd Graph: Accuracy ========================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ### Draw the precision graph
    ax.plot(it_ax,
            stats['learning']['accuracy'],
            ls='-',
            marker='x',
            color='blue',
            label="accuracy_score")
    ax.set_ylim([0, 1])
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title('Classifier Accuracy per iteration')

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'accuracy_graph.png'))

    # ===== 3rd Graph TP/FP rate for target_class, TP/FP rate for other class ==========================================

    fig, axs = plt.subplots(1, 2, figsize=(21, 7), dpi=96)

    axs[0].plot(it_ax,
                stats['learning'][target_class]["num_tp"],
                ls='-',
                marker='x',
                color='blue',
                label="TP Rate")
    axs[0].plot(it_ax,
                stats['learning'][target_class]["num_fp"],
                ls='-',
                marker='x',
                color='red',
                label="FP Rate")
    axs[0].locator_params(axis="x", integer=True, tight=True)
    axs[0].legend(loc="lower right", fontsize=10)
    axs[0].set_title('TP/FP Rate for {} per iteration'.format(target_class))

    ### Draw the TP/FP graph for the other class
    axs[1].plot(it_ax,
                stats['learning'][other_class]["num_tp"],
                ls='-',
                marker='x',
                color='blue',
                label="TP Rate")
    axs[1].plot(it_ax,
                stats['learning'][other_class]["num_fp"],
                ls='-',
                marker='x',
                color='red',
                label="FP Rate")
    axs[1].locator_params(axis="x", integer=True, tight=True)
    axs[1].legend(loc="lower right", fontsize=10)
    axs[1].set_title('TP/FP Rate for {}'.format(other_class))

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'tp_fp_rate_graph.png'))

    # ===== 4th graph: Precision =======================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ### Draw the precision graph
    ax.plot(it_ax,
            stats['learning'][target_class]["precision"],
            ls='-',
            marker='x',
            color='blue',
            label='{}-cv'.format(target_class) if print_evl_data else target_class)
    if print_evl_data:
        ax.plot(it_ax,
                stats['test_evl'][target_class]["precision"],
                ls='--',
                marker='x',
                color='orange',
                label='{}-evl'.format(target_class))
    ax.set_ylim([0, 1])
    ax.set_xlabel("iteration")
    ax.set_ylabel("precision")
    ax.xaxis.label.set_color('dimgrey')
    ax.yaxis.label.set_color('dimgrey')
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title('Precision per iteration')

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'precision_graph.png'))

    # ===== 5th graph: Recall ==========================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ax.plot(it_ax,
            stats['learning'][target_class]["recall"],
            ls='-',
            marker='x',
            color='blue',
            label='{}-cv'.format(target_class) if print_evl_data else target_class)
    if print_evl_data:
        ax.plot(it_ax,
                stats['test_evl'][target_class]['recall'],
                ls='--',
                marker='x',
                color='orange',
                label='{}-evl'.format(target_class))
    ax.set_ylim([0, 1])
    ax.set_xlabel("iteration")
    ax.set_ylabel("recall")
    ax.xaxis.label.set_color('dimgrey')
    ax.yaxis.label.set_color('dimgrey')
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title('Recall per iteration')

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'recall_graph.png'))

    # ===== 6th graph: F1-Score ========================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ### Draw the F1-Score graph
    ax.plot(it_ax,
            stats['learning'][target_class]['f_measure'],
            ls='-',
            marker='x',
            color='blue',
            label=target_class)
    if print_evl_data:
        ax.plot(it_ax,
                stats['test_evl'][target_class]['f_measure'],
                ls='--',
                marker='^',
                color='orange',
                label=other_class)
    ax.set_ylim([0, 1])
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title('F1-Score per iteration')

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'f1_graph.png'))

    # ===== 7th graph: Area under ROC ==================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)

    ax.plot(it_ax,
            stats['learning'][target_class]["auroc"],
            ls='-',
            marker='x',
            color='blue')
    ax.set_ylim([0, 1])
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title('Area under ROC per iteration')

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'auc_roc_graph.png'))

    # ===== 8th graph: Area under PRC ==================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    ax.plot(it_ax,
            stats['learning'][target_class]["auprc"],
            ls='-',
            marker='x',
            color='blue',
            label='{}-cv'.format(target_class) if print_evl_data else target_class)
    ax.set_ylim([0, 1])
    ax.set_xlabel("iteration")
    ax.set_ylabel("prc in %")
    ax.xaxis.label.set_color('dimgrey')
    ax.yaxis.label.set_color('dimgrey')
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title('Area under PRC per iteration')

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'auc_prc_graph.png'))

    # ===== 9th graph: MCC =============================================================================================

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
    min_mcc = min(0 if v is None else v for v in stats['learning'][target_class]["mcc"])
    max_mcc = max(0 if v is None else v for v in stats['learning'][target_class]["mcc"])
    min_ax = 0 if min_mcc > 0 else min_mcc - 0.25
    max_ax = 1 if max_mcc > 0.5 else max_mcc + 0.25
    ax.plot(it_ax,
            stats['learning'][target_class]["mcc"],
            ls='-',
            marker='x',
            color='blue',
            label=target_class)
    ax.set_ylim([min_ax, max_ax])
    ax.locator_params(axis="x", integer=True, tight=True)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title('MCC score per iteration')

    plt.tight_layout()
    plt.plot()
    if show is True:
        plt.show()
    fig.savefig(os.path.join(local_path['graphs'], 'mcc_graph.png'))

    # ===== 10th graph: ratio of class and other class instances =======================================================

    if _COMPUTE_IR is True and 'imbalance' in stats['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.set_ylim([0, 1])
        ax.plot(it_ax,
                stats['data']['imbalance'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="upper right", fontsize=10)
        ax.set_title("Imbalance per iteration")

        plt.tight_layout()
        plt.plot()
        if show is True:
            plt.show()
        fig.savefig(os.path.join(local_path['graphs'], 'imbalance_graph.png'))

    # ===== 11th graph: Geometric Diversity ==================================================================

    if _COMPUTE_GD is True and 'geometric_diversity' in stats['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.plot(it_ax,
                stats['data']['geometric_diversity'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="upper left", fontsize=10)
        ax.set_title("Geometric Diversity")

        plt.tight_layout()
        plt.plot()
        if show is True:
            plt.show()
        fig.savefig(os.path.join(local_path['graphs'], 'gd_score_graph.png'))

    # ===== 12th graph: N1 Score ==================================================================

    if _COMPUTE_N1 is True and 'N1_score' in stats['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.plot(it_ax,
                stats['data']['N1_score'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="upper left", fontsize=10)
        ax.set_title("N1 Score")

        plt.tight_layout()
        plt.plot()
        if show is True:
            plt.show()
        fig.savefig(os.path.join(local_path['graphs'], 'n1_score_graph.png'))

    # ===== 13th graph: Standard Deviation =============================================================================

    if _COMPUTE_STD is True and 'standard_deviation' in stats['data']:
        fig, ax = plt.subplots(1, 1, figsize=(10, 7), dpi=96)
        ### Draw the F1-Score graph
        ax.plot(it_ax,
                stats['data']['standard_deviation'],
                ls='-',
                marker='x',
                color='blue',
                label=target_class)
        ax.locator_params(axis="x", integer=True, tight=True)
        ax.legend(loc="upper left", fontsize=10)
        ax.set_title("Standard Deviation per Iteration")

        plt.tight_layout()
        plt.plot()
        if show is True:
            plt.show()
        fig.savefig(os.path.join(local_path['graphs'], 'std_graph.png'))
# End def _generate_graphics


def _generate_report(stats: dict, local_path):
    #
    rules = stats['learning']['rules']
    target_class = stats['context']['target_class']

    # Write about the context
    if len(stats['context']['criterion']['kwargs']) > 0:
        criterion_kwargs = ", ".join('{}: {}'.format(key, stats['context']['criterion']['kwargs'][key]) for key in
                                     stats['context']['criterion']['kwargs'].keys())
        criterion_kwargs = "({})".format(criterion_kwargs)
    else:
        criterion_kwargs = ''

    lines = [
        "======== Context ========\n\n",
        "Scenario: {}\n".format(stats['context']['scenario']),
        "Criterion: {} {}\n".format(stats['context']['criterion']['name'], criterion_kwargs),
        "Target class: \"{}\" (other class: \"{}\")\n".format(stats['context']['target_class'],
                                                              stats['context']['other_class']),
        "Samples per iteration: {}\n".format(stats['context']['samples_per_iteration']),
        "Mutation enabled: {}\n".format(stats['context']['enable_mutation']),
        "Mutation rate: {}\n".format(
            stats['context']['mutation_rate'] if stats['context']['enable_mutation'] is True else "N/A"),
        # "Data formatting method used: {}\n\n".format(stats['context']['data_format_method']),
        "\n======== Iteration Summary ========\n\n"
    ]

    for i in range(stats["context"]["iterations"]):
        # First compute the rule string
        rule_str = ""
        nb_of_rules = 0
        if rules[i] is not None:
            for rule in rules[i]:
                nb_of_rules += 1
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
        lines.append("\t\tPrecision for target class: {}\n".format(stats['learning'][target_class]["precision"][i]))
        lines.append("\t\tRecall for target class: {}\n\n".format(stats['learning'][target_class]["recall"][i]))

        # Write the time used per iteration:
        iteration_time = str(datetime.timedelta(seconds=float(stats["timing"]["iteration"][i])))
        learning_time = str(datetime.timedelta(seconds=float(stats["timing"]["learning"][i])))
        lines.append("\tTime taken to finish the iteration: {}\n".format(iteration_time))
        lines.append("\ttime taken to generate the classifier: {}\n\n".format(learning_time))

        # Add the rules
        lines.append("\tNumber of Rules generated: {}\n".format(nb_of_rules))
        if nb_of_rules > 0:
            lines.append("\tRules:\n")
            lines.append(rule_str)
        lines.append("\n")

    # Write the lines to the report file
    with open(os.path.join(local_path['root'], "report.txt"), 'w') as f:
        f.writelines(lines)
# End def _generate_report


def reevaluate_against_test_data(stats: dict, test_data_path, local_path):
    # TODO: Parallelize the process
    # Get the target and other class
    target_class = stats['context']['target_class']
    other_class = stats['context']['other_class']

    iterations = stats['context']['iterations']

    # First, add the data_evaluation metrics to the stats
    stats['test_evl']               = dict()
    stats['test_evl']['accuracy']   = list()
    stats['test_evl']['confidence'] = list()
    stats['test_evl']['rules']      = list()
    stats['test_evl'][target_class] = dict()
    stats['test_evl'][other_class]  = dict()

    for class_ in (target_class, other_class):
        stats['test_evl'][class_]["num_tp"]     = list()
        stats['test_evl'][class_]["num_fp"]     = list()
        stats['test_evl'][class_]["num_tn"]     = list()
        stats['test_evl'][class_]["num_fn"]     = list()
        stats['test_evl'][class_]["precision"]  = list()
        stats['test_evl'][class_]["recall"]     = list()
        stats['test_evl'][class_]["f_measure"]  = list()
        stats['test_evl'][class_]["mcc"]        = list()
        stats['test_evl'][class_]["auroc"]      = list()
        stats['test_evl'][class_]["auprc"]      = list()

    print("Evaluating the generated models against the test data: \"{}\"".format(test_data_path))
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
        model_path = join(local_path['models'], 'it_{}.model'.format(i))
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
            stats['test_evl']["accuracy"]   += [model.info.accuracy]
            if model.ruleset is not None:
                stats['test_evl']['confidence'] += [model.ruleset.confidence()]
            else:
                stats['test_evl']['confidence'] += [None]
        else:
            stats['test_evl']["accuracy"]   += [None]
            stats['test_evl']['confidence'] += [None]

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
            stats['test_evl']['rules'] += [rules_info]

        for class_ in (target_class, other_class):
            if model is not None and class_ in model.info.classes:
                stats['test_evl'][class_]['num_tp']       += [model.info.num_fp[class_]]
                stats['test_evl'][class_]['num_fp']       += [model.info.num_tp[class_]]
                stats['test_evl'][class_]['num_tn']       += [model.info.num_tn[class_]]
                stats['test_evl'][class_]['num_fn']       += [model.info.num_fn[class_]]
                stats['test_evl'][class_]['precision']    += [model.info.precision[class_]]
                stats['test_evl'][class_]['recall']       += [model.info.recall[class_]]
                stats['test_evl'][class_]['f_measure']    += [model.info.f_measure[class_]]
                stats['test_evl'][class_]['mcc']          += [model.info.mcc[class_]]
                stats['test_evl'][class_]['auroc']        += [model.info.auroc[class_]]
                stats['test_evl'][class_]['auprc']        += [model.info.auprc[class_]]
            else:
                stats['test_evl'][class_]['num_tp']       += [None]
                stats['test_evl'][class_]['num_fp']       += [None]
                stats['test_evl'][class_]['num_tn']       += [None]
                stats['test_evl'][class_]['num_fn']       += [None]
                stats['test_evl'][class_]['precision']    += [None]
                stats['test_evl'][class_]['recall']       += [None]
                stats['test_evl'][class_]['f_measure']    += [None]
                stats['test_evl'][class_]['mcc']          += [None]
                stats['test_evl'][class_]['auroc']        += [None]
                stats['test_evl'][class_]['auprc']        += [None]

        progress_bar(
            iteration=i+1,
            total=iterations,
            prefix='\rProgress',
            suffix='Complete {}/{}'.format(i+1, iterations),
            print_end=''
        )

        # Re-save the updated stats.json file
        with open(join(local_path['root'], 'stats.json'), 'w') as f:
            json.dump(stats, f, indent=4, sort_keys=True)
# End def reevaluate_against_test_data

# ===== ( Main Loop ) ==================================================================================================


def fetch(hostname, port, username, password, expt, debug : bool = False):

    # Create the local folder structure
    if debug is True:
        print("Creating output folder for experiment {}".format(expt))
    local_path = _create_folder_structure(expt)

    # Fetch the experiment files
    nodes.fetch_experiment_files(
        hostname=hostname,
        port=port,
        username=username,
        password=password,
        expt=expt,
        dest_root=local_path['root'],
        dest_data=local_path['data'],
        dest_models=local_path['models'],
        quiet=not debug
    )

    # Get the statistics
    with open(join(local_path['root'], "stats.json"), 'r') as jl:
        stats = json.load(jl)

    # Extract some more statistics from the datasets
    print("Extracting information from the datasets")
    raw_files = [join(local_path['data'], f) for f in listdir(local_path['data']) if
                 isfile(join(local_path['data'], f)) and f.endswith("raw.csv")]
    csv_ops.merge(csv_in=raw_files,
                  csv_out=join(local_path['data'], "merged_raw.csv"),
                  in_sep=[';'] * len(raw_files),
                  out_sep=';')
    df = pd.read_csv(join(local_path['data'], "merged_raw.csv"), sep=";")

    target_class = stats["context"]["target_class"]
    other_class = stats["context"]["other_class"]

    if use_test_dataset is True:
        # Start the JVM

        if debug is True:
            print("Starting the JVM".format(expt))
        try:
            jvm.start(packages=True)
            reevaluate_against_test_data(stats=stats, test_data_path=test_data, local_path=local_path)
        finally:
            jvm.stop()

    # Calculate the metrics on data for the experiments
    _calculate_data_metrics(
        stats,
        local_path=local_path,
        compute_n1=_COMPUTE_N1,
        compute_ir=_COMPUTE_IR,
        compute_density=_COMPUTE_DENSITY,
        compute_gd=_COMPUTE_GD,
        compute_std=_COMPUTE_STD
    )

    # Create the report
    print("Generating the report")
    _generate_report(stats, local_path=local_path)

    # Create the graph
    print("Generating the graphs")
    _generate_graphics(stats, local_path=local_path, show=display_graphs)

    # Create the confusion matrices
    print("Generating the confusion matrices")
    _generate_confusion_matrices(stats, local_path=local_path)

    print("Results at last iteration for {}:".format(target_class))
    print(
        "\t Precision: {}{}".format(
            stats['learning'][target_class]['precision'][-1],
            ' ({})'.format(stats['test_evl'][target_class]['precision'][-1] if 'test_evl' in stats else '')
        )
    )
    print(
        "\t Recall: {}{}".format(
            stats['learning'][target_class]['recall'][-1],
            ' ({})'.format(stats['test_evl'][target_class]['recall'][-1] if 'test_evl' in stats else '')
        )
    )

    if _COMPUTE_GD is True:
        print("\t Geometric diversity: {}".format(stats['data']['geometric_diversity'][-1]))

    if _COMPUTE_IR is True:
        print("\t Imbalance Ratio: {}".format(stats['data']['imbalance'][-1]))

    print("Done")
# End main
