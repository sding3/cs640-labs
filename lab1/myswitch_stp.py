import sys
import time
from datetime import datetime

import SpanningTreeMessage as STM
from switchyard.lib.userlib import *


def isBroadcast(addr):
    return SpecialEthAddr.ETHER_BROADCAST.value == addr


class ForwardingTable:
    def __init__(self, size=5):
        self.array = [None for i in range(size)]
        self.pos = 0
        self.size = size
        self.map = {}
        return

    def __iter__(self):
        return iter(self.map)

    def __getitem__(self, item):
        return self.map[item]

    def update(self, addr, port):
        """ If addr is the broadcast addr, then do nothing.
        If addr is already in map, we set it again
        without changing anything else, (as the port may
        have changed).
        If addr not in map, we update ForwardingTable in
        a fifo manner, e.g. if we have a vacant spot, we
        will just add the new addr/port pair; otherwise,
        if we do not have a vacancy, we'll need to evict
        the oldest item from the ForwardingTable, then add
        the new item
        """
        if isBroadcast(addr):
            return

        if addr in self.map:
            self.map[addr] = port
            return

        self.map[addr] = port
        if self.array[self.pos] == None:
            self.array[self.pos] = addr
        else:
            evict = self.array[self.pos]
            del self.map[evict]
            self.array[self.pos] = addr

        self.pos = (self.pos + 1) % self.size

        return


class SpanningTreeContext:
    def __init__(self, my_id):
        """ switches assume they're the root node upon startup
        """
        self.my_id = EthAddr(my_id)
        self.root_id = EthAddr(my_id)
        self.hops_from_root = 0
        self.time_last_spm_tx = None
        """ Non-root mode properties
        """
        # rx interface from where the STM of the perceived root came
        self.root_interface = None
        # ID of the switch connected to the root_interface
        self.root_switch_id = None
        self.blocked_interfaces = set()
        self.time_last_spm_rx = None
        log_debug("{} became root".format(self.my_id))

    def am_root(self):
        return self.my_id == self.root_id

    def become_root(self):
        self.__init__(my_id=self.my_id)

    def set_root(self, new_root_id):
        self.root_id = EthAddr(new_root_id)
        log_debug("{} set {} as the new root".format(self.my_id, new_root_id))

    def block(self, blockee):
        if self.am_root():
            log_debug("{}, the root, ignored request to block {}".format(
                self.my_id, blockee))
            return
        self.blocked_interfaces.add(blockee)
        log_debug("{} blocked {}".format(self.my_id, blockee))

    def unblock(self, unblockee):
        if unblockee in self.blocked_interfaces:
            self.blocked_interfaces.remove(unblockee)
            log_debug("{} unblocked {}".format(self.my_id, unblockee))

    def __str__(self):
        return "SpanningTreeContext - root: {}, blocked: {}".format(
            self.am_root(), self.blocked_interfaces)


def emit_stm(net, interfaces, stp_context):
    """ If am the root node and it's been 2 seconds since the last STM tx
    then send STM out; else if am not the root and I have not seen any STM
    packets in 10 seconds, I become the root.
    """
    now = datetime.now()
    if stp_context.am_root():
        if stp_context.time_last_spm_tx == None or \
                (now - stp_context.time_last_spm_tx).seconds >= 2:

            spm = STM.SpanningTreeMessage(root_id=stp_context.my_id,
                                          switch_id=stp_context.my_id)
            for intf in interfaces:
                pkt = Ethernet(src=intf.ethaddr,
                               dst="ff:ff:ff:ff:ff:ff",
                               ethertype=EtherType.SLOW) + spm
                safe_send_packet(net, intf.name, pkt)
                log_debug("{} emitted STM on {}: {}".format(
                    stp_context.my_id, intf.name, pkt))

            stp_context.time_last_spm_tx = datetime.now()

    else:
        if stp_context.time_last_spm_rx == None or \
                (now - stp_context.time_last_spm_rx).seconds >= 10:

            stp_context.become_root()


