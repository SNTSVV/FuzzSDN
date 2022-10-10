#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import ast

import arff
import pandas as pd


def merge(csv_in: list, csv_out, in_sep : list = None, out_sep=','):
    """
    Combine two csv file into one
    :param csv_in:
    :param csv_out:
    :param in_sep:
    :param out_sep:
    """
    csv_len = len(csv_in)
    in_sep = [','] * csv_len if in_sep is None else in_sep

    if len(in_sep) != csv_len:
        raise AttributeError("length of sep != len of csv ({} sep for {} csv)".format(len(in_sep), csv_len))

    # combine all files in the list
    df = pd.concat([pd.read_csv(csv_in[i], sep=in_sep[i]) for i in range(csv_len)])

    # export to csv
    df.to_csv(csv_out,
              index=False,
              sep=out_sep,
              encoding='utf-8-sig')
# End def csv


def to_arff(csv_path, arff_path, relation, description='', csv_sep=',', exclude=None):
    """
    Convert a csv file to an arff file
    :param csv_path: The path to the csv file
    :param arff_path: The path to the csv file
    :param relation:
    :param description:
    :param csv_sep: The separator used in the csv file
    :param exclude: the list of columns to be excluded
    """

    df = pd.read_csv(csv_path, sep=csv_sep)

    if exclude is not None:
        for field in exclude:
            df.drop([field], axis='columns', inplace=True)

    # Add the columns attributes to the data
    attributes = []
    for c in df.columns.values[:-1]:
        # By default, all values are numeric
        att = (c, 'NUMERIC')
        # Find if some are booleans
        try:
            var_eval = ast.literal_eval(str(df[c].iloc[0]))
        except ValueError as e:
            print("Failed evaluation: {} for col '{}' ({})".format(df[c].iloc[0], c, str(df[c].iloc[0])))
            raise e
        if type(var_eval) is bool:
            att = (c, ['True', 'False'])
        # Add the attribute tuple to the attributes
        attributes += [att]

    t = df.columns[-1]
    # TODO: Either generalize that part, or change this whole module so it is valid only for the dataset used in this
    #       program.
    attributes += [('error_type', sorted(df[t].unique().astype(str).tolist()))]
    data = [df.loc[i].values[:-1].tolist() + [df[t].loc[i]] for i in
            range(df.shape[0])]

    arff_dict = {
        'attributes': attributes,
        'data': data,
        'relation': relation,
        'description': description
    }

    with open(arff_path, "w", encoding="utf8") as f:
        arff.dump(arff_dict, f)
