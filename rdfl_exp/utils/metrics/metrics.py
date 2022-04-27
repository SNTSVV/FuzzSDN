from collections import Counter

import gower
import numpy as np
import pandas as pd
import sympy

from numpy import absolute, dot, zeros
from numpy.linalg import matrix_rank, norm

from rdfl_exp.utils.metrics import graph
from rdfl_exp.utils.metrics.mst import mst


def fraction_of_borderline_points(X, y, cat_features=[]):
    """
    Calculate Fraction of Borderline Points (N1)
      - X: ndarray features
      - y: ndarray target
      - cat_features: a boolean array that specifies categorical features
    """

    if len(cat_features) == 0:
        cat_features = np.zeros(X.shape[-1], dtype=bool)

    # Calculate Gower distance matrix
    distance_matrix = gower.gower_matrix(X, cat_features=cat_features)

    # Generate a Minimum Spanning Tree
    tree = mst(distance_matrix)
    sub = tree[y[tree[:, 0]] != y[tree[:, 1]]]
    vertices = np.unique(sub.flatten())

    return len(vertices) / X.shape[0]
# End def fraction_of_borderline_points


def geometric_diversity(X):
    """
    Calculate the geometric diversity of the dataset
    :param X:
    :return:
    """
    # Remove the duplicate rows
    vm = np.array(np.unique(X, axis=0), dtype=np.uint64, copy=True)
    # Remove the constant columns
    vm = vm[:, ~(vm == vm[0, :]).all(0)]

    vmtt = np.dot(vm, vm.T)
    # Return the geometric determinant
    return np.linalg.slogdet(vmtt)[1]
# End def geometric_diversity


def imbalance_ratio(X, y):
    """
    Calculate the imbalance ratio
    :param X: ndarray features
    :param y: ndarray target
    :return:
    """
    counter = Counter(y)
    total = sum(counter.values())

    # If there is more than 1 class
    if len(counter) > 1:
        ir = 0
        for cls in counter:
            ir += counter[cls] / (total - counter[cls])
        ir *= (len(counter) - 1) / len(counter)
        return 1 - 1 / ir
    else:  # if there is only one class then imbalance cannot be computed
        return None
# End def imbalance_ratio


def density(X, y):
    """
    Calculate the density of the 0.15-NN graph
    :param X: ndarray features
    :param y: ndarray target
    :return:
    """
    gr = graph.eps_nn_class_graph(X=X, y=y, epsilon=0.15, include_self=False)

    return 1 - (2 * len(gr.edges)) / (len(gr.nodes) * (len(gr.nodes) - 1))
# End def density


def std(X):

    # First remove the constant columns
    x_no_const = X[:, ~(X == X[0, :]).all(0)]
    # Then normalize the columns
    # x_norm = x_no_const / x_no_const.max(axis=0)
    x_norm = X
    # Finally, return the standard deviation
    return np.nanstd(x_norm) / np.mean(x_norm)
# End def std


if __name__ == '__main__':

    # X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0], [10.0, 11.0, 12.0], [3.0, 2.0, 1.0]])
    # X = np.random.rand(15, 15)
    files = (
        '../../bin/.rdfl_exp/report/CA_0_2-20220426_114854/data/it_11.csv',
        '../../bin/.rdfl_exp/report/CA_1_1-20220426_142619/data/it_5.csv',
        '../../bin/.rdfl_exp/report/CA_2_1-20220426_142721/data/it_3.csv',
        '../../bin/.rdfl_exp/report/CA_3_1-20220426_142824/data/it_11.csv',
        '../../bin/.rdfl_exp/report/CA_4_2-20220426_142936/data/it_5.csv',
        '../../bin/.rdfl_exp/report/CA_5_1-20220426_143212/data/it_3.csv',
        '../../bin/.rdfl_exp/report/CA_6_1-20220426_143332/data/it_11.csv',
        '../../bin/.rdfl_exp/report/CA_7_1-20220426_143522/data/it_5.csv',
        '../../bin/.rdfl_exp/report/CA_8-20220426_143709/data/it_3.csv'
    )
    for f in files:
        # for i in range(12):
        df = pd.read_csv(f)
        X = df.drop(columns=['class']).values
        y = df['class'].values

        print(geometric_diversity(X))



    # print(df)

    # for col in df.columns:
    #     for col2 in (c for c in df.columns if c != col):
    #         X = df.drop(columns=[col, col2, 'class'])
    #         print(np.linalg.matrix_rank(np.array(np.unique(X, axis=0), copy=True)),col,col2)



    # print(geometric_diversity(X))