# -*- coding: utf-8 -*-
"""
Module used to calculate various metrics.
"""

from collections import Counter
from copy import copy
from typing import Iterable, Optional

import gower
import numpy as np
from numpy.linalg import matrix_rank

from common.metrics import graph
from common.metrics.mst import mst


def fraction_of_borderline_points(X : np.ndarray, y : np.ndarray, cat_features : Optional[Iterable[bool]] = None) -> float:
    """
    Calculate Fraction of Borderline Points (N1) score of a dataset.

    :param X: feature vector matrix
    :type X: ndarray
    :param y: target of the feature vector matrix
    :type X: ndarray
    :param cat_features: a boolean array that specifies categorical features
    :type cat_features: list[bool] or None

    :return: the Fraction of Borderline Points (N1) score
    :rtype: float
    """

    if cat_features is None:
        cat_features = []
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


def geometric_diversity(X : np.ndarray) -> float:
    """
    Calculate the geometric diversity of the dataset

    :param X: feature vector matrix
    :type X: np.ndarray
    :return: the GD score of the feature vector matrix X
    :rtype: float
    """
    # Remove the duplicate rows
    vm = np.array(np.unique(X, axis=0), dtype=np.uint64, copy=True)
    # Remove the constant columns
    vm = vm[:, ~(vm == vm[0, :]).all(0)]
    # Calculate the dot product of the matrix and its transpose
    vmtt = np.dot(vm, vm.T)
    # Return the geometric determinant
    return np.linalg.slogdet(vmtt)[1]
# End def geometric_diversity


def imbalance_ratio(y) -> Optional[float]:
    """
    Calculate the imbalance ratio
    :param y: ndarray target
    :return:
    """
    counter = Counter(y)
    total = sum(counter.values())

    # If there is exactly 2 classes we use a simpler formular
    if len(counter) == 2:
        cls_1, cls_2 = counter.keys()
        return 1 - min(counter[cls_1], counter[cls_2])/max(counter[cls_1], counter[cls_2])

    # If there is more than two classes (or always_use_C2 is True) we use the C2 formula
    elif len(counter) > 2:
        ir = 0
        for cls in counter:
            ir += counter[cls] / (total - counter[cls])
        ir *= (len(counter) - 1) / len(counter)
        return 1 - 1 / ir

    # If there is only one class then imbalance cannot be computed
    else:
        return None
# End def imbalance_ratio


def density(X, y, epsilon : float = 0.15):
    """
    Calculate the density of a NN graph
    :param X: ndarray features
    :param y: ndarray target
    :param epsilon:
    :return:
    """
    gr = graph.eps_nn_class_graph(X=X, y=y, epsilon=epsilon, include_self=False)
    return 1 - (2 * len(gr.edges)) / (len(gr.nodes) * (len(gr.nodes) - 1))
# End def density


def standard_deviation(X, normalize : bool = False):
    """
    Calculate the standard deviation of a feature vector matrix X

    :param X: The feature vector matrix
    :param normalize:
    :return:
    """
    data = copy(X)
    # Then normalize the columns
    if normalize is True:
        data = data / data.max(axis=0)
    # Finally, return the standard deviation
    return np.nanstd(data)
# End def standard_deviation
