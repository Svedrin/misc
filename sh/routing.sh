#!/bin/bash
echo 1 > /proc/sys/net/ipv4/ip_forward

if [ -z "$1" ]
then
	echo "Usage: $0 <iface>";
	exit 1;
fi

echo "Setting $1 IP to 192.168.13.254/24."
ip link set $1 up
sleep 1
ip addr add 192.168.13.254/24 dev $1

/sbin/iptables -t nat -A POSTROUTING -s 192.168.13.0/24 ! -d 192.168.13.0/24 -j MASQUERADE
/sbin/iptables        -A FORWARD     -o $1 -j ACCEPT     -m state --state RELATED,ESTABLISHED
/sbin/iptables        -A FORWARD     -i $1 -j ACCEPT

echo "Running DNSMASQ. Hit ^c to exit."
dnsmasq --strict-order --bind-interfaces --keep-in-foreground --conf-file= \
	--except-interface lo --listen-address 192.168.13.254 --interface $1 \
	--dhcp-range=interface:${1},192.168.13.100,192.168.13.250 \
	--dhcp-leasefile=/tmp/${1}.leases --log-dhcp --log-facility=-
