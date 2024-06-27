#!/bin/bash
set -euo pipefail

IP=$(command -v ip)

# Starting
echo "Start cleaning up..."

# We check if ns1 and ns2 namespaces exist
netns=$($IP netns list | grep "ns[12]" || [[ $? == 1 ]])

if [[ ${#netns} -eq 0 ]]; then
    echo "Nothing to clean. Exiting..."
    exit 0
fi

# Shutting down the veth devices
sudo $IP -n ns1 link set dev veth1 down
sudo $IP -n ns2 link set dev veth2 down

# Delete the veth pair (this command will remove both veth1 and veth2)
sudo $IP -n ns1 link delete veth1 type veth

# Delete the two namespaces
sudo $IP netns del ns1
sudo $IP netns del ns2

# Finished
echo "Cleanup finished."
