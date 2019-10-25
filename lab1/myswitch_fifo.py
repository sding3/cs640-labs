import sys
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
        if intf.name != skip:
            log_debug("Flooding packet {} to {}".format(packet, intf.name))
            safe_send_packet(net, intf.name, pkt)


def main(net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]
    forwarding_table = ForwardingTable()

    while True:
        try:
            _, input_port, packet = net.recv_packet()
        except NoPackets:
            log_debug("No packets received!")
            continue
        except Shutdown:
            log_debug("Received signal for shutdown!")
            return

        forwarding_table.update(packet[0].src, input_port)

        log_debug("In {} received packet {} on {}".format(
            net.name, packet, input_port))

        # drop packet intended for me
        if packet[0].dst in mymacs:
            log_debug("Packet intended for me")
            continue

        # packet's destination found in forwarding table - send it
        if packet[0].dst in forwarding_table:
            safe_send_packet(net, forwarding_table[packet[0].dst], packet)
            continue

        # packet's destination not found in forwarding table, or the destination
        # is the broadcast addrress - broadcast it either way
        broadcast(net, my_interfaces, input_port, packet)

    net.shutdown()
