#!/bin/sh

# Starting
echo "Start cleaning up..."

# Shutting down the veth devices
sudo ip -n ns1 link set dev veth101 down
sudo ip -n ns2 link set dev veth102 down

# Delete the veth pair (this command will remove both veth101 and veth102)
sudo sudo ip -n ns1 link delete veth101 type veth

# Delete the two namespaces
sudo ip netns del ns1
sudo ip netns del ns2

# Finished
echo "Cleanup finished."
