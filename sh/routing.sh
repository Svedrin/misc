#!/bin/bash
echo 1 > /proc/sys/net/ipv4/ip_forward

if [ -z $1 -o -z $2 ]
then
	echo "Usage: $0 <in_iface> <out_iface>";
	exit 1;
fi

echo "Setting $1 IP to 192.168.13.254/24."
ifconfig $1 192.168.13.254/24

/sbin/iptables -t nat -A POSTROUTING       -o $2 -j MASQUERADE
/sbin/iptables        -A FORWARD     -i $2 -o $1 -j ACCEPT     -m state --state RELATED,ESTABLISHED
/sbin/iptables        -A FORWARD     -i $1 -o $2 -j ACCEPT

echo "Running DNSMASQ. Hit ^c to exit."
dnsmasq --strict-order --bind-interfaces --keep-in-foreground --conf-file= \
	--except-interface lo --listen-address 192.168.13.254 --interface $1 \
	--dhcp-range=interface:${1},192.168.13.100,192.168.13.250 \
	--dhcp-leasefile=/tmp/${1}.leases
