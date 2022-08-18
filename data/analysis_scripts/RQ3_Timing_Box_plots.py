#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
## Imports
import itertools
import json
import operator

import math
import os

import matplotlib.legend_handler
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as plt_lines
import matplotlib.ticker as mticker
from matplotlib import ticker
from matplotlib.legend_handler import HandlerBase, HandlerLine2D
from mpl_toolkits.axes_grid1 import make_axes_locatable

from figsdn.common import app_path


## Settings

# Dictionary with all the experiment info.
EXPERIMENTS = (
    "RQ3_FULLY_CONNECTED_1_2",
    "RQ3_FULLY_CONNECTED_3_2",
    "RQ3_FULLY_CONNECTED_5_2",
    "RQ3_FULLY_CONNECTED_7_2",
    "RQ3_FULLY_CONNECTED_10_2"
)
# ITs = [1, 5, 10, 15, 20, 25, 30, 35, 40]
ITs = [i for i in range(1, 41)]
WIDTH = 1
REPORT_DIR = app_path.report_dir()

STEP_IT  = 1

_cm = 1/2.54  # centimeters in inches
QUALITY = 600  # dpi
FONTSIZE = 15
FIGSIZE = (25 * _cm, 15 * _cm)
FONTSIZE_LARGE = 19.5

save_graph = True


# ---------
# Main code
# ---------

