#!/usr/bin/env python3

"""
David to implement
"""

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *
import random
import time
import sys

def drop(percent):
    return random.randrange(100) < percent

def delay(mean, std):
    delay =random.gauss(mean, std)
    print(delay)
    if delay > 0:
        time.sleep(delay/1000)

'''
load_file
Loads the configuration file for the middlebox.
Parameters:
    filename    - name of the file to load
Returns:
    dictionary with the following fields:
        s     = pseudorandom seed
        p     = probability of packet drop
        dm    = mean delay time
        dstd  = mean standard deviation
'''
def load_file(filename):
    log_debug("Loading file: {}".format(filename))

    config = {}
    try:
        fh = open(filename, 'r')
        line = fh.read().replace('\n', '').strip()
        fh.close()
    except:
        log_debug("Failed to load config file {}: {}".format(filename, sys.exc_info()))
        return config

    fields = line.split()
    if (len(fields) != 8):
        log_debug("Bad file contents: {}".format(line))
        return config
    for i in range(0, 7, 2):
        key = fields[i].replace('-', '')
        val = fields[i+1]
        config[key] = int(val)

    return config

'''
update_pkt
Replaces the Ethernet header when forwarding.
Updates ttl on the IPv4 header
Parameters:
    pkt         - packet to update
    out_port    - output port (EthAddr)
    out_dst     - dest mac (EthAddr)
'''
def update_pkt(pkt, out_port, out_dst):
    del pkt[0]
    eth_head = Ethernet(src=out_port, dst=out_dst, ethertype=EtherType.IPv4)
    pkt.prepend_header(eth_head)
    pkt[IPv4].ttl -= 1


'''
Returns: True if pkt's ipv4 ttl is 1 or less, False otherwise
'''
def ttl_reached(pkt):
    try:
        return pkt[IPv4].ttl <= 1
    except:
        return False

def switchy_main(net):

    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    config = load_file("./middlebox_params.txt")

    random_seed = config['s']
    random.seed(random_seed) #Extract random seed from params file

    while True:
        try:
            _,dev,pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            continue
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        log_debug("I got a packet {}".format(pkt))

        if not pkt.has_header(IPv4):
            log_debug("Dropping non IPv4 packet {}".format(pkt))
            continue

        if ttl_reached(pkt):
            log_debug("Dropping packet as ttl has been reached {}".format(pkt))
            continue

        if dev == "middlebox-eth0":
            log_debug("Received from blaster: {}".format(pkt))
            '''
            Received data packet
            Should I drop it?

            If not, modify headers, add a delay & send to blastee
            '''
            if drop(config['p']):
                log_debug("Dropping packet: {}".format(pkt))
            else:
                delay(config['dm'], config['dstd'])
                out_intf = net.interface_by_name("middlebox-eth1")
                update_pkt(pkt, out_intf.ethaddr, '20:00:00:00:00:01')
                log_debug("Sending packet: {}".format(pkt))
                net.send_packet("middlebox-eth1", pkt)

        elif dev == "middlebox-eth1":
            log_debug("Received from blastee: {}".format(pkt))
            '''
            Received ACK
            Modify headers & send to blaster. Not dropping ACK packets!
            Don't add any delay as well
            net.send_packet("middlebox-eth0", pkt)
            '''
            out_intf = net.interface_by_name("middlebox-eth0")
            update_pkt(pkt, out_intf.ethaddr, '10:00:00:00:00:01')
            log_debug("Sending packet: {}".format(pkt))
            net.send_packet("middlebox-eth0", pkt)
        else:
            log_debug("Oops :))")

    net.shutdown()
