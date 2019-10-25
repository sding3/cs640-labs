[Lab-Assignment-1](https://canvas.wisc.edu/courses/155029/assignments/666969)

> # Lab-Assignment-1
> 
> -   Due Friday by 11:59pm
> -   Points 50
> -   Submitting a file upload
> -   Available after Oct 7 at 12am
> 
> **Due:** 10/25/2019
> 
> **For your questions:** thumbe at wisc dot edu
> 
> ## **Overview**
> 
> In this assignment, you are going to implement the core functionalities of an Ethernet learning switch with Spanning Tree using the [Switchyard framework (Links to an external site.)](https://github.com/jsommers/switchyard). An Ethernet switch is a layer 2 device that uses packet switching to receive, process and forward frames to other devices (end hosts, other switches) in the network. A switch has a set of interfaces (ports) through which it sends/receives Ethernet frames. When Ethernet frames arrive on any port, the switch will process the header of the frame to obtain information about the destination host. If the switch knows that the host is reachable through one of its ports, it sends out the frame from the appropriate output port. If it does not know where the host is, it floods the frame out of all ports except the input port.
> 
> Spanning Tree (or STP) is a network protocol in Ethernet used to prevent broadcast storms, by converting a physical loop into a logical loop-free topology. This is done by electing a root port in the topology and designating ports as forwarding or blocking, depending on the proximity to the root switch.
> 
> ## **Details**
> 
> ### **Part 1: Learning Switch**
> 
> Your task is to implement the logic that is described in the flowchart [here (Links to an external site.)](https://github.com/jsommers/switchyard/blob/master/examples/exercises/learning_switch/learning_switch.rst#ethernet-learning-switch-operation).. A more elaborate flowchart has been described in the FAQ section. As it is described in the last paragraph of the "Ethernet Learning Switch Operation" section, your switch will also handle the frames that are intended for itself and the frames whose Ethernet destination address is the broadcast address FF:FF:FF:FF:FF:FF.
> 
> In addition to these, you will also implement a mechanism to purge the outdated/stale entries from the forwarding table. This will allow your learning switch to adapt to changes in the network topology.
> 
> You will implement the following mechanism in a Python file named **myswitch_fifo.py**:
> 
> -   Remove the entry from the forwarding table using the FIFO (First In First Out) policy. For this functionality assume that your table can only hold 5 entries at a time. If a new entry comes and your table is full, you will remove the entry that was been put first in the switch’s mac-learning table. FIFO policy would solely depend on the source mac address of the packet and the destination mac address of the packet would play no role.
> 
> **NOTE**: There is an example of a switch without learning implemented in  switchyard-master/examples/exercises/learning_switch/ which will likely be useful to get you started.
> 
> **Also please keep an eye on the FAQ section below which will be updated with information regarding the most common issues that arise during implementation.**
> 
> ### **Part 2: Spanning Tree implementation**
> 
> Helper code can be downloaded [here](https://canvas.wisc.edu/courses/155029/files/9657679/download) (SpanningTreeMessage.py). For the second part of the assignment you will build on top of your learning switch implementation. STP packets will be handled in a separate code path whereas the other packets will continue as per the behavior of the learning switch. Create a copy of the above file and name it as **myswitch_stp.py.** You will be implementing a simplified version of the Spanning Tree Protocol for the purpose of this assignment. The problem description has been modified from [here (Links to an external site.)](https://github.com/jsommers/switchyard/blob/master/examples/exercises/learning_switch/learning_switch.rst#implement-a-simplified-spanning-tree-computation-algorithm) to suite our requirements as described below. (**NOTE:** This is not the actual STP working but a simplified version which can be implemented within the restrictions of the framework capabilities.)
> 
> If you attempt to run your switch on multiple nodes within a virtual network using Mininet, and if there is a physical _loop_ in the network, you will observe that packets will circulate infinitely. Oops. An interesting and challenging extension to the learning switch is to implement a simplified spanning tree computation algorithm. Once the spanning tree is computed among switches in the network, traffic will only be forwarded along links that are part of the spanning tree, thus eliminating the loop and preventing packets from circulating infinitely.
> 
> To implement a spanning tree computation, you'll need to do the following:
> 
> 1.  Add to your switch the notion of an _id_, which can just be an integer (or even a string). The point is that each switch will need its own unique id, and there should be a simple way to compare ids. (**NOTE:** For our implementation the ID of the switch will be equal to the smallest MAC address among all it’s ports MAC addresses.)
> 2.  Create a new packet header type that includes three attributes: the id of the _root_ node in the spanning tree, the number of observed hops to the root, and the id of the switch that forwards the spanning tree packet (**NOTE**: For this part of the assignment you can refer to API example given [here (Links to an external site.)](https://jsommers.github.io/switchyard/advanced_api.html#one-more-example). Also note that (root id = switch id) when the message is generated at the root. 
> 3.  The implementation has been packaged and given in the starter code under **spanningtreemessage.py**. Just import that in your myswitch_stp.py). The source MAC in the Ethernet header can be anything as we are not going to learn any MAC table information from STP packets but the destination MAC should be broadcast address (“ff:ff:ff:ff:ff:ff”).
> 4.  Add a capability to each switch so that when it starts up, it floods out spanning tree packets to determine and/or find out what node is the root. Each switch needs to store a few things: the id of the current root (which is initialized to the switch's own id), the number of hops to the root (initialized to 0), and the time at which the last spanning tree message was received. Each non-root node also needs to remember
> 
> 1.  the interface on which spanning tree message from the perceived root arrives  => **_root_interface_**
> 2.  ID of the switch connected to the **_root_interface_** =\> **_root\_switch\_id_**
> 3.  The information that which ports are blocked.
> 4.  The time at which the last spanning tree message was received
> 
> 6.  Let’s call the interface through which STP message is received => **_incoming_interface_**
> 7.  Only root nodes generate STP packets periodically. Initially, a node assumes that it is the root. These packets (root\_id, number of hops, switch id)  are initialized as (switch\_id, 0, switch id). The root node should emit new spanning tree packets every 2 seconds. Once a node gets to know that it is not the root, it should stop generating spanning tree messages
> 8.  When a node receives a spanning tree packet it examines the interface through which the message was received and the root attribute of the packet. 
>     1.  ( If the number of hops to the root + 1 is less than the value that the switch has stored )  or (If the number of hops to the root + 1 is equal to the value that the switch has stored and the **_root\_switch\_id_** is greater than the switch_id of the packet), then 
>     
>     1.  switch removes the **_incoming_interface_** from the list of blocked interfaces( if present), block the original **_root_interface_** and update **_root_interface_** = **_incoming_interface_** and other relevant information(as described in point 4). Finally  forward the STP packets taking the information update into account.
>     
>     3.  Otherwise block the **_incoming_interface_**  
>           
>         
> 
> 1.  If **_incoming_interface_** is same as **_root_interface_** or the root ID in the received packet is _smaller_ than the ID that the node currently thinks is the root, the switch updates its information(as described in point 4) and forwards the STP packets taking information update into account.
> 2.  If the root ID in the received packet is greater than the id of that node, then remove **_incoming_interface_** from the list of blocked interfaces ( if present ).
> 3.  If the id in the received packet is _the same_ as the id that the node currently thinks is the root, it examines the number of hops to the root value:
> 
> 10.  If a non root node doesn’t receive STP messages for more than 10 seconds, then re-initialize the root id to switch’s own id, hop count to 0 and remove all interfaces from the set of blocking interfaces.
> 11.  Lastly, the learning switch forwarding algorithm changes a bit in the context of a spanning tree. Instead of flooding a frame with an unknown destination Ethernet address out _every_ port (except the one on which the frame was received), a switch only floods a frame out every port except the input port and the ports corresponding to the set of interfaces that are blocked.
> 
> ## **Testing your code**
> 
> Once you develop your learning switch, you should test the correctness of your implementation. Switchyard allows you to write scenarios to test your implementation. You can find more detailed information on creating test scenarios [here (Links to an external site.)](https://cs.colgate.edu/~jsommers/switchyard/2017.01/test_scenario_creation.html). You can also find a simple test scenario in switchyard/examples/hubtests.py. Once you understand and get comfortable with the framework, make sure that you test your switch implementations meticulously. Do not forget to consider corner cases. Make sure that your entry purging mechanisms work as expected.
> 
> Once you prepare your test scenario, you can compile it as follows:
> 
> ./swyard.py -c mytestscenario.py
> 
> To run the test scenario with your switch implementation:
> 
> ./swyard.py -t mytestscenario.srpy myswitchimplementation.py
> 
> You can find more detailed information on compiling test scenarios and running in the test environment in the Switchyard documentation.
> 
> **_(Optional)_** In addition to these, you should also try running your switch in Mininet. You can find more information on this [here (Links to an external site.)](https://github.com/jsommers/switchyard/blob/master/examples/exercises/learning_switch/learning_switch.rst#testing-and-deploying-your-switch).
> 
> **NOTE:** FIFO implementation can be tested using the compiled code. But for testing the STP implementation directly pass the python file.
> 
> ./swyard.py -t testfile.py myswitch_stp.py
> 
> ## **Test Scenarios**
> 
> You can find example test scenarios here.
> 
> ### _[**Myswitchfifo_test**.**srpy**](https://canvas.wisc.edu/courses/155029/files/9798883/download "Link")_ \- compiled test file for testing fifo implementation
> 
> ### [**_Myswitchstp_test.py_**](https://canvas.wisc.edu/courses/155029/files/9657503/download?wrap=1) \- test file for testing stp algorithm
> 
> Note that these tests are not comprehensive and are provided to help you debug simple issues. We will be running additional tests for grading your assignment.
> 
> ## **Handing it in**
> 
> You will submit a **.tar.gz** file that will include:
> 
> -   **SpanningTreeMessage.py:** Already provided. Leave it as is
> -   **myswitch_fifo.py**: Your learning switch with FIFO based entry removal
> -   **myswitch_stp.py**: Your learning switch with spanning tree implementation and FIFO code
> -   **README** : Has name and netid of your partner. Only one of the group members should  submit the assignment. 
> 
> **IMPORTANT:** The file names in your submission package has to **exactly match the file names above**. Otherwise, you will lose points!
> 
> You **DON'T have to turn in your test scenarios** for this project. However, you should still write test scenarios that test all aspects of your code, since the test scenarios provided are not comprehensive.
> 
> ## **Development notes**
> 
> -   We are providing you with a Ubuntu 14.04 (64-bit) VM image for this assignment. This image has Switchyard, Mininet and Wireshark installed so you do not need to worry about setting up the environment. After logging in the vm you can find a switchyard_master folder. The tests and switch python file should be located and executed from that folder.
> -   You can find the VM image [here](http://pages.cs.wisc.edu/~seanm/assets/Switchyard.ova). (user name: **cs640user** \- password: **cs640**)
> -   You can learn more about importing a VM image in VirtualBox [here (Links to an external site.)](https://docs.oracle.com/cd/E26217_01/E26796/html/qs-import-vm.html).CSL  machines ( [link](https://csl.cs.wisc.edu/services/remote-access/instructional-linux-computers) ) already have VirtualBox installed so you should be able to use the image there without any problems You can also install VirtualBox in your machines following this [link (Links to an external site.)](https://www.virtualbox.org/wiki/Downloads).
> -   If you are a free soul and want to setup Switchyard in a different environment you are welcome to do that as well. You can find some useful information [here (Links to an external site.)](https://github.com/jsommers/switchyard#installation). Here's a [f](http://pages.cs.wisc.edu/~seanm/projects/sy_install.txt)[i](http://pages.cs.wisc.edu/~karthikc/CS640S19/P1/sy_install.txt)[le](http://pages.cs.wisc.edu/~seanm/projects/sy_install.txt) with commands that can be used to setup the Switchyard environment on Ubuntu 14.04. This might or might not be useful for you depending on your environment. (**NOTE** Grading however will be done using the VM provided above. If you build the code using a different environment, ensure that your code runs in the VM provided).
> -   Documentation for Switchyard is available at [switchyard (Links to an external site.)](http://cs.colgate.edu/~jsommers/switchyard/2017.01/)
> -   FAQ will be updated if multiple people run into the same problems, so it might be useful to regularly check the FAQ. Otherwise, you can always shoot me an email  to get clarification.
> 
> ## FAQs  
>   
> 
> **Q:** How would the table look for the following sequence of packets in the FIFO based implementation: (h1,h4), (h2,h1), (h3,h1), (h1, h4), (h4,h1), (h5,h1), (h6,h1), (h1, h4) ? (assuming that the network topology does not change)  
>   
> **A:** Assuming that the leftmost entry is entry that came first:  
> \[h1\]-->\[h1,h2\]-->\[h1,h2, h3\]-->\[h1,h2,h3\]-->\[h1,h2, h3, h4\]-->\[h1,h2, h3, h4, h5\]--->\[h2, h3, h4, h5, h6\]---> \[h3, h4, h5, h6, h1\]  
> 
> **Q** Should the entries in the FIFO switch removed based on a timeout condition?
> 
> **A:** No,  you shouldn't remove the entries based on a timeout. The entries should only be removed based on the FIFO condition.
> 
> **Q** If the state of the mac table is \[h1, h2, h3, h4, h5\] and a packet (h6,h1) comes to the switch what should be the final state of the table?
> 
> **A**. Since the table is full we should first delete the entry for h1 and then put h6 thus the final state of the table becomes \[h2,h3,h4,h5,h6\]. Now since, we don't have the entry for h1 we should forward this packet along all the ports except the incoming port. 
> 
> **Q:** Should our switch implementations be aware of changes in the topology?  
>   
> **A:**
> 
> **FIFO switch**: Your learning switch has to be aware of the changes in the topology. More specifically, if the switch receives a packet from host A on its interface 1 (i1) it will record this in its table {a->i1}. Later, if the switch receives another packet from host A but on a different interface (say i2), and if the entry {a->i1} is still present, it will be updated to {a->i2}. There will not be two different entries for the same host in your table! When updating the entry for a particular host, **do not** update its FIFO order information. (i.e if the host was third entry in the FIFO queue it should still be the third entry after the update)
> 
> **STP switch:**
> 
>  We will be first testing if spanning tree protocol is running correctly on the switches. Once this is ensured we will check if FIFO forwarding for this switch is working as expected (For instance: packets should not forwarded along the blocked ports). The idea of the stp switch is to learn the blocked ports.
> 
> Once the blocked ports are learnt through spanning tree algorithm, you just have to do FIFO forwarding taking blocked ports into account and not worry about learning the spanning tree again(for the purpose of this assignment). 
> 
> However **while** learning the spanning tree you have to consider topology changes into account. For instance, if the switch was connected to root switch with a distance of 2 hops, but there was a change in topology later, where the same switch has a direct connection to root, then the hop count of the switch to the root should be updated to 1.
> 
> **Q**  What MAC addresses should STP packets contain when being flooded or forwarded?
> 
> 1.  **A**. STP packets are generated at the node itself, so whenever a STP packet is to be sent, it should be sent with src MAC of the node (for convenience hard-code the src mac to the ethernet address of **eth0** and destination should be broadcast always: "ff:ff:ff:ff:ff:ff"
> 
> **Grading Rubric**
> 
> 1) 10 points for turning in required files that have required content and documentation
> 
> 2) 15 points for code that runs the test cases provided
> 
> 3) 10 points for code that successfully runs  switching tests
> 
> 4) 15 points for code that successfully runs spanning tree tests
