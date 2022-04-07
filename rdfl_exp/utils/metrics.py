from collections import Counter

import gower
import numpy as np

from rdfl_exp.utils.mst import mst


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
    V = np.matrix(np.unique(X, axis=0), copy=True)
    return np.linalg.slogdet(V * np.transpose(V))[1]
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
