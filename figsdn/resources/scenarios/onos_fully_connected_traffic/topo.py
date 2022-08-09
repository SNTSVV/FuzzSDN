#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
"""

from itertools import combinations
from mininet.topo import Topo

######################################
######### Global Variables ###########
######################################


######################################
###### Define topologies here ########
######################################

# Data center Spine Leaf Network Topology
class FullyConnectedTopo(Topo):
    """A fully connected topology.

        Args:
            k (int): number of switches
            n (int): number of nodes per switches
    """

    def __init__(self, k, n, **opts):

        super(FullyConnectedTopo, self).__init__(**opts)

        self.k = k
        self.n = n
        switch_list = []
        host_list = []

        # Create the switches
        for i in range(k):
            switch = self.addSwitch('s{}'.format(i + 1))
            switch_list.append(switch)

            # Create the hosts for this switch
            for j in range(n):
                host = self.addHost('h{}{}'.format(i, j))
                self.addLink(host, switch)
                host_list.append(switch)

        # Connect all the switches together
        switch_pairs = combinations(switch_list, 2)
        for s_left, s_right in switch_pairs:
            self.addLink(s_left, s_right)
# End def FullyConnectedTopo


topos = {'fully_connected': (lambda: FullyConnectedTopo(5, 5))}
