#!/bin/bash

set -e
set -u


if [ "$(lsb_release -is)" = "Debian" ]; then
    OS="jessie"
else
    OS="xenial"
fi

DOMAIN="local.lan"
CACHEDIR="/var/cache/vmaker"
BRIDGE="svdr0"



########################################
#                                      #
#    Check for tools                   #
#                                      #
########################################

for tool in qemu-img guestfish guestmount debootstrap virt-install; do
    if ! which "$tool" > /dev/null; then
        echo "$tool is missing -> abort"
        exit 4
    fi
done

########################################
#                                      #
#        Parse argumentés              #
#                                      #
########################################


while [ -n "${1:-}" ]; do
    case "$1" in
        -h|--help)
            echo "Usage: $0 [options] <imagefile> <os> <hostname>"
            echo
            echo "Options:"
            echo " -h --help             This help text"
            echo "    --virt-install     Automatically register a KVM VM"
            echo "    --puppet           Auto-Deploy and start the Puppet agent"
            echo " -o --os               OS variant [$OS]"
            echo " -f --imagefile        Image file"
            echo " -n --hostname         Host name for the created VM"
            exit 0
            ;;

        --virt-install)
            VIRTINST=true
            ;;

        --puppet)
            PUPPIFY=true
            ;;

        -o|--os)
            OS="$2"
            shift
            ;;

        -f|--imagefile)
            IMAGEFILE="$2"
            shift
            ;;

        -n|--hostname)
            VMNAME="$2"
            shift
            ;;

        *)
            echo "Unknown option $1, see --help"
            exit 3
    esac
    shift
done

if [ -z "${IMAGEFILE:-}" ] || [ -z "${VMNAME:-}" ]; then
    echo "Usage: $0 [options] -i <imagefile> -n <hostname> -- see --help"
    exit 3
fi


if [ -e "os/$OS/vmaker.sh" ]; then
    source "os/$OS/vmaker.sh"
fi


########################################
#                                      #
#        CLEANUP MECHANISM             #
#                                      #
########################################

CLEANUP_STAGE=0

cleanup() {
    if [ "$CLEANUP_STAGE" -ge 2 ]; then
        umount /mnt/{dev,proc,sys}
    fi

    if [ "$CLEANUP_STAGE" -ge 1 ]; then
        umount /mnt/
    fi
}

trap cleanup EXIT


set -x

########################################
#                                      #
#    Update cache                      #
#                                      #
########################################


if [ ! -d "$CACHEDIR" ]; then
    mkdir -p "$CACHEDIR"
fi

if [ ! -e "$CACHEDIR/$OS.tgz" ]; then
    if [ -e "$CACHEDIR/$OS" ]; then
        rm -rf "$CACHEDIR/$OS"
    fi
    mkdir "$CACHEDIR/$OS"
    debootstrap --download-only --make-tarball="$CACHEDIR/$OS.tgz" \
                --include=htop,iftop,iotop,sysstat,vim,dialog,lvm2,rsync,ssh,rsyslog,sed,openssh-server \
                ${DEBOOTSTRAP_OPTS:-} $OS "$CACHEDIR/$OS"
fi



########################################
#                                      #
#     CREATE IMAGE AND PARTITIONS      #
#                                      #
########################################




qemu-img create "$IMAGEFILE" 15G

guestfish -a "$IMAGEFILE" run   \
: part-disk /dev/sda mbr        \
: pvcreate /dev/sda1            \
: vgcreate vmsys /dev/sda1      \
: lvcreate root vmsys 5120      \
: mkfs ext4 /dev/vmsys/root     \
: mount /dev/vmsys/root /       \
: mkdir-p /var/log              \
: lvcreate varlog vmsys 2048    \
: mkfs ext4 /dev/vmsys/varlog

guestmount -a "$IMAGEFILE"      \
-m /dev/vmsys/root              \
-m /dev/vmsys/varlog:/var/log   \
--rw -o dev /mnt

CLEANUP_STAGE=1


########################################
#                                      #
#         INSTALL THE SYSTEM           #
#                                      #
########################################

# Debootstrap sometimes exits with 1 even though the installation worked perfectly fine.
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=526978
debootstrap --unpack-tarball="$CACHEDIR/$OS.tgz" $OS /mnt || /bin/true

mount --bind /dev  /mnt/dev
mount --bind /proc /mnt/proc
mount --bind /sys  /mnt/sys

CLEANUP_STAGE=2


########################################
#                                      #
#        CONFIGURE THE SYSTEM          #
#                                      #
########################################


cp os/$OS/sources.list /mnt/etc/apt/sources.list


# Configure networking

<<EOF cat > /mnt/etc/network/interfaces
# interfaces(5) file used by ifup(8) and ifdown(8)
# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d

# The loopback network interface
auto lo
iface lo inet loopback

iface ens3 inet dhcp
auto ens3
EOF

echo $VMNAME > /mnt/etc/hostname

<<EOF cat > /mnt/etc/hosts
127.0.0.1       localhost
127.0.1.1       $VMNAME.$DOMAIN  $VMNAME

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF

# Configure mounts

<<EOF cat > /mnt/etc/fstab
# <filesystem>        <mount point>  <type>  <options>              <dump> <pass>
/dev/vmsys/root       /              ext4    errors=remount-ro      0      1
/dev/vmsys/varlog     /var/log       ext4    defaults               0      2
EOF

ln -sf /proc/mounts /mnt/etc/mtab


if [ "$OS" = "xenial" ]; then
    sed -i 's#TimeoutStartSec=5min#TimeoutStartSec=10sec#g' /mnt/lib/systemd/system/networking.service
fi


<<EOSCRIPT cat > /mnt/install.sh
#!/bin/bash

set -e
set -u

<<EOF debconf-set-selections
locales	locales/locales_to_be_generated	multiselect	de_DE.UTF-8 UTF-8, en_US.UTF-8 UTF-8
locales	locales/default_environment_locale	select	de_DE.UTF-8
EOF

# Update installed packages and install a basic set of tools

apt-get update
apt-get dist-upgrade -y
apt-get install -y lvm2 locales

locale-gen en_US.UTF-8
locale-gen de_DE.UTF-8

service rsyslog stop
service udev stop

# root password = init123
usermod --password '\$6\$5/wXIu6E\$P4qgpWiECnhO0TH/PwLJCSPgHX5Fl6GSCz1VOKn6LYGq6lBqW8ULKTUzusGZUfcIej5RrEI8lKgkq48n/Mm.41' root

EOSCRIPT

if [ "${PUPPIFY:-false}" = "true" ]; then
    echo apt-get install -y --download-only puppet >> /mnt/install.sh
fi


# Prepare postinst script to be run at first boot

mv /mnt/etc/rc.local  /mnt/etc/rc.local.orig

<<EOSCRIPT cat > /mnt/etc/rc.local
#!/bin/bash

exec >> /var/log/sysprep.log
exec 2>&1

set -e
set -u

<<EOF debconf-set-selections
keyboard-configuration	keyboard-configuration/xkb-keymap	select	
keyboard-configuration	console-setup/detect	detect-keyboard	
keyboard-configuration	keyboard-configuration/modelcode	string	pc105
keyboard-configuration	keyboard-configuration/ctrl_alt_bksp	boolean	true
keyboard-configuration	keyboard-configuration/store_defaults_in_debconf_db	boolean	true
keyboard-configuration	keyboard-configuration/unsupported_layout	boolean	true
keyboard-configuration	keyboard-configuration/switch	select	No temporary switch
keyboard-configuration	keyboard-configuration/unsupported_config_options	boolean	true
keyboard-configuration	keyboard-configuration/layoutcode	string	de
keyboard-configuration	keyboard-configuration/toggle	select	No toggling
keyboard-configuration	console-setup/ask_detect	boolean	false
keyboard-configuration	keyboard-configuration/variant	select	German - German (eliminate dead keys)
keyboard-configuration	keyboard-configuration/compose	select	Left Logo key
keyboard-configuration	console-setup/detected	note	
keyboard-configuration	keyboard-configuration/model	select	Generic 105-key (Intl) PC
keyboard-configuration	keyboard-configuration/variantcode	string	nodeadkeys
keyboard-configuration	keyboard-configuration/optionscode	string	lv3:ralt_switch,compose:lwin,terminate:ctrl_alt_bksp
keyboard-configuration	keyboard-configuration/layout	select	German
keyboard-configuration	keyboard-configuration/altgr	select	Right Alt (AltGr)
keyboard-configuration	keyboard-configuration/unsupported_config_layout	boolean	true
keyboard-configuration	keyboard-configuration/unsupported_options	boolean	true
EOF

if dpkg-query -l keyboard-configuration > /dev/null; then
    dpkg-reconfigure -fnoninteractive keyboard-configuration
else
    apt-get -y install keyboard-configuration console-setup
fi

mv /etc/rc.local      /etc/rc.local.done
mv /etc/rc.local.orig /etc/rc.local

EOSCRIPT

if [ "${PUPPIFY:-false}" = "true" ]; then
    echo apt-get install puppet >> /mnt/etc/rc.local
    echo puppet agent --enable  >> /mnt/etc/rc.local
    service puppet start        >> /mnt/etc/rc.local
fi

chmod +x /mnt/etc/rc.local

chmod +x /mnt/install.sh
chroot /mnt /install.sh
rm /mnt/install.sh


if [ "${VIRTINST:-false}" = "true" ]; then
    virt-install --disk "$IMAGEFILE,format=raw,cache=writeback,io=threads" --boot hd \
        --network bridge="$BRIDGE" \
        --boot 'kernel=/vmlinuz,initrd=/initrd.img,kernel_args="root=/dev/vmsys/root ro"' \
        -v --accelerate -n ${VMNAME} -r 4096 --arch=x86_64 --vnc --os-variant="$OSVARIANT" --vcpus 2 --noautoconsole
fi

