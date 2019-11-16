import struct

from ipaddress import IPv4Address
from switchyard.lib.userlib import *
from switchyard.lib.packet import *

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


    # 1   IP packet to be forwarded to 172.16.42.2 should arrive on
    #     router-eth0
    #         Expected event: recv_packet Ethernet
    #         10:00:00:00:00:03->30:00:00:00:00:01 IP | IPv4
    #         192.168.1.100->172.16.42.2 ICMP | ICMP EchoRequest 0 42 (0
    #         data bytes) on router-eth0

    packet = mk_pkt(hwsrc = '10:00:00:00:00:03', hwdst =  '30:00:00:00:00:01', ipsrc  = '192.168.1.100', ipdst = '172.16.42.2')
    s.expect(PacketInputEvent("router-eth0", packet), "IP packet to be forwarded to 172.16.42.2 should arrive on router-eth0")

    # 2 to 6
    #     Router should send ARP request for 172.16.42.2 out router-
    #     eth2 interface for a total of 3 times
    #         Expected event: send_packet(s) Ethernet
    #         10:00:00:00:00:03->ff:ff:ff:ff:ff:ff ARP | Arp
    #         10:00:00:00:00:03:172.16.42.1 ff:ff:ff:ff:ff:ff:172.16.42.2
    #         out router-eth2
    # 2 - assert the firing of the 1st ARP request
    # 3 - wait for 1 second
    # 4 - assert the firing of the 2nd ARP request
    # 5 - wait for 1 second
    # 6 - assert the firing of the 3rd ARP request


    arp_request2  = create_ip_arp_request('10:00:00:00:00:03', '172.16.42.1', '172.16.42.2')
    s.expect(PacketOutputEvent("router-eth2", arp_request2), "Router should send ARP request for 172.16.42.2 out router-eth2 interface")

    s.expect(PacketInputTimeoutEvent(1.0), "Waiting 1.0 seconds")
    s.expect(PacketOutputEvent("router-eth2", arp_request2), "Router should send 2nd ARP request for 172.16.42.2 out router-eth2 interface")

    s.expect(PacketInputTimeoutEvent(1.0), "Waiting 1.0 seconds")
    s.expect(PacketOutputEvent("router-eth2", arp_request2), "Router should send 3rd ARP request for 172.16.42.2 out router-eth2 interface")

    # 7
    #     A long wait to expire the ARP request attempt for 172.16.42.2
    s.expect(PacketInputTimeoutEvent(3.0), "Waiting 3.0 seconds to let things settle")

    # 8 to 17
    #     Essentially a repeat of the above test cases 1 to 6
    #     with the difference being that these test cases test the router's handling of two concurrent sets of ARP requests:
    #       172.16.42.2 and 10.10.0.2
    packet = mk_pkt(hwsrc = '10:00:00:00:00:03', hwdst =  '30:00:00:00:00:01', ipsrc  = '192.168.1.100', ipdst = '172.16.42.2')
    s.expect(PacketInputEvent("router-eth0", packet), "IP packet to be forwarded to 172.16.42.2 should arrive on router-eth0")
    arp_request2  = create_ip_arp_request('10:00:00:00:00:03', '172.16.42.1', '172.16.42.2')
    s.expect(PacketOutputEvent("router-eth2", arp_request2), "Router should send ARP request for 172.16.42.2 out router-eth2 interface")

    packet = mk_pkt(hwsrc = '10:00:00:00:00:02', hwdst =  '30:00:00:00:00:01', ipsrc  = '192.168.1.100', ipdst = '10.10.0.2')
    s.expect(PacketInputEvent("router-eth1", packet), "IP packet to be forwarded to 10.10.0.2 should arrive on router-eth1")
    arp_request1  = create_ip_arp_request('10:00:00:00:00:02', '10.10.0.1', '10.10.0.2')
    s.expect(PacketOutputEvent("router-eth1", arp_request1), "Router should send ARP request for 10.10.0.2 out router-eth1 interface")

    s.expect(PacketInputTimeoutEvent(1.0), "Waiting 1.0 seconds")
    s.expect(PacketOutputEvent("router-eth2", arp_request2), "Router should send 2nd ARP request for 172.16.42.2 out router-eth2 interface")

    s.expect(PacketOutputEvent("router-eth1", arp_request1), "Router should send 2nd ARP request for 10.10.0.2 out router-eth1 interface")

    s.expect(PacketInputTimeoutEvent(1.0), "Waiting 1.0 seconds")

    s.expect(PacketOutputEvent("router-eth2", arp_request2), "Router should send 3rd ARP request for 172.16.42.2 out router-eth2 interface")

    s.expect(PacketOutputEvent("router-eth1", arp_request1), "Router should send 3rd ARP request for 10.10.0.2 out router-eth1 interface")


    # 18   Router should receive ARP response for 172.16.42.2 on
    #     router-eth2 interface
    #         Expected event: recv_packet Ethernet
    #         30:00:00:00:00:01->10:00:00:00:00:03 ARP | Arp
    #         30:00:00:00:00:01:172.16.42.2 10:00:00:00:00:03:172.16.42.1
    #         on router-eth2

    arp_response = create_ip_arp_reply('30:00:00:00:00:01', '10:00:00:00:00:03',
                                       '172.16.42.2', '172.16.42.1')
    s.expect(PacketInputEvent("router-eth2", arp_response), "Router should receive ARP response for 172.16.42.2 on router-eth2 interface")


    # 19   IP packet should be forwarded to 172.16.42.2 out router-eth2
    #         Expected event: send_packet(s) Ethernet
    #         10:00:00:00:00:03->30:00:00:00:00:01 IP | IPv4
    #         192.168.1.100->172.16.42.2 ICMP | ICMP EchoRequest 0 42 (0
    #         data bytes) out router-eth2

    packet = mk_pkt(hwsrc='10:00:00:00:00:03', hwdst='30:00:00:00:00:01', ipsrc='192.168.1.100', ipdst='172.16.42.2', ttl=63)
    s.expect(PacketOutputEvent("router-eth2", packet), "IP packet should be forwarded to 172.16.42.2 out router-eth2")

    return s

scenario = router_tests()
