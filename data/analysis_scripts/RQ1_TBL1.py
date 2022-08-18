#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
## Imports
import itertools
import json
from datetime import timedelta

import os

import pandas as pd

from figsdn.common import app_path


## Settings

# Dictionary with all the experiment info.
PLOT_INFO = {

    # ===== ONOS =====

    'groups': {
        "FIGSDN" : {

            'remove_learning_time' : False,
            'experiments' : [
                "TEST_ONOS_NO_SMOTE_ORVM00",
                "TEST_ONOS_NO_SMOTE_ORVM01",
                "TEST_ONOS_NO_SMOTE_ORVM02",
                "TEST_ONOS_NO_SMOTE_ORVM03",
                "TEST_ONOS_NO_SMOTE_ORVM04",
                "TEST_ONOS_NO_SMOTE_ORVM01_2",
                "TEST_ONOS_NO_SMOTE_ORVM02_2",
                "TEST_ONOS_NO_SMOTE_ORVM03_2",
                "TEST_ONOS_NO_SMOTE_ORVM04_2"
            ]
        },

        "FIGSDN_NO_LEARN": {

            'remove_learning_time': True,
            'experiments': [
                "TEST_ONOS_NO_SMOTE_ORVM00",
                "TEST_ONOS_NO_SMOTE_ORVM01",
                "TEST_ONOS_NO_SMOTE_ORVM02",
                "TEST_ONOS_NO_SMOTE_ORVM03",
                "TEST_ONOS_NO_SMOTE_ORVM04",
                "TEST_ONOS_NO_SMOTE_ORVM01_2",
                "TEST_ONOS_NO_SMOTE_ORVM02_2",
                "TEST_ONOS_NO_SMOTE_ORVM03_2",
                "TEST_ONOS_NO_SMOTE_ORVM04_2"
            ]
        },

        "FIGSDN_FULLY_CONNECTED": {

            'remove_learning_time': False,
            'experiments': [
                "RQ3_FULLY_CONNECTED_5_5"
            ]
        },

        "FIGSDN_FULLY_CONNECTED_NO_LEARN": {

            'remove_learning_time': True,
            'experiments': [
                "RQ3_FULLY_CONNECTED_5_5"
            ]
        },

        "BEADS": {
            'remove_learning_time' : True,
            'experiments' : [
                "TEST_ONOS_BEADS_ORVM02",
                # "TEST_ONOS_BEADS_ORVM03",
                "TEST_ONOS_BEADS_ORVM04",
            ],

        },

        "DELTA": {
            'remove_learning_time': True,
            'experiments': [
                "TEST_ONOS_DELTA_ORVM00",
            ],

        }
    }
}
MAX_IT = 40

# ---------
# Main code
# ---------

def main():
    """Main function."""

    data = dict()

    for group, group_info in PLOT_INFO['groups'].items():

        data[group] = dict()
        data[group]['count']    = list()
        data[group]['timing']   = list()

        for j in range(len(group_info['experiments'])):
            path_ = os.path.join(app_path.report_dir(), group_info['experiments'][j], 'stats.json')
            stats = None
            with open(path_, 'r') as f:
                stats = json.load(f)

            target_count      = [int(x) for x in stats['data']['count'][stats['context']['target_class']][:MAX_IT]]
            timing_iteration  = [float(x) for x in stats['timing']['iteration'][:MAX_IT]]

            if group_info['remove_learning_time']:
                timing_learning = [float(x) for x in stats['timing']['learning'][:MAX_IT]]
                timing_iteration = [i_i - l_i for i_i, l_i in zip(timing_iteration, timing_learning)]

            # Finally, accumulate al the timing iterations
            timing_iteration = itertools.accumulate(timing_iteration)

            data[group]['count'].append(target_count)
            data[group]['timing'].append(timing_iteration)

        # Finally, average the count and timings
        data[group]['count'] = [sum(x) / len(x) for x in zip(*data[group]['count'])]
        data[group]['timing'] = [str(timedelta(seconds=sum(x) / len(x))) for x in zip(*data[group]['timing'])]

    # Create the dictionary for
    csv_dict = dict()
    for group in data:
        csv_dict[group + '_count']  = data[group]['count']
        csv_dict[group + '_timing'] = data[group]['timing']


    pd.DataFrame(csv_dict).to_csv(
        os.path.join(app_path.report_dir(), "timing+count.csv".format()),
        sep=',',
        index=True
    )

# End def main


if __name__ == '__main__':
    main()
