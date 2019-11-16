'''
Title:          myrouter_part3
Description:    Project 3, part 3 - Add forwarding table updating to Part2
Authors:        David Billmire, Shang Ding
Course:         UWCS 640, Section 2, Fall 2019
'''
import sys
import os
import time

from dynamicroutingmessage import DynamicRoutingMessage
from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *
from switchyard.llnetbase import LLNetBase

'''
Class:          ForwardingTable
Description:    Implements a forwarding table with simple FIFO entry managment
                Includes the following fields:
                    net_prfx - Network prefix number
                    net_mask - Network mask
                    nxt_addr - Next hop IP address
                    nxt_port - Port to forward packets through
                Holds a maximum of <size>+#Local interface routes
'''
class ForwardingTable:
    def __init__(self, net: LLNetBase, size = 5):
        self._net_ = net
        self.table = {}
        self.index = [None for i in range(size)]
        self.i_ptr = 0
        self.size  = size

        #Populate table based on net object
        for intf in net.interfaces():

            net_prfx = IPv4Address(int(intf.ipaddr) & int(intf.netmask))
            network  = "{}/{}".format(net_prfx, intf.netmask)
            mac_addr = intf.ethaddr

            self.add_entry(network, None, mac_addr, True)

    '''
    add_entry
    Adds or updates a new entry to the forwarding table. Maintains a limited table
    of non-local routes, stored in a FIFO index.
    Parameters:
        network     - network+mask string descriptor, ie "172.95.0.0\\16" or "172.95.0.0 255.255.0.0"
        next_hop    - IPv4 address of next hop (if it exists)
        port        - MAC address of the forwarding port for this network
        is_local    - True => entry is from a local port; False otherwise
    '''
    def add_entry(self, network, next_hop, port, is_local):
        log_debug("FT: Add: {}, {}, {}, local: {}".format(str(network), str(next_hop), str(port), is_local))

        net_addr = IPv4Network(network)

        #Update existing table entry
        if net_addr in self.table:
            self.table[net_addr].next_hop = next_hop
            self.table[net_addr].port = port
            return

        #Add new entry
        self.table[net_addr] = ForwardingTable.FTabEntry(
                                    net_addr.network_address,
                                    net_addr.netmask,
                                    next_hop,
                                    port,
                                    is_local
        )

        #Update index and evict old entries if not-local
        #This uses the same logic used for lab1, part 1
        if not is_local:
            if self.index[self.i_ptr] == None:
                self.index[self.i_ptr] = net_addr

            else:
                evict = self.index[self.i_ptr]
                del self.table[evict]
                self.index[self.i_ptr] = net_addr

            self.i_ptr = (self.i_ptr + 1) % self.size

    '''
    lookup_route
    Finds a route for a packet. If a route can be found,
    return the port and the IP address of the next hop
    If the packet is already at its destination or no
    route can be found, return None
    '''
    def lookup_route(self, ip_head: IPv4):

        #Get matching networks, sorted by prefix length larget > small
        networks = sorted(
                        filter(
                            lambda x: ip_head.dst in x,
                            self.table.keys()
                        ),
                        key=lambda x: x.prefixlen,
                        reverse=True
        )

        if len(networks) > 0:
            port = self.table[networks[0]].nxt_port
            addr = self.table[networks[0]].nxt_addr
            if addr == None: addr = ip_head.dst         #Local destination
            return port, addr

        return None

    '''
    load_file
    Loads a file of forwarding table information
    Parameters:
        filename    - name of the file to load
    '''
    def load_file(self, filename):
        log_debug("FT: Load: {}".format(filename))

        try:          
            fh = open(filename, 'r')
            for line in fh.readlines():
                line   = line.strip()
                fields = line.split()
                if (len(fields) != 4):  continue
                network  = fields[0] + "/" + fields[1]
                next_hop = IPv4Address(fields[2])
                intf     = self._net_.interface_by_name(fields[3])
                mac_addr = intf.ethaddr

                self.add_entry(network, next_hop, mac_addr, False)
                fh.close()
        except:
            log_debug("Failed to load table file {}: {}".format(filename, sys.exc_info()))

    '''
    Class:          FTabEntry
    Description:    Entry in the forwarding table
    '''
    class FTabEntry:
        def __init__(
                self,
                net_prfx: IPv4Address,
                net_mask: IPv4Address,
                nxt_addr: IPv4Address,
                nxt_port: EthAddr,
                is_local
        ):

            self.net_prfx = net_prfx
            self.net_mask = net_mask
            self.nxt_addr = nxt_addr
            self.nxt_port = nxt_port
            self.is_local = is_local
