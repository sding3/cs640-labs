import struct

from ipaddress import IPv4Address
from switchyard.lib.userlib import *
from switchyard.lib.packet import *

'''
This test here is to solely test the longest prefix match logic

This test is meant to run with the following forwarding_table.txt as the input, which
  is found in the current working directory.

    172.16.253.0 255.255.255.0 192.168.1.2 router-eth0
    172.16.254.0 255.255.255.0 10.10.1.254 router-eth1
    172.16.255.0 255.255.255.0 172.16.42.2 router-eth2

'''

def mk_pkt(hwsrc, hwdst, ipsrc, ipdst, reply=False, ttl = 64):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=ttl)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt


def router_tests():
    s = TestScenario("Basic functionality testing for DynamicRoutingMessage")

    # Initialize switch with 3 ports.
    s.add_interface('router-eth0', '10:00:00:00:00:01', ipaddr = '192.168.1.1', netmask = '255.255.255.252')
    s.add_interface('router-eth1', '10:00:00:00:00:02', ipaddr = '10.10.0.1', netmask = '255.255.0.0')
    s.add_interface('router-eth2', '10:00:00:00:00:03', ipaddr = '172.16.42.1', netmask = '255.255.255.0')


    packet = mk_pkt(hwsrc = '10:00:00:00:00:03', hwdst =  '30:00:00:00:00:01', ipsrc  = '192.168.1.100', ipdst = '172.16.254.123')

    s.expect(PacketInputEvent("router-eth0", packet), "IP packet to be forwarded to 172.16.254.123  arrives on router-eth0")

    arp_request2  = create_ip_arp_request('10:00:00:00:00:02', '10.10.0.1', '10.10.1.254')

    s.expect(PacketOutputEvent("router-eth1", arp_request2), "Router should send ARP request for 10.10.1.254 out router-eth1 interface")

    return s

scenario = router_tests()
