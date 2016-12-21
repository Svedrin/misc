
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