#end class ForwardingTable

'''
Class:          ARPContext
Description:    Implements basic ARP functions, including IP to MAC translation and table management
                ARP Context is iterable and supports direct get/set of IPv4 -> MAC mapping
'''
class ARPContext:
    def __init__(self):
        self.map   = {}

    def __iter__(self):
        return iter(self.map)

    def __getitem__(self, item):
        if item in self.map and isinstance(self.map[item], ARPContext.ARPEntry):
            return self.map[item].mac_addr
        else:
            return None

    def __setitem__(self, ip_addr, mac_addr):
        self.add_mapping(ip_addr, mac_addr)

    '''
    add_mapping
    Add or updates an IP to MAC address mapping
      ip_addr      IPv4Address
      mac_addr     EthAddr
    '''
    def add_mapping(self, ip_addr, mac_addr):
        if isinstance(ip_addr, IPv4Address) and isinstance(mac_addr, EthAddr):
            self.map[ip_addr] = ARPContext.ARPEntry(mac_addr)

    '''
    handle_arp_request
    Process an ARP requests in the provided packet. Return a reply packet
    if the target IP address is in our table
       arp_head         Arp packet header to process
    Returns an ARP reply packet
    '''
    def handle_arp_request(self, arp_head: Arp):
        reply_ip  = arp_head.targetprotoaddr
        reply_mac = self.map[reply_ip].mac_addr

        #Construct reply packet
        etp = Ethernet(
                    ethertype = EtherType.ARP,
                    src       = reply_mac,
                    dst       = arp_head.senderhwaddr
        )

        arp = Arp(
                operation       = ArpOperation.Reply,
                senderhwaddr    = reply_mac,
                senderprotoaddr = reply_ip,
                targethwaddr    = arp_head.senderhwaddr,
                targetprotoaddr = arp_head.senderprotoaddr
        )

        return_pkt = etp + arp
        return return_pkt

    '''
    handle_arp_reply
    Process an ARP reply in the provided packet.
       arp_head         Arp packet header to process
    '''
    def handle_arp_reply(self, arp_head: Arp):
        self.add_mapping(arp_head.senderprotoaddr, arp_head.senderhwaddr)

    '''
    get_arp_request
    Generate an ARP request packet
      target_addr       Target IP address
      intf              Outoing interface
    Returns a new Arp reqeust packet
    '''
    def get_arp_request(self, target_addr: IPv4, intf: Interface):

        arp_head = Arp(
                    operation       = ArpOperation.Request,
                    senderhwaddr    = intf.ethaddr,
                    senderprotoaddr = intf.ipaddr,
                    targetprotoaddr = target_addr
        )

        eth_head = Ethernet(
                        ethertype = EtherType.ARP,
                        src       = intf.ethaddr,
                        dst       = SpecialEthAddr.ETHER_BROADCAST.value
        )

        return_pkt = eth_head + arp_head
        return return_pkt

    '''
    Class:          ARPContext.ArpEntry
    Description:    Table entry pairing a timestamp with a MAC address
    '''
    class ARPEntry:
        def __init__(self, mac_addr, timestamp = None):
            self.mac_addr   = mac_addr
            if timestamp == None:
                self.timestamp = time.time()
            else:
                self.timestamp = timestamp
# end class ARPContext

