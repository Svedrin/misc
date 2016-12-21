
# Default settings for vmaker.
#
# To customize, create a file named settings.sh and overwrite any
# values you'd like to change there.


if [ "$(lsb_release -is)" = "Debian" ]; then
    OS="jessie"
else
    OS="xenial"
fi


CACHEDIR="/var/cache/vmaker"

DOMAIN="example.com"
BRIDGE="virbr0"

get_network () {
    # get_network is a stub which should be overwritten in settings.sh.
    #
    # This script needs to figure out the network configuration for the new VM,
    # and return the appropriate variables to be used by parts/networking.sh.
    # Variables are returned by echoing them in an eval-compatible way.
    #
    # These variables exist:
    #
    #   NETWORK_METHOD="static" or "dhcp"
    #   NETWORK_IPADDR=192.168.4.2
    #   NETWORK_NAMESERVERS="192.168.0.1 192.168.0.10"
    #   NETWORK_DOMAIN=example.com
    #   NETWORK_BRIDGE=virbr0
    #   NETWORK_GATEWAY=192.168.4.254
    #   NETWORK_NETMASK=24
    #
    # The default configuration is to use DHCP.

    echo "NETWORK_METHOD=dhcp"
    echo "NETWORK_BRIDGE=$BRIDGE"
    echo "NETWORK_DOMAIN=$DOMAIN"

}
