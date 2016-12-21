
# Networking configuration.
# Required variables:
#
# VMNAME
# NETWORK_INTERFACE
# NETWORK_METHOD=[dhcp, static]
# NETWORK_IPADDR
# NETWORK_NETMASK
# NETWORK_GATEWAY
# NETWORK_DOMAIN
# NETWORK_NAMESERVERS


# /etc/network/interfaces

if [ "$NETWORK_METHOD" = "dhcp" ]; then

<<EOF cat > /mnt/etc/network/interfaces
# interfaces(5) file used by ifup(8) and ifdown(8)
# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d

# The loopback network interface
auto lo
iface lo inet loopback

iface $NETWORK_INTERFACE inet dhcp
allow-hotplug $NETWORK_INTERFACE
EOF

else

<<EOF cat > /mnt/etc/network/interfaces
# interfaces(5) file used by ifup(8) and ifdown(8)
# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d

# The loopback network interface
auto lo
iface lo inet loopback

iface $NETWORK_INTERFACE inet static
    address $NETWORK_IPADDR
    netmask $NETWORK_NETMASK
    gateway $NETWORK_GATEWAY
    dns-nameservers $NETWORK_NAMESERVERS
    dns-search $NETWORK_DOMAIN
allow-hotplug $NETWORK_INTERFACE
EOF

fi

# /etc/hostname

echo $VMNAME > /mnt/etc/hostname

# /etc/hosts

<<EOF cat > /mnt/etc/hosts
127.0.0.1       localhost
127.0.1.1       $VMNAME.$NETWORK_DOMAIN $VMNAME

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF
