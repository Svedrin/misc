#!/bin/bash

set -e
set -u

SELF="$0"

usage () {
    echo "Usage: $SELF add|del <ext iface> <ext ip> <int ip>"
    echo "Add <ext ip> to <ext iface> and statically NAT it to <int ip>."
}

if [ "$#" != 4 ]; then
    usage
    exit 2
fi


ACTION="$1"
EXT_IFACE="$2"
EXT_IP="$3"
INT_IP="$4"

EXT_NET=$(ip route show dev "$EXT_IFACE" scope link proto kernel | awk '{ print $1 }')
EXT_NETADDR="${EXT_NET%/*}"
EXT_NETCIDR="${EXT_NET#*/}"

if [ "$ACTION" = add ]; then
    set -x
    ip addr add "$EXT_IP"/"$EXT_NETCIDR" dev "$EXT_IFACE"
    iptables -t nat -I PREROUTING  -s "$EXT_NET" -d "$EXT_IP"  -j DNAT --to="$INT_IP"
    iptables -t nat -I POSTROUTING -s "$INT_IP"  -d "$EXT_NET" -j SNAT --to="$EXT_IP"

elif [ "$ACTION" = del ]; then
    set -x
    iptables -t nat -D PREROUTING  -s "$EXT_NET" -d "$EXT_IP"  -j DNAT --to="$INT_IP"
    iptables -t nat -D POSTROUTING -s "$INT_IP"  -d "$EXT_NET" -j SNAT --to="$EXT_IP"
    ip addr del "$EXT_IP"/"$EXT_NETCIDR" dev "$EXT_IFACE"

else
    usage
    exit 2

fi

