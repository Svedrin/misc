#!/bin/bash

# Parse /etc/{quagga,frr}/zebra.conf, look for `veth` interfaces that are
# configured but don't exist, and issue `vtysh` commands to remove them.

set -e
set -u

if [ -e /etc/quagga ]; then
    ZEBRA_CONF="/etc/quagga/zebra.conf"
else
    ZEBRA_CONF="/etc/frr/zebra.conf"
fi

for VETH in $(grep -e '^interface veth' -e '^interface br-' "$ZEBRA_CONF" | cut '-d ' -f2); do
    if [ ! -e "/sys/class/net/$VETH" ]; then
        vtysh -c "conf t" -c "no interface $VETH"
    fi
done

vtysh -c write
