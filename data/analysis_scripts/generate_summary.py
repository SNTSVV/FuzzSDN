#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
## Imports
import math
import os

import numpy as np
import pandas as pd

from figsdn.common import app_path

## Settings
IT_LIMIT = 40
ATTRIBUTES = 'iteration_time', 'count_target', 'learning_time'

EXPERIMENTS = {
    'FIGSDN' : [
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
    # 'BEADS' : [
    #
    # ]
}

# ---------
# Main code
# ---------

# -- declare main stuff --
df_dict = {
    'method'    : list(),
    'iteration' : list(),
    'attribute' : list(),
    'mean'      : list(),
    'deviation' : list()
}

# -- Iterate through the summaries to generate --
for method, expt_names in EXPERIMENTS.items():

    stats = list()
    number_of_experiments = len(expt_names)
    for experiment in expt_names:
        with open(os.path.join(app_path.report_dir(), experiment, 'stats.json'), 'r') as f:
            stats.append(json.load(f))

    for i in range(IT_LIMIT):
        for attribute in ATTRIBUTES:
            df_dict['method'].append(method)
            df_dict['iteration'].append(i)
            df_dict['attribute'].append(attribute)

            if attribute == 'iteration_time':
                times = [float(s['timing']['iteration'][i]) for s in stats]
                df_dict['mean'].append(np.nanmean(times))
                df_dict['deviation'].append(np.nanstd(times))

            elif attribute == 'learning_time':
                times = [float(s['timing']['iteration'][i]) for s in stats]
                df_dict['mean'].append(np.nanmean(times))
                df_dict['deviation'].append(np.nanstd(times))

            elif attribute == 'count_target':
                counts = [int(s['data']['count'][s['context']['target_class']][i]) for s in stats]
                counts = [0 if np.isnan(c) else c for c in counts]
                df_dict['mean'].append(np.mean(counts))
                df_dict['deviation'].append(np.std(counts))

# Save the summary
pd.DataFrame(df_dict).to_csv(
    os.path.join(app_path.report_dir(), "summary.csv".format()),
    sep=',',
    index=False
)
