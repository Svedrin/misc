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

{
    echo conf t
    for VETH in $(grep '^interface veth' "$ZEBRA_CONF" | cut '-d ' -f2); do
        if [ ! -e "/sys/class/net/$VETH" ]; then
            echo "no interface $VETH"
        fi
    done
    echo end
    echo write
} | vtysh
