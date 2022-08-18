#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
## Imports
import itertools
import json
import math
import os

import matplotlib.legend_handler
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as plt_lines
import matplotlib.ticker as mticker
from matplotlib.legend_handler import HandlerBase, HandlerLine2D

from figsdn.common import app_path


## Settings

# Dictionary with all the experiment info.
PLOT_INFO = {

    # ===== ONOS =====

    'category' : ['precision', 'recall', 'imbalance'],
    'test': "ONOS_UNKNOWN_REASON_3_METHODS_15000",
        # 'ONOS_UNKNOWN_REASON_FIGSDN_5000',
        # 'ONOS_UNKNOWN_REASON_BEADS_5000',
        # 'ONOS_UNKNOWN_REASON_DELTA_5000'
    'experiment': {

        "FIGSDN" : [
            "TEST_ONOS_NO_SMOTE_ORVM00",
            "TEST_ONOS_NO_SMOTE_ORVM01",
            "TEST_ONOS_NO_SMOTE_ORVM02",
            "TEST_ONOS_NO_SMOTE_ORVM03",
            "TEST_ONOS_NO_SMOTE_ORVM04",
            "TEST_ONOS_NO_SMOTE_ORVM01_2",
            "TEST_ONOS_NO_SMOTE_ORVM02_2",
            "TEST_ONOS_NO_SMOTE_ORVM03_2",
            "TEST_ONOS_NO_SMOTE_ORVM04_2"
        ],

        "BEADS": [
            "TEST_ONOS_BEADS_ORVM02",
            # "TEST_ONOS_BEADS_ORVM03",
            "TEST_ONOS_BEADS_ORVM04",
        ],

        "DELTA": [
            "TEST_ONOS_DELTA_ORVM00",
        ]
    }

    # RYU
    # 'FIGSDN' : {
    #     'test' : 'ryu_unkrea_dflt+beads+delta_24000',
    #     'dataset' : [
    #         "TEST_RYU_FIGSDN_ORVM06",
    #         "TEST_RYU_FIGSDN_ORVM07",
    #         "TEST_RYU_FIGSDN_ORVM08",
    #     ],
    # }
}

BOXPLOT_FREQUENCY = 2
REPORT_DIR = app_path.report_dir()

NUMBER_OF_IT = 40
STEP_IT  = 1

QUALITY = 150  # dpi
FONTSIZE = 10

REVERSE_IMBALANCE = False

_cm = 1/2.54  # centimeters in inches


# ---------
# Main code
# ---------


class HandlerBoxPlot(HandlerBase):
    """A class to draw a little boxplot symbol for boxplot legends."""

    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):

        # Create a list of all lines
        artists = list()

        # Create the line for the box
        artists.append(
            plt_lines.Line2D(
                np.array([0    , 0    , 1    , 1    , 0])    * 0.8 * (width  - xdescent),
                np.array([0.25 , 0.75 , 0.75 , 0.25 , 0.25]) * 0.8 * (height - ydescent),
                lw=orig_handle.get_linewidth()
            )
        )

        # Top vertical line
        artists.append(
            plt_lines.Line2D(
                np.array([0.5  , 0.5]) * 0.8 * (width  - xdescent),
                np.array([0.75 , 1])   * 0.8 * (height - ydescent),
                lw=orig_handle.get_linewidth()
            )
        )

        # bottom vertical line
        artists.append(
            plt_lines.Line2D(
                np.array([0.5  , 0.5]) * 0.8 * (width  - xdescent),
                np.array([0.25 , 0])   * 0.8 * (height - ydescent),
                lw=orig_handle.get_linewidth()
            )
        )

        # Top whisker
        artists.append(
            plt_lines.Line2D(
                np.array([0.25 , 0.75]) * 0.8 * (width  - xdescent),
                np.array([1    , 1])    * 0.8 * (height - ydescent),
                lw=orig_handle.get_linewidth()
            )
        )

        # top whisker
        artists.append(
            plt_lines.Line2D(
                np.array([0.25 , 0.75]) * 0.8 * (width  - xdescent),
                np.array([0    , 0])    * 0.8 * (height - ydescent),
                lw=orig_handle.get_linewidth()
            )
        )  # bottom whisker

        # # median
        # a_list.append(
        #     plt_lines.Line2D(
        #         np.array([0,1])*width-xdescent,
        #         np.array([0.5,0.5])*height-ydescent,
        #         lw=1
        #     )
        # )

        for a in artists:
            a.set_color(orig_handle.get_color())
        return artists
# End def


