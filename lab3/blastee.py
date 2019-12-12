#!/usr/bin/env python3

"""
Shang to implement
"""

import sys
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *

ENDIAN='big'

class Blastee(object):
    def __init__(self, net):
        self.net = net
        self.intf = self.net.interface_by_name('blastee-eth0')
        self.blaster_ip = IPv4Address("192.168.100.1")
        self.target_ethaddr = EthAddr('40:00:00:00:00:02') # see start_mininet.py
        self.payload = b'\xff' * 8

    def ack(self, packet):
        contents = packet.get_header(RawPacketContents)
        if contents == None:
            log_debug('Ignored packet of unknown type')
            return
        seq_num = int.from_bytes(contents.data[:4], 'big')
        log_info("Got packet seq_num = {}".format(seq_num))

        etp = Ethernet(
            src = self.intf.ethaddr,
            dst = self.target_ethaddr
        )
        ip = IPv4(
            protocol = IPProtocol.UDP,
            src = self.intf.ipaddr,
            dst = self.blaster_ip,
            ttl = 64
        )
        pkt = etp + ip + UDP() + seq_num.to_bytes(4, ENDIAN) + self.payload
        try:
            self.net.send_packet(self.intf.name, pkt)
        except ValueError as e:
            log_debug("Failed to send packet due to ValueError: {}".format(str(e)))
        except:
            log_debug("Failed to send packet due to unknown error: {}".format(
                sys.exc_info()[0]))

    def start(self):
        while True:
            try:
                _, _, packet = self.net.recv_packet()
                self.ack(packet)
            except NoPackets:
                log_debug("No packets available in recv_packet")
                continue
            except Shutdown:
                log_debug("Got shutdown signal")
                break


def main(net):
    blastee = Blastee(net)
    blastee.start()
    net.shutdown()
