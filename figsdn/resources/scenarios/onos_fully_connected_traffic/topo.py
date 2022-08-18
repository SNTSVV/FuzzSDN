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
            s (int): number of switches
            h (int): number of hosts per switches
    """

    def __init__(self, s, h, **opts):

        super(FullyConnectedTopo, self).__init__(**opts)

        self.k = s
        self.n = h
        switch_list = []
        host_list = []

        # Create the switches
        for i in range(s):
            switch = self.addSwitch('s{}'.format(i + 1))
            switch_list.append(switch)

            # Create the hosts for this switch
            for j in range(h):
                host = self.addHost('h{}{}'.format(i, j))
                self.addLink(host, switch)
                host_list.append(switch)

        # Connect all the switches together
        switch_pairs = combinations(switch_list, 2)
        for s_left, s_right in switch_pairs:
            self.addLink(s_left, s_right)
# End def FullyConnectedTopo


topos = {
    '1s_2h' : lambda: FullyConnectedTopo(1, 2),
    '3s_2h' : lambda: FullyConnectedTopo(3, 2),
    '5s_2h' : lambda: FullyConnectedTopo(5, 2),
    '7s_2h' : lambda: FullyConnectedTopo(7, 2),
    '10s_2h': lambda: FullyConnectedTopo(10, 2),
}
