#!/usr/bin/env python3

"""
Shang to implement
"""

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
import time
import sys

ENDIAN='big'

class WindowEntry:
    # WindowEntry is used to track sent pkts attributes, like time of the initial
    # transmission, time of the last [re]transmission, and the sequence number
    def __init__(self, seq_num, ack=False, ts_initial=None, ts_last=None):
        self.seq_num = seq_num
        self.ack = ack
        if ts_initial == None:
            self.ts_initial = time.time()
        if ts_last == None:
            self.ts_last = time.time()


class Blaster:
    def __init__(self, net, params_file):
        self.net = net
        self.parse_params(params_file)
        my_interfaces = net.interfaces()
        if len(my_interfaces) != 1:
            raise Exception("Blaster must have exactly one interface!")
        self.intf = my_interfaces[0]
        self.target_ethaddr = EthAddr('40:00:00:00:00:01') # see start_mininet.py
        self.blast_content = b'\xff' * self.length_per_blast
        self.timeout_ms = 2*self.est_rtt_ms

        self.window = [None for i in range(self.window_size)]
        self.lhs = 1
        self.rhs = 1

        self.metrics_first_sent_time = None
        self.metrics_last_ack_time = None
        self.metrics_total_retrans = 0
        self.metrics_num_timeout = 0
        self.metrics_total_payload_bytes_sent = 0
        self.metrics_min_rtt_ms = None
        self.metrics_max_rtt_ms = None


    def __str__(self):
        ret = ""
        for i in [a for a in dir(self) if not a.startswith('__') and
                not callable(getattr(self, a))]:
            ret += i + " " + str(getattr(self, i)) + "\n"
        return ret

    def assert_window_integrity(self, message=""):
        if self.rhs < self.lhs or self.rhs-self.lhs > self.window_size:
            raise Excpetion("Window property violation " + str(message))

    def parse_params(self, params_file):
        params_map = {
            '-b': {'name': 'blastee_ip', 'type': IPv4Address},
            '-n': {'name': 'total_packet_to_blast', 'type': int},
            '-l': {'name': 'length_per_blast', 'type': int}, # bytes
            '-w': {'name': 'window_size', 'type': int},      # packets
            '-rtt': {'name': 'est_rtt_ms', 'type': int}, # ms
            '-r': {'name': 'recv_timeout_ms', 'type': int},  # ms
            '-alpha': {'name': 'ewma_alpha', 'type': float}
        }
        params_seen = set()

        with open(params_file, 'r') as f:
            fields = f.readline().strip().split()
        if len(fields) != 14:
            raise Exception(str(params_file) + " contain odd # of fields")

        while len(fields):
            key= fields[0]
            value = fields[1]
            params_seen.add(key)
            if key not in params_map:
                raise Exception("unknown input parameter: " + str(key))
            setattr(self, params_map[key]['name'],
                    params_map[key]['type'](value))
            fields = fields[2:]

        if len(params_seen) != 7:
            raise Exception("Unexpected # of input pamaraters : " + str(fields))

    def should_stop(self):
        return self.rhs > self.total_packet_to_blast and \
                self.lhs == self.rhs

    def reblast_unack_pkts(self):
        # re-transmit un-ack'ed pkts that have exceeded the timeout
        self.assert_window_integrity()
        for offset in range(self.rhs - self.lhs):
            seq = self.lhs + offset
            now = time.time()
            window_entry = self.window[seq%self.window_size]
            if window_entry.ack:
                continue # don't care about ones that have been ACK'ed already
            age_s = now - window_entry.ts_last
            if age_s*1000 > self.timeout_ms:
                self.send(seq)
                self.window[seq%self.window_size].ts_last = now
                self.metrics_total_retrans += 1
                self.metrics_num_timeout += 1
                log_info("Retransmitted seq {}.".format(seq))

    def blast(self):
        # blast out enough pkts to fill the available window, which may be zero
        # in which case we won't send out anything
        cnt = self.available_window_count()
        if cnt <= 0:
            return
        for _ in range(cnt):
            if self.rhs > self.total_packet_to_blast:
                return
            self.send(self.rhs)
            self.window[self.rhs%self.window_size] = WindowEntry(self.rhs)
            log_debug("blasted pkt with seq # of {}".format(self.rhs))
            self.rhs += 1

    def available_window_count(self):
        # returns # of pkts that can be sent without violating the window rules
        # lhs is the lowest seq # of un-ack'ed packets
        # rhs is the seq # of the next packet to send
        self.assert_window_integrity()
        return self.window_size - (self.rhs - self.lhs)

    def send(self, seq_number):
        etp = Ethernet(
            src = self.intf.ethaddr,
            dst = self.target_ethaddr
        )
        ip = IPv4(
            protocol = IPProtocol.UDP,
            src = self.intf.ipaddr,
            dst = self.blastee_ip,
            ttl = 64
        )
        pkt = etp + ip + UDP() + seq_number.to_bytes(4, ENDIAN) + \
                self.length_per_blast.to_bytes(2, ENDIAN) + \
                self.blast_content
        try:
            self.net.send_packet(self.intf.name, pkt)
            self.metrics_total_payload_bytes_sent += self.length_per_blast
            if self.metrics_first_sent_time == None:
                self.metrics_first_sent_time = time.time()
        except ValueError as e:
            log_debug("Failed to send packet due to ValueError: {}".format(str(e)))
        except:
            log_debug("Failed to send packet due to unknown error: {}".format(
                sys.exc_info()[0]))

    def process_ack(self, packet):
        contents = packet.get_header(RawPacketContents)
        if contents == None:
            log_debug('Ignored packet of unknown type')
            return
        now = time.time()
        seq_num = int.from_bytes(contents.data[:4], ENDIAN)
        if seq_num < self.lhs or seq_num >= self.rhs:
            log_debug('Ignored out-of-bound ACK')
            return
        log_debug('Received ACK for seq # {}'.format(seq_num))
        self.window[seq_num%self.window_size].ack = True
        self.metrics_last_ack_time = now
        rtt_ms = (now - self.window[seq_num%self.window_size].ts_initial) * 1000
        if self.metrics_min_rtt_ms == None or rtt_ms < self.metrics_min_rtt_ms:
            self.metrics_min_rtt_ms = rtt_ms
        if self.metrics_max_rtt_ms == None or rtt_ms > self.metrics_max_rtt_ms:
            self.metrics_max_rtt_ms = rtt_ms
        # update rtt_to_ms using the EWMA method
        self.est_rtt_ms = (  ((1-self.ewma_alpha)*self.est_rtt_ms)
                               +
                             (self.ewma_alpha*rtt_ms)  )
        self.timeout_ms = 2*self.est_rtt_ms

    def advance_lhs(self):
        # advances lhs if lhs points to a window entry which has been ACK'ed
        #   AND that lhs is less than rhs
        while self.window[self.lhs%self.window_size].ack and self.lhs < self.rhs:
            self.lhs += 1

    def start(self):
        while True:
            if self.should_stop():
                log_info("Stopping - have blasted and ack'ed {} total pkts".\
                        format(self.total_packet_to_blast))
                self.print_metrics()
                return

            self.reblast_unack_pkts()
            self.blast()

            try:
                _, _, pkt = self.net.recv_packet(timeout=self.recv_timeout_ms/1000.0)
            except NoPackets:
                log_debug("No packets available in recv_packet")
                continue
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            self.process_ack(pkt)
            self.advance_lhs()

    def print_metrics(self):
        total_tx_seconds=self.metrics_last_ack_time-self.metrics_first_sent_time
        print("Total TX time (s): " + str(total_tx_seconds))
        print("Number of reTX: " + str(self.metrics_total_retrans))
        print("Number of coarse TOs: " + str(self.metrics_num_timeout))
        print("Throughput (Bps): " + str(self.metrics_total_payload_bytes_sent/total_tx_seconds))
        print("Goodput (Bps): " + \
                str((self.total_packet_to_blast*self.length_per_blast)/total_tx_seconds))
        print("Final estRTT(ms): " + str(self.est_rtt_ms))
        print("Final TO(ms): " + str(self.timeout_ms))
        print("Min RTT(ms):" + str(self.metrics_min_rtt_ms))
        print("Max RTT(ms):" + str(self.metrics_max_rtt_ms))

def main(net):
    b = Blaster(net,"./blaster_params.txt")
    log_debug(b)
    b.start()
    net.shutdown()