def main():
    """Main function."""

    data = dict()
    it_range = list(range(0, NUMBER_OF_IT, STEP_IT))
    test = PLOT_INFO['test']

    for expt, expt_items in PLOT_INFO['experiment'].items():
        data[expt] = dict()



        data[expt] = dict()
        data[expt]['auroc']     = [[0] * len(expt_items) for _ in range(len(it_range))]
        data[expt]['imbalance'] = [[0] * len(expt_items) for _ in range(len(it_range))]
        data[expt]['mcc']       = [[0] * len(expt_items) for _ in range(len(it_range))]
        data[expt]['precision'] = [[0] * len(expt_items) for _ in range(len(it_range))]
        data[expt]['recall']    = [[0] * len(expt_items) for _ in range(len(it_range))]

        # For each dataset, its information
        for j in range(len(expt_items)):
            path_ = os.path.join(app_path.report_dir(), expt_items[j], 'test', test, 'results.csv')
            df = pd.read_csv(path_)

            for i in it_range:
                # Get the test precision, recall, auroc, etc.
                prc = df['test_precision'][i]
                rec = df['test_recall'][i]
                roc = df['test_auroc'][i]
                mcc = df['test_mcc'][i]
                imb = df['data_imbalance'][i]
                # Make sure that all NaN values are replaced by 0
                data[expt]['precision'][i][j]   = prc if not math.isnan(prc) else 0
                data[expt]['recall'][i][j]      = rec if not math.isnan(rec) else 0
                data[expt]['auroc'][i][j]       = roc if not math.isnan(roc) else 0
                data[expt]['mcc'][i][j]         = mcc if not math.isnan(mcc) else 0
                data[expt]['imbalance'][i][j]   = imb if REVERSE_IMBALANCE is False else 1 - imb if not math.isnan(imb) else 0 if REVERSE_IMBALANCE is False else 1

        # Calculate the medians value of each sub set
        data[expt]['medians'] = dict()
        data[expt]['medians']['precision']   = [np.median(p) for p in data[expt]['precision']]
        data[expt]['medians']['recall']      = [np.median(p) for p in data[expt]['recall']]
        data[expt]['medians']['auroc']       = [np.median(p) for p in data[expt]['auroc']]
        data[expt]['medians']['mcc']         = [np.median(p) for p in data[expt]['mcc']]
        data[expt]['medians']['imbalance']   = [np.median(p) for p in data[expt]['imbalance']]

    # Plot the graphs
    # fig, axes = plt.subplots(len(PLOT_INFO['experiment']), len(PLOT_INFO['category']),
    #                          figsize=(len(PLOT_INFO['category']) * 25 * _cm, len(PLOT_INFO['experiment']) * 20 * _cm),
    #                          dpi=QUALITY,
    #                          constrained_layout=True)
    fig, axes = plt.subplots(len(PLOT_INFO['experiment']), len(PLOT_INFO['category']),
                             figsize=(21 * _cm, 14 * _cm),
                             dpi=QUALITY,
                             constrained_layout=True)

    for j in range(len(PLOT_INFO['category'])):
        plot_cat = PLOT_INFO['category'][j]

        expt_keys = list(PLOT_INFO['experiment'].keys())
        # test_keys = list.keys())

        for i in range(len(PLOT_INFO['experiment'])):
            expt            = list(PLOT_INFO['experiment'].keys())[i]
            plot_data       = data[expt][plot_cat]
            plot_medians    = data[expt]['medians'][plot_cat]

            # Create the precision box plot
            ax = axes[i][j]
            # ax.set_xlabel("# of iterations", fontsize=FONTSIZE)
            # ax.set_ylabel(plot_cat, fontsize=FONTSIZE)
            # ax.set_title(plot_cat + ' per iterations', fontsize=FONTSIZE*1.2)
            # ax.margins(x=0, y=0.1)

            bxplt = []  # Will store boxplot objects
            medln = []  # Will store the median line

            # for expt, plt_data, plt_medians in zip(expt_keys, plot_data, plot_medians):
            # Plot the boxplot
            box_pos = tuple(range(1, NUMBER_OF_IT, BOXPLOT_FREQUENCY))  # First iteration at position 1
            # print(expt, plot_data, plot_medians, sep='\n')
            box_data = [plot_data[it] for it in it_range[0::BOXPLOT_FREQUENCY]]
            bxplt = ax.boxplot(
                    box_data,
                    sym='+',
                    positions=box_pos,
                    widths=1,
                    boxprops=dict(color="black")
            )
            # Plot the median line

            medln = ax.plot(
                range(1, NUMBER_OF_IT+1),  # Start iteration count from 1
                plot_medians,
                linewidth=1.0,
            )

            # Build the legend
            ax.legend(
                handles=[bxplt["boxes"][0], medln[0]],
                labels=['distribution', 'median'],
                handler_map={
                    bxplt["boxes"][0]: HandlerBoxPlot(),
                    medln[0]: HandlerLine2D()
                },

                loc='best',
                frameon=True,
                fontsize=FONTSIZE/1.25
            )

            # Sets the limits
            ax.set_xlim(0, NUMBER_OF_IT + 1)
            ax.set_ylim(-0.05, 1.05)
            # Manage the x-axis
            ax.xaxis.grid(True, which='major')
            major_ticks = np.arange(0, NUMBER_OF_IT + 1, 5)  # Major every 5 ticks
            major_ticks[0] = 1
            minor_ticks = np.arange(0, NUMBER_OF_IT + 2, 1)  # Minor every ticks
            ax.set_xticks(major_ticks)
            ax.set_xticklabels(major_ticks)
            ax.set_xticks(minor_ticks, minor=True)

            # Manage the y-axis
            ax.yaxis.grid(True, which='major')
            ax.yaxis.set_minor_locator(mticker.MultipleLocator(0.025))

            # Set the font size of ticks
            ax.tick_params(axis='both', which='major', labelsize=FONTSIZE/1.25)

    # Sets the title for each row and columns
    for ax, col in zip(axes[0], PLOT_INFO['category']):
        ax.set_title(col, size=FONTSIZE)

    for ax, row in zip(axes[:, 0], PLOT_INFO['experiment'].keys()):
        ax.set_ylabel(row, rotation=90, size=FONTSIZE)

    # fig.tight_layout(pad=0.5)
    fig.savefig("RQ1_FIG1.pdf", format='pdf')
    fig.show(fig)
    plt.close(fig)
# End def main


if __name__ == '__main__':
    main()
