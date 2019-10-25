#!/usr/bin/python

import sys

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI

from time import sleep, time
from subprocess import Popen, PIPE
import subprocess
import os

lg.setLogLevel('info')

class PySwitchTopo(Topo):

    def __init__(self):
        # Add default members to class.
        super(PySwitchTopo, self).__init__()
        #
        #  c1---sw1
        #       |  \
        #       |   sw2---c2
        #       |  /
        #       sw3

        nodeconfig = {'cpu':-1}
        self.addHost('sw1', **nodeconfig)
        self.addHost('sw2', **nodeconfig)
        self.addHost('sw3', **nodeconfig)
        self.addHost('c1', **nodeconfig)
        self.addHost('c2', **nodeconfig)

        self.addLink('sw1', 'sw2', bw=10, delay='100ms')
        self.addLink('sw2', 'sw3', bw=10, delay='100ms')
        self.addLink('sw3', 'sw1', bw=10, delay='100ms')
        self.addLink('sw1', 'c1', bw=10, delay='100ms')
        self.addLink('sw2', 'c2', bw=10, delay='100ms')

def set_ip(net, node1, node2, ip):
    node1 = net.get(node1)
    ilist = node1.connectionsTo(net.get(node2)) # returns list of tuples
    intf = ilist[0]
    intf[0].setIP(ip)

def reset_macs(net, node, macbase):
    ifnum = 1
    node_object = net.get(node)
    for intf in node_object.intfList():
        node_object.setMAC(macbase.format(ifnum), intf)
        ifnum += 1

    for intf in node_object.intfList():
        print node,intf,node_object.MAC(intf)

def set_route(net, fromnode, prefix, nextnode):
    node_object = net.get(fromnode)
    ilist = node_object.connectionsTo(net.get(nextnode))
    node_object.setDefaultRoute(ilist[0][0])

def setup_addressing(net):
    reset_macs(net, 'sw1', '10:00:00:00:00:{:02x}')
    reset_macs(net, 'sw2', '20:00:00:00:00:{:02x}')
    reset_macs(net, 'sw3', '30:00:00:00:00:{:02x}')
    reset_macs(net, 'c1', 'a0:00:00:00:00:{:02x}')
    reset_macs(net, 'c2', 'b0:00:00:00:00:{:02x}')
    set_ip(net, 'c1','sw1','192.168.100.1/24')
    set_ip(net, 'c2','sw2','192.168.100.2/24')

def main():
    topo = PySwitchTopo()
    net = Mininet(controller=None, topo=topo, link=TCLink, cleanup=True)
    setup_addressing(net)
    net.interact()


if __name__ == '__main__':
    main()
