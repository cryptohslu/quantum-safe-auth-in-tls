#!/bin/sh

# Starting
echo "Start the setup..."

# Set up two namespaces with the name ns1 and ns2
sudo ip netns add ns1 
sudo ip netns add ns2

# Create a virtual Ethernet pair (veth101 and veth102) and link them to the namespaces (ns1 and ns2, respectively)
sudo ip link add name veth101 address 00:00:00:00:00:01 netns ns1 type veth peer name veth102 address 00:00:00:00:00:02 netns ns2

# Assign an IP address to each veth device and change the device state to "up"
sudo ip -n ns1 addr add 192.168.101.1/24 dev veth101 && sudo ip -n ns1 link set dev veth101 up
sudo ip -n ns2 addr add 192.168.102.1/24 dev veth102 && sudo ip -n ns2 link set dev veth102 up

# Add default route configs
sudo ip -n ns1 route add 192.168.102.0/24 dev veth101
sudo ip -n ns2 route add 192.168.101.0/24 dev veth102

# Disable TCP Segmentation Offload (TSO), GSO and GRO
sudo ip netns exec ns1 ethtool -K veth101 gso off gro off tso off
sudo ip netns exec ns2 ethtool -K veth102 gso off gro off tso off

# Finished.
echo "Setup finished."

