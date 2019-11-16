'''
Title:          myrouter_part1
Description:    Project 2, part 1 - implement basic ARP handling in a simulated router
Authors:        David Billmire, Shang Ding
Course:         UWCS 640, Section 2, Fall 2019
'''

import sys
import os
import time

from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *

'''
Class:          ARPContext
Description:    Implements basic ARP functions, including IP to MAC translation and table management
                ARP Context is iterable and supports direct get/set of IPv4 -> MAC mapping
'''
class ARPContext:
    def __init__(self):
        self.map = {}
        return

    def __iter__(self):
        return iter(self.map)

    def __getitem__(self, item):
        if item in self.map and isinstance(self.map[item], ARPContext.ARPEntry):
            return self.map[item].mac_addr
        else:
            return None

    def __setitem__(self, ip_addr, mac_addr):
        self.add_mapping(ip_addr, mac_addr)
        return

    #Add or updates an IP to MAC address mapping
    #  ip_addr      IPv4Address
    #  mac_addr     EthAddr
    def add_mapping(self, ip_addr, mac_addr):
        if isinstance(ip_addr, IPv4Address) and isinstance(mac_addr, EthAddr):
            self.map[ip_addr] = ARPContext.ARPEntry(mac_addr)
        return

    #Process an ARP requests in the provided packet. Return a reply packet
    #if the target IP address is in our table
    #   pkt         Arp packet to process
    def arp_request(self, pkt: Arp):
        reply_ip  = pkt.targetprotoaddr
        reply_mac = self.map[reply_ip].mac_addr

        #Construct reply packet
        etp = Ethernet(ethertype = EtherType.ARP,
                       src       = reply_mac,
                       dst       = pkt.senderhwaddr)

        arp = Arp(operation         = ArpOperation.Reply,
                  senderhwaddr      = reply_mac,
                  senderprotoaddr   = reply_ip,
                  targethwaddr      = pkt.senderhwaddr,
                  targetprotoaddr   = pkt.senderprotoaddr)

        return_pkt = etp + arp
        return return_pkt

    #Process an ARP reply in the provided packet.
    #   pkt         Arp packet to process
    def arp_reply(self, pkt: Arp):
        self.add_mapping(pkt.senderprotoaddr, pkt.senderhwaddr)

    """
    Class:          ARPContext.ArpEntry
    Description:    Table entry pairing a timestamp with a MAC address
    """
    class ARPEntry:
        def __init__(self, mac_addr, time=time.time()):
            self.mac_addr   = mac_addr
            self.timestamp  = time
            return

# end class ARPContext

class Router(object):
    def __init__(self, net):
        self.net = net
        self.local_proto_eth = ARPContext()     #Local address maps
        self.other_proto_eth = ARPContext()     #Other address maps

        #Cache IP->MAC mapping for local interfaces
        for intf in net.interfaces():
            self.local_proto_eth[intf.ipaddr] = intf.ethaddr

    #Main Router loop
    def router_main(self):    
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''
        while True:
            try:
                _, input_port, pkt = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                log_debug("No packets available in recv_packet")
                continue
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            log_debug("Got a packet: {}".format(str(pkt)))

            #Handle ARP
            if pkt.has_header(Arp):
                self.handle_arp(pkt, input_port)
            else:
                log_debug("Unknown packet type received: {}".format(str(pkt)))

            #TODO: Handle other packets

    #ARP Handler
    def handle_arp(self, pkt: Packet, input_port):

        arp_head = pkt.get_header(Arp)
        if not isinstance(arp_head, Arp): return

        if arp_head.targetprotoaddr in self.local_proto_eth:
            if arp_head.operation == ArpOperation.Request:
                self.send_packet(self.local_proto_eth.arp_request(arp_head), input_port)
                return None

            elif arp_head.operation == ArpOperation.Reply:
                return self.other_proto_eth.arp_reply(arp_head)

            else:
                log_debug("Unknown ARP header operation: {}".format(str(arp_head)))

    #Packet sender
    def send_packet(self, pkt, output_port):

        if not isinstance(pkt, Packet):
            log_debug("send_packet called with invalid packet: {}".format(pkt))
            return

        ports = [ intf.name for intf in self.net.interfaces() ]
        if not output_port in ports:
            log_debug("send_packet called with unknown port: {}".format(output_port))
            return

        try:
            self.net.send_packet(output_port, pkt)
        except ValueError as e:
            log_debug("Failed to send packet. Got ValueError: {}".format(e))
        except:
            log_debug("Failed to send packet. Unknown Error: {}".format(sys.exc_info()[0]))



def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