'''
Class:              Router
Description:        Simulated IPv4 Router. Currently handles static packet forwarding and ARP lookup
'''
class Router(object):
    def __init__(self, net: LLNetBase):
        self.net = net
        self.local_proto_eth = ARPContext()             #Local address maps
        self.other_proto_eth = ARPContext()             #Other address maps
        self.forwarding_table = ForwardingTable(net)    #Forwarding table

        self.my_ips = [intf.ipaddr for intf in net.interfaces()]     #Local IPs

        #Load context-provided forwarding table info
        self.forwarding_table.load_file("forwarding_table.txt")

        #Cache IP->MAC mapping for local interfaces
        for intf in net.interfaces():
            self.local_proto_eth[intf.ipaddr] = intf.ethaddr

    #Main Router loop
    def router_main(self):
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''
        self.queue = []          #Packet waiting queue
        self.index = {}          #Packet waiting index

        while True:

            #Process any waiting packets
            self.dequeue_packets()

            #Get and handle any new packets
            try:
                _, input_port, pkt = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                log_debug("No packets available in recv_packet")
                continue
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            log_debug("Got a packet: {}".format(str(pkt)))

            if pkt.has_header(Arp):
                self.handle_arp(pkt, input_port)
            elif pkt.has_header(IPv4):
                self.handle_ipv4(pkt)
            elif pkt.has_header(DynamicRoutingMessage):
                self.handle_DRM(pkt, input_port)
            else:
                log_debug("Packet is of unsupported format: {}".format(str(pkt)))

    #end Main Router loop

    '''
    handle_DRM
    Handles a Dynamic Routing Message in a packet (if one exists)
    Updates the forwarding table based onthe DRM contents
      pkt        Packet to handle
      input_port Name of the interface the packet arrived on
    '''
    def handle_DRM(self, pkt: Packet, input_port):
        drm_head = pkt.get_header(DynamicRoutingMessage)
        if not isinstance(drm_head, DynamicRoutingMessage): return
        log_debug("R: Handle DRM: {}".format(pkt))

        #Add/Update the route
        network = "{}/{}".format(drm_head.advertised_prefix, drm_head.advertised_mask)
        port_intf = self.net.interface_by_name(input_port)

        self.forwarding_table.add_entry(network, drm_head.next_hop, port_intf.ethaddr, False)

    '''
    handle_ipv4
    Handles an IPv4 header in the packet (if one exists)
    Attempts to forward the packet based on the existing routing table
    Requests MAC addresses using ARP if necessary
      pkt       Packet to handle
    '''
    def handle_ipv4(self, pkt: Packet):

        ip_head = pkt.get_header(IPv4)
        if not isinstance(ip_head, IPv4): return
        log_debug("R: Handle IPv4: {}".format(pkt))

        #Drop packet if this port is its destination
        if ip_head.dst in self.my_ips: return

        #Lookup forwarding info. If no dest MAC is known, sidetrack and send ARP
        port, addr = self.forwarding_table.lookup_route(ip_head)
        log_debug("Type of Port: {}\nType of Addr: {}".format(type(port), type(addr)))

        if (isinstance(port, EthAddr) and isinstance(addr, IPv4Address)):
            if addr in self.other_proto_eth:
                self.forward_ipv4(pkt, port, self.other_proto_eth[addr])

            else:
                self.enqueue_packet(pkt, port, addr)

    '''
    forward_ipv4
    Forwards an IPv4 packet to a new destination through a specific port
      pkt       Packet to forward (Ethernet header will be replaced)
      out_port  Output port
      dst_mac   Destination MAC
    '''
    def forward_ipv4(self, pkt: Packet, out_port: EthAddr, dst_mac: EthAddr):

        #Create new Ethernet Header
        del pkt[0]
        eth_head = Ethernet(src=out_port, dst=dst_mac, ethertype=EtherType.IPv4)
        pkt.prepend_header(eth_head)

        #Decrement TTL
        pkt[IPv4].ttl -= 1

        out_interface = self.net.interface_by_macaddr(out_port)
        self.send_packet(pkt, out_interface.name)

    '''
    handle_arp
    Handles an ARP header in the packet (if one exists)
    Sends an ARP reply to requests that can be serviced
    Updates the ArpContext table for replies to earlier requests
      pkt           Packet to handle
      input_port    port the packet arrived from
    '''
    def handle_arp(self, pkt: Packet, input_port):

        arp_head = pkt.get_header(Arp)
        if not isinstance(arp_head, Arp): return

        if arp_head.targetprotoaddr in self.local_proto_eth:
            if arp_head.operation == ArpOperation.Request:
                self.send_packet(self.local_proto_eth.handle_arp_request(arp_head), input_port)
                return None

            elif arp_head.operation == ArpOperation.Reply:
                return self.other_proto_eth.handle_arp_reply(arp_head)

            else:
                log_debug("Unknown ARP header operation: {}".format(str(arp_head)))

    '''
    send_packet
    Sends a packet through a port
      pkt       Packet to send
      port      Port (interface name) to send the packet through
    '''
    def send_packet(self, pkt, output_port):
        if not isinstance(pkt, Packet):
            log_debug("send_packet called with invalid packet: {}".format(pkt))
            return

        ports = [ intf.name for intf in self.net.interfaces() ]
        if not output_port in ports:
            log_debug("send_packet called with unknown port: {}".format(output_port))
            return

        log_debug("R: Send Packet: {} on {}".format(str(pkt), output_port))

        try:
            self.net.send_packet(output_port, pkt)
        except ValueError as e:
            log_debug("Failed to send packet. Got ValueError: {}".format(e))
        except:
            log_debug("Failed to send packet. Unknown Error: {}".format(sys.exc_info()))

    '''
    enqueue_packet
    Side-tracks a packet until its destination IP can be resolved to a MAC
    Generates and sends an ARP requests, then places the packet on a queue
      pkt           Packet
      port          Output port
      addr          Destination IPv4 addr
    '''
    def enqueue_packet(self, pkt: Packet, port: EthAddr, addr: IPv4Address):
        #Enqueue the packet to be sent later
        self.queue.append(Router.QueuedPacket(pkt, port, addr))

        #Add to index if necessary
        if addr not in self.index:
            self.index[addr] = (0, time.time()-2)

    '''
    dequeue_packets
    Evaluates side-tracked packets. Sends packets with resolvable destinations.
    For packets still waiting for destinations, sends up to 2 additional ARP requests
    Drops packets after 3 ARP requests.
    '''
    def dequeue_packets(self):
        now = time.time()
        log_debug("Queue length: {}".format(len(self.queue)))
        for queued_pkt in self.queue:
            log_debug("Trying to dequeue: {}".format(queued_pkt))
            addr = queued_pkt.addr
            arps = self.index[addr][0]
            last = self.index[addr][1]
            if addr in self.other_proto_eth:
                #Send packet
                self.forward_ipv4(
                            queued_pkt.packet,
                            queued_pkt.port,
                            self.other_proto_eth[addr]
                )

                self.queue.remove(queued_pkt)

            #Send another ARP if fewer than 3 ARPs have been sent and at least 1 second has passed
            elif now-last < 1:
                continue
            elif arps < 3:

                out_interface = self.net.interface_by_macaddr(queued_pkt.port)
                arp_pkt = self.local_proto_eth.get_arp_request(addr, out_interface)

                self.send_packet(arp_pkt, out_interface.name)

                self.index[addr] = (arps+1, now)

            else:
                #Give up
                self.queue.remove(queued_pkt)
                del self.index[addr]

    '''
    Class:          QueuedPacket
    Description:    Datastructure for tracking sidetracked packets
    '''
    class QueuedPacket:
        def __init__(self, pkt: Packet, port: EthAddr, addr: IPv4Address, timestamp = None):
            self.packet = pkt
            self.addr   = addr
            self.port   = port
            self.arps   = 1

            if timestamp == None:
                self.time = time.time()
            else:
                self.time = timestamp

#end class Router

def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