def main():
    """Main function."""
    data = dict()

    for expt in EXPERIMENTS:
        # Create dict
        data[expt] = dict()

        # Load stats
        filename = os.path.join(app_path.report_dir(), expt, 'stats.json')
        with open(filename, 'r') as f:
            stats = json.load(f)

        data[expt]['fuzzing']   = [stats['timing']['fuzzing'][i-1] for i in ITs if i <= len(stats['timing']['fuzzing'])]
        data[expt]['testing']   = [stats['timing']['testing'][i-1] - stats['timing']['fuzzing'][i-1] for i in ITs if i <= len(stats['timing']['testing'])]
        data[expt]['planning']  = [stats['timing']['planning'][i-1] for i in ITs if i <= len(stats['timing']['planning'])]
        data[expt]['learning']  = [stats['timing']['learning'][i-1] for i in ITs if i <= len(stats['timing']['learning'])]
        data[expt]['method']    = [x for x in map(operator.add, data[expt]['fuzzing'], map(operator.add, data[expt]['learning'], data[expt]['planning']))]
        data[expt]['iteration'] = [stats['timing']['iteration'][i-1] for i in ITs if i <= len(stats['timing']['iteration'])]

    # Plot the graphs
    labels = ["{}s 2h".format(1 + 2 * j) for j in range(len(EXPERIMENTS))]
    # ===== ( First Graphic with the testing time )
    fig, ax = plt.subplots(1, 1,
                           figsize=FIGSIZE,
                           dpi=QUALITY)

    test_times = list()
    for i in range(len(EXPERIMENTS)):
        expt = EXPERIMENTS[i]
        test_times.append(np.array(data[expt]['testing'])/60)

    bxplt = ax.boxplot(
        test_times,
        sym='k.',
        labels=labels,
        positions=range(len(EXPERIMENTS)),
        widths=0.5,
        patch_artist=True,
        boxprops=dict(color="black", facecolor='white', linewidth=2),
        medianprops=dict(color='black', linewidth=1.5),
        whiskerprops=dict(linewidth=2),
        capprops=dict(linewidth=0)
    )

    ax.grid(True, which='major', axis='y', color='lightgray', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("configurations", fontsize=FONTSIZE, weight='bold')
    ax.set_ylabel("time (min)", fontsize=FONTSIZE, weight='bold')
    ax.tick_params(axis="y", direction="in")
    ax.xaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    ax.yaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    ax.legend(facecolor='white', edgecolor='white', framealpha=1, fontsize=FONTSIZE, loc='upper left')

    plt.tight_layout()
    if save_graph is True:
        fig.savefig("RQ3_FIG1.pdf", format='pdf')
    fig.show(fig)
    plt.close(fig)

    # ===== ( 2nd Graphic with the learning, etc, etc )
    fig, ax = plt.subplots(1, 1,
                           figsize=FIGSIZE,
                           dpi=QUALITY)

    fuzz_times  = list()
    plan_times  = list()
    learn_times = list()

    for i in range(len(EXPERIMENTS)):
        expt = EXPERIMENTS[i]
        fuzz_times.extend([data[expt]['fuzzing'][j]  if j < len(data[expt]['fuzzing']) else 0 for j in range(len(ITs))])
        plan_times.extend([data[expt]['planning'][j] if j < len(data[expt]['planning']) else 0 for j in range(len(ITs))])
        learn_times.extend([data[expt]['learning'][j] if j < len(data[expt]['learning']) else 0 for j in range(len(ITs))])

    box_data = [fuzz_times, learn_times, plan_times]

    bxplt = ax.boxplot(
        box_data,
        labels=['Fuzzing', 'Learning', 'Planning'],
        sym='k.',
        showfliers=True,
        vert=True,
        positions=[0, 1, 2],
        widths=0.5,
        patch_artist=True,
        boxprops=dict(linewidth=2),
        medianprops=dict(color='black'),
        whiskerprops=dict(linewidth=2),
        capprops=dict(linewidth=0),
        zorder=3
    )

    # Fill with the colors
    colors = ['#0000a7', '#eecc16', '#c1272d']
    for patch, color in zip(bxplt['boxes'], colors):
        patch.set_facecolor(color)

    ax.grid(True, which='major', axis='y', color='lightgray', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    ax.set_ylabel("time (s)", fontsize=FONTSIZE, weight='bold')
    ax.set_xlabel("configurations", fontsize=FONTSIZE, weight='bold')
    ax.xaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    ax.yaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    # ax.set_ylimit(0, 10)

    plt.tight_layout()
    if save_graph is True:
        fig.savefig("RQ3_FIG2.pdf", format='pdf')
    fig.show(fig)
    plt.close(fig)



    # if draw_bar_graph is True:
    #     ticks_pos = []
    #     fig, ax = plt.subplots(1, 1,
    #                            figsize=FIGSIZE,
    #                            dpi=QUALITY)
    #
    #     test_times = dict()
    #     means = []
    #     stds = []
    #     for expt in EXPERIMENTS:
    #         means.append(np.mean(data[expt]['testing']) / 60)
    #         stds.append(np.std(data[expt]['testing']) / 60)
    #
    #     bar = ax.bar(labels, means, 1 / len(ITs), yerr=stds, bottom=None, label='test times', color='#c1272d', linewidth=1, edgecolor='black', zorder=3)
    #
    #     # Configure 1st axis
    #     ax.grid(True, which='major', axis='y', color='black', linestyle='-', linewidth=1)
    #     ax.set_xlabel("configurations", fontsize=FONTSIZE, weight='bold')
    #     ax.set_ylabel("time (min)", fontsize=FONTSIZE, weight='bold')
    #     ax.tick_params(axis="y", direction="in")
    #     ax.xaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    #     ax.yaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    #     ax.legend(facecolor='white', edgecolor='white', framealpha=1, fontsize=FONTSIZE, loc='upper left')
    #
    #     fig.tight_layout(pad=0.5)
    #     fig.savefig("RQ3_TEST.pdf", format='pdf')
    #     fig.show(fig)
    #     # plt.close(fig)
    #
    #     # ==== ( Second graphic ) =====
    #
    #     # Configure 1st axis
    #     ax.set_ylabel("time (s)", fontsize=FONTSIZE, weight='bold')
    #     ax.yaxis.set_major_locator(ticker.MultipleLocator(base=5))  # this locator puts ticks at regular intervals
    #     ax.yaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    #     ax.grid(True, which='major', axis='y', color='gray', linestyle='-', linewidth=1)
    #     ax.tick_params(axis="y", direction="in")
    #     ax.set_xlim(0, len(ITs)*len(EXPERIMENTS) + gap*len(ITs) + gap/2)
    #     # ax.set_xticks(np.arange(len(ITs)*len(EXPERIMENTS) + gap*len(ITs)) + gap)
    #     ax.set_xticks(ticks_pos)
    #     ax.set_xticklabels([i if i % 10 == 0 or i == 1 else '' for i in ITs]*len(EXPERIMENTS), rotation=0, fontsize=FONTSIZE)
    #     ax.margins(x=0)
    #     ax.legend(facecolor='white', edgecolor='white', framealpha=1, fontsize=FONTSIZE)
    #
    #     # Configure 2nd axis
    #     ax2 = ax.twiny()
    #     ax2.margins(x=0)
    #     ax2.set_xlabel("configurations", fontsize=FONTSIZE, weight='bold')
    #     ax2.spines["bottom"].set_position(('axes', -0.09))
    #     ax2.tick_params('both', length=0, width=0, which='minor')
    #     ax2.tick_params('both', direction='in', which='major')
    #     ax2.xaxis.set_ticks_position("bottom")
    #     ax2.xaxis.set_label_position("bottom")
    #     ax2.set_xlim(ax.get_xlim())
    #     # ax2_ticks = [i/(len(EXPERIMENTS)) for i in range(len(EXPERIMENTS)+1)]
    #     # ax2_ticks = [1, 6, 12, 18, 24, 30]
    #     ax2_ticks = [0] + [i*(len(ITs)*width+gap) for i in range(1, len(EXPERIMENTS)+1)]
    #     ax2.set_xticks(ax2_ticks)
    #     ax2.xaxis.set_major_formatter(ticker.NullFormatter())
    #     ax2.xaxis.set_minor_locator(ticker.FixedLocator([ax2_ticks[i] + (ax2_ticks[i+1] - ax2_ticks[i])/2 for i in range(0, len(ax2_ticks)-1)]))
    #     ax2.xaxis.set_minor_formatter(ticker.FixedFormatter(labels))
    #     ax2.xaxis.set_tick_params(which='both', labelsize=FONTSIZE)
    #
    #     fig.tight_layout(pad=0.5)
    #     fig.savefig("RQ3_PLAN_LEARN_FUZZ.pdf", format='pdf')
    #     fig.show(fig)
    #     plt.close(fig)

        # First graphics

# End def main


if __name__ == '__main__':
    main()