def handle_stm(net, interfaces, stp_context, pkt, incoming_interface):
    stp_context.time_last_spm_rx = datetime.now()
    log_debug("{} received STM on {}: {}".format(stp_context.my_id,
                                                 incoming_interface, pkt))
    stm = STM.SpanningTreeMessage()
    b = pkt[1].to_bytes()
    stm.from_bytes(b)
    log_debug("STM: {}".format(stm))
    stm.hops_to_root += 1

    def update_info_as_described_in_point_4_and_forward_STP():
        stp_context.set_root(stm.root)
        stp_context.root_interface = incoming_interface
        stp_context.unblock(incoming_interface)
        stp_context.root_switch_id = stm.switch_id
        stp_context.hops_from_root = stm.hops_to_root
        stm.switch_id = stp_context.my_id
        for intf in interfaces:
            if intf.name == incoming_interface:
                continue
            pkt = Ethernet(src=intf.ethaddr,
                           dst=SpecialEthAddr.ETHER_BROADCAST.value,
                           ethertype=EtherType.SLOW) + stm
            safe_send_packet(net, intf.name, pkt)

    # If (incoming_interface is same as root_interface) or (the root ID in
    # the received packet is smaller than the ID that the node currently thinks
    # is the root), then switch updates its information(as described in point
    # 4) and forwards the STP packets taking information update into account.
    if incoming_interface == stp_context.root_interface or \
            stm.root < stp_context.root_id:
        update_info_as_described_in_point_4_and_forward_STP()
        return

    # If the root ID in the received packet is greater than the id of that
    # node, then remove incoming_interface from the list of blocked interfaces
    if stm.root > stp_context.my_id:
        stp_context.unblock(incoming_interface)
        return

    # If the root ID in the received packet is the same as the id that the node
    # currently thinks is the root, we examine # of hops to root:
    #
    #   (If the number of hops to the root + 1 is less than the value that the
    #   switch has stored ) or (If the number of hops to the root + 1 is equal
    #   to the value that the switch has stored and the root_switch_id is greater
    #   than the switch_id of the packet):
    #     1. switch removes the incoming_interface from the list of blocked ones
    #     2. block the original root_interface and update root_interface to
    #        incoming_interface
    #     3. updates ohter information as described in point 4
    #     4. forwards the STP packets taking information update into account.
    #
    #   otherwise:
    #     block the incoming interface
    if stm.root == stp_context.root_id:
        if stm.hops_to_root < stp_context.hops_from_root or \
                (stm.hops_to_root == stp_context.hops_from_root and \
                stp_context.root_switch_id > stm.switch_id):
            stp_context.unblock(incoming_interface)
            stp_context.block(stp_context.root_interface)
            update_info_as_described_in_point_4_and_forward_STP()
        else:
            stp_context.block(incoming_interface)
        return

    return


def safe_send_packet(net, intf_name, pkt):
    try:
        net.send_packet(intf_name, pkt)
    except ValueError as e:
        log_debug("Failed to send packet due to ValueError: {}".format(str(e)))
    except:
        log_debug("Failed to send packet due to unknown error: {}".format(
            sys.exc_info()[0]))


def broadcast(net, egresses, skip, pkt):
    for intf in egresses:
        if intf.name not in skip:
            log_debug("Flooding packet {} to {}".format(packet, intf.name))
            safe_send_packet(net, intf.name, pkt)


def main(net):
    Ethernet.add_next_header_class(EtherType.SLOW, STM)
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]
    forwarding_table = ForwardingTable()

    mymacs.sort()
    stp_context = SpanningTreeContext(mymacs[0])

    while True:
        emit_stm(net, my_interfaces, stp_context)

        log_debug(stp_context)

        try:
            _, input_port, packet = net.recv_packet(timeout=1)
        except NoPackets:
            log_debug("No packets received!")
            continue
        except Shutdown:
            log_debug("Received signal for shutdown!")
            return

        log_debug("In {} received packet {} on {}".format(
            net.name, packet, input_port))

        # code path to soley handling STM packets
        if packet[0].ethertype == EtherType.SLOW:
            handle_stm(net, my_interfaces, stp_context, packet, input_port)
            continue

        forwarding_table.update(packet[0].src, input_port)

        # drop packet intended for me
        if packet[0].dst in mymacs:
            log_debug("Packet intended for me")
            continue  # do nothing

        # packet's destination found in forwarding table - send it
        if packet[0].dst in forwarding_table:
            safe_send_packet(net, forwarding_table[packet[0].dst], packet)
            continue

        # packet's destination not found in forwarding table, or the destination
        # is the broadcast addrress - broadcast it either way
        broadcast(net=net,
                  egresses=my_interfaces,
                  skip=stp_context.blocked_interfaces.union({input_port}),
                  pkt=packet)

    net.shutdown()
