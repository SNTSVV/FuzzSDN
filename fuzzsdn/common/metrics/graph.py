import gower
import numpy as np
import networkx as nx
import pandas as pd

from fuzzsdn.common.metrics import metrics


def eps_nn_graph(X, epsilon : float, include_self=False):

    # Output graph
    out_gr = nx.Graph()

    # Get the gower distance matrix
    cat_feat = np.zeros(X.shape[-1], dtype=bool)
    adj_matrix = gower.gower_matrix(X, cat_features=cat_feat)

    for i in range(adj_matrix.shape[1]):
        out_gr.add_node(i)

    edge_x, edge_y = np.where(adj_matrix < epsilon)
    for ix, iy in zip(edge_x.tolist(), edge_y.tolist()):
        if iy != ix or include_self is True:
            out_gr.add_edge(iy, ix)

    return out_gr
# End def eps_nn_graph


def eps_nn_class_graph(X, y, epsilon : float, include_self=False):

    # Output graph
    out_gr = nx.Graph()

    # Get the gower distance matrix
    cat_feat = np.zeros(X.shape[-1], dtype=bool)
    adj_matrix = gower.gower_matrix(X, cat_features=cat_feat)

    for i in range(adj_matrix.shape[1]):
        out_gr.add_node(i)

    # edge_x, edge_y = np.where(adj_matrix < epsilon)
    # for ix, iy in zip(edge_x.tolist(), edge_y.tolist()):
    #     if iy != ix or include_self is True:
    #         # Only keep edges from 2 different classes
    #         if y[ix] != y[iy]:
    #             out_gr.add_edge(iy, ix)

    rows, cols = np.where(adj_matrix < epsilon)
    edges = zip(rows.tolist(), cols.tolist())

    out_gr.add_edges_from(e for e in edges if (e[0] != e[1] or include_self is True) and (y[e[0]] != y[e[1]]))


    return out_gr
# End def eps_nn_graph


if __name__ == '__main__':

    # X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0], [10.0, 11.0, 12.0], [3.0, 2.0, 1.0]])
    # X = np.random.rand(15, 15)
    for i in range(100):
        df = pd.read_csv('/Users/raphael.ollando/.fuzzsdn/report/exp-20220314_181444_from-10.240.5.104_at-20220323_105326/datasets/it_{}.csv'.format(i))
        X = df.drop(columns=['class']).values
        y = df['class'].values

        print(metrics.geometric_diversity(X) / len(X))
        # gr = eps_nn_class_graph(X=X, y=y, epsilon=0.15, include_self=False)
        # print(1 - (2*len(gr.edges))/(len(gr.nodes)*(len(gr.nodes) - 1)))