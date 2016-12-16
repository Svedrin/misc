#!/bin/bash

set -e
set -u

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <imagefile> <os> <hostname>"
    exit 3
fi


IMAGEFILE="$1"
OS="$2"
HOSTNAME="$3"

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
    debootstrap --download-only --make-tarball="$CACHEDIR/$OS.tgz"                       \
                --include=htop,iftop,iotop,sysstat,vim,dialog,lvm2,rsync,ssh,rsyslog,sed \
                $OS "$CACHEDIR/$OS"
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


debootstrap --unpack-tarball="$CACHEDIR/$OS.tgz" $OS /mnt

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

echo $HOSTNAME > /mnt/etc/hostname

<<EOF cat > /mnt/etc/hosts
127.0.0.1       localhost
127.0.1.1       $HOSTNAME.$DOMAIN  $HOSTNAME

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF

# Configure mounts

<<EOF cat > /etc/fstab
# <filesystem>        <mount point>  <type>  <options>              <dump> <pass>
/dev/vmsys/root       /              ext4    errors=remount-ro      0      1
/dev/vmsys/varlog     /var/log       ext4    defaults               0      2
EOF

ln -sf /proc/mounts /mnt/etc/mtab



sed -i 's#TimeoutStartSec=5min#TimeoutStartSec=10sec#g' /mnt/lib/systemd/system/networking.service



<<EOSCRIPT cat > /mnt/install.sh
#!/bin/bash

set -e
set -u

locale-gen en_US.UTF-8
locale-gen de_DE.UTF-8

# Update installed packages and install a basic set of tools

apt-get update
apt-get dist-upgrade -y

service rsyslog stop
service udev stop

apt-get install -y --download-only puppet
EOSCRIPT


# Prepare postinst script to be run at first boot

mv /mnt/etc/rc.local  /mnt/etc/rc.local.orig

<<EOSCRIPT cat > /mnt/etc/rc.local
#!/bin/bash

set -e
set -u

<<EOF debconf-set-selections
keyboard-configuration  keyboard-configuration/xkb-keymap       select  de(nodeadkeys)
keyboard-configuration  keyboard-configuration/unsupported_layout       boolean true
keyboard-configuration  keyboard-configuration/switch   select  No temporary switch
keyboard-configuration  keyboard-configuration/ctrl_alt_bksp    boolean false
keyboard-configuration  keyboard-configuration/layout   select  German
keyboard-configuration  keyboard-configuration/variant  select  Deutsch - Deutsch (ohne Akzenttasten)
keyboard-configuration  keyboard-configuration/store_defaults_in_debconf_db     boolean true
keyboard-configuration  keyboard-configuration/layoutcode       string  de
keyboard-configuration  keyboard-configuration/modelcode        string  pc105
keyboard-configuration  keyboard-configuration/unsupported_options      boolean true
keyboard-configuration  keyboard-configuration/variantcode      string  nodeadkeys
keyboard-configuration  keyboard-configuration/unsupported_config_layout        boolean true
keyboard-configuration  keyboard-configuration/unsupported_config_options       boolean true
keyboard-configuration  keyboard-configuration/optionscode      string  compose:lwin
keyboard-configuration  keyboard-configuration/toggle   select  No toggling
keyboard-configuration  keyboard-configuration/model    select  Generische PC-Tastatur mit 105 Tasten (Intl)
keyboard-configuration  keyboard-configuration/compose  select  Left Logo key
keyboard-configuration  keyboard-configuration/altgr    select  The default for the keyboard layout
EOF

dpkg-reconfigure -fnoninteractive keyboard-configuration

mv /etc/rc.local      /etc/rc.local.done
mv /etc/rc.local.orig /etc/rc.local
EOF

chmod +x /mnt/etc/rc.local

EOSCRIPT


chmod +x /mnt/install.sh
chroot /mnt /install.sh
rm /mnt/install.sh


virt-install --disk "$IMAGEFILE,format=raw,cache=writeback,io=threads" --boot hd \
    --network bridge="$BRIDGE" \
    --boot 'kernel=/vmlinuz,initrd=/initrd.img,kernel_args="root=/dev/vmsys/root ro"' \
    -v --accelerate -n ${HOSTNAME} -r 4096 --arch=x86_64 --vnc --os-variant=ubuntu16.04 --vcpus 2 --noautoconsole

