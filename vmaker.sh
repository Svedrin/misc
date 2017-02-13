#!/bin/bash

set -e
set -u


if [ ! -e defaults.sh ]; then
    echo "defaults.sh not found, exiting"
    exit 3
fi

source defaults.sh

if [ -e "os/$OS/vmaker.sh" ]; then
    source "os/$OS/vmaker.sh"
fi

if [ -e settings.sh ]; then
    source settings.sh
fi


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

if ! python -c 'import xmltodict'; then
    echo "Please install python-xmltodict."
    exit 4
fi

########################################
#                                      #
#        Parse argumentés              #
#                                      #
########################################


while [ -n "${1:-}" ]; do
    case "$1" in
        -h|--help)
            echo "Usage: $0 [options] -f <imagefile> -n <hostname>"
            echo
            echo "Options:"
            echo " -h --help             This help text"
            echo "    --virt-install     Automatically register a KVM VM"
            echo "    --pcmk             Automatically register the VM with pacemaker (implies --virt-install)"
            echo "    --puppet           Auto-Deploy and start the Puppet agent (useful with an autosign policy on the master)"
            echo " -o --os               OS variant [$OS]"
            echo " -i --ipaddr           IP Address [dhcp]"
            echo " -f --imagefile        Image file (file path, or rbd:pool/image for Ceph)"
            echo " -n --hostname         Host name for the created VM"
            echo " -r --ram              RAM in MB [$RAM]"
            echo " -c --cpus             CPU Cores [$CPUS]"
            exit 0
            ;;

        --virt-install)
            VIRTINST=true
            ;;

        --pcmk)
            VIRTINST=true
            PCMK=true
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

        -i|--ipaddr)
            IPADDR="$2"
            shift
            ;;

        -r|--ram)
            RAM="$2"
            shift
            ;;

        -c|--cpus)
            CPUS="$2"
            shift
            ;;

        *)
            echo "Unknown option $1, see --help"
            exit 3
    esac
    shift
done

if [ -z "${IMAGEFILE:-}" ] || [ -z "${VMNAME:-}" ]; then
    echo "Usage: $0 [options] -f <imagefile> -n <hostname> -- see --help"
    exit 3
fi


MNT="/tmp/vmaker-${VMNAME}"

########################################
#                                      #
#        CLEANUP MECHANISM             #
#                                      #
########################################

CLEANUP_STAGE=0

cleanup() {
    if [ "$CLEANUP_STAGE" -ge 2 ]; then
        umount "$MNT"/{dev,proc,sys}
    fi

    if [ "$CLEANUP_STAGE" -ge 1 ]; then
        while ! umount "$MNT"; do
            sleep 1
        done
        rmdir "$MNT"
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
    debootstrap --make-tarball="$CACHEDIR/$OS.tgz" \
                ${DEBOOTSTRAP_OPTS:-} $OS "$CACHEDIR/$OS"
fi



########################################
#                                      #
#     CREATE IMAGE AND PARTITIONS      #
#                                      #
########################################


if [ "`echo $IMAGEFILE | cut -d: -f1`" = "rbd" ]; then
    # Target is an RBD image. Since guestfish can't handle those,
    # use a tempfile and qemu-img convert to rbd before booting
    # the VM.

    if qemu-img info "$IMAGEFILE" &> /dev/null; then
        echo "Image already exists"
        exit 1
    fi

    RBD_MODE="true"
    RBD_POOL="`echo $IMAGEFILE | cut -d: -f2 | cut -d/ -f1`"
    RBD_IMAGE="`echo $IMAGEFILE | cut -d: -f2 | cut -d/ -f2`"
    IMAGEFILE="/tmp/$VMNAME.img"

    # See if virsh is ok
    virsh pool-refresh "$RBD_POOL"
fi

if [ -e "$MNT" ]; then
    rmdir "$MNT"
fi
mkdir -p "$MNT"

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
--rw -o dev "$MNT"

CLEANUP_STAGE=1


########################################
#                                      #
#         INSTALL THE SYSTEM           #
#                                      #
########################################

# Debootstrap sometimes exits with 1 even though the installation worked perfectly fine.
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=526978
debootstrap --unpack-tarball="$CACHEDIR/$OS.tgz" $OS "$MNT" || /bin/true

mount --bind /dev  "$MNT/dev"
mount --bind /proc "$MNT/proc"
mount --bind /sys  "$MNT/sys"

CLEANUP_STAGE=2


########################################
#                                      #
#        CONFIGURE THE SYSTEM          #
#                                      #
########################################


cp os/$OS/sources.list "$MNT/etc/apt/sources.list"


# Configure networking

eval "$(get_network)"
source parts/networking.sh

# Configure mounts

<<EOF cat > "$MNT/etc/fstab"
# <filesystem>        <mount point>  <type>  <options>              <dump> <pass>
/dev/vmsys/root       /              ext4    errors=remount-ro      0      1
/dev/vmsys/varlog     /var/log       ext4    defaults               0      2
EOF

ln -sf /proc/mounts "$MNT/etc/mtab"


<<EOF cat > "$MNT/etc/default/keyboard"
# KEYBOARD CONFIGURATION FILE

# Consult the keyboard(5) manual page.

XKBMODEL="pc105"
XKBLAYOUT="de"
XKBVARIANT="nodeadkeys"
XKBOPTIONS=""

BACKSPACE="guess"
EOF


<<EOSCRIPT cat > "$MNT/install.sh"
#!/bin/bash

set -e
set -u
set -x

apt-get update

<<EOF debconf-set-selections
locales	locales/locales_to_be_generated	multiselect	de_DE.UTF-8 UTF-8, en_US.UTF-8 UTF-8
locales	locales/default_environment_locale	select	de_DE.UTF-8
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
console-setup	console-setup/fontsize-text47	select	8x16
console-setup	console-setup/charmap47	select	UTF-8
console-setup	console-setup/fontsize	string	8x16
console-setup	console-setup/codesetcode	string	Lat15
console-setup	console-setup/codeset47	select	# Latin1 and Latin5 - western Europe and Turkic languages
console-setup	console-setup/store_defaults_in_debconf_db	boolean	true
console-setup	console-setup/fontface47	select	VGA
console-setup	console-setup/fontsize-fb47	select	8x16
EOF

if dpkg-query -l keyboard-configuration > /dev/null; then
    dpkg-reconfigure -fnoninteractive keyboard-configuration
else
    apt-get -y install keyboard-configuration console-setup
fi


# Update installed packages and install a basic set of tools

apt-get dist-upgrade -y
apt-get install -y lvm2 locales htop iftop iotop sysstat vim dialog rsync rsyslog
locale-gen en_US.UTF-8
locale-gen de_DE.UTF-8

service rsyslog stop || /bin/true
service udev    stop || /bin/true

# root password = init123
usermod --password '\$6\$5/wXIu6E\$P4qgpWiECnhO0TH/PwLJCSPgHX5Fl6GSCz1VOKn6LYGq6lBqW8ULKTUzusGZUfcIej5RrEI8lKgkq48n/Mm.41' root

/usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y $KERNEL_PACKAGE grub2

apt-get install -y --download-only openssh-server ssh

EOSCRIPT

if [ "${PUPPIFY:-false}" = "true" ]; then
    echo apt-get install -y --download-only puppet >> "$MNT/install.sh"
fi


# Prepare postinst script to be run at first boot

mv "$MNT/etc/rc.local" "$MNT/etc/rc.local.orig"

<<EOSCRIPT cat > "$MNT/etc/rc.local"
#!/bin/bash

exec >> /var/log/sysprep.log
exec 2>&1

set -e
set -u
set -x

<<EOF debconf-set-selections
grub-pc	grub-pc/install_devices	multiselect	/dev/vda
EOF

DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server ssh

grub-install --recheck /dev/vda

mv /etc/rc.local      /etc/rc.local.done
mv /etc/rc.local.orig /etc/rc.local

EOSCRIPT

if [ "${PUPPIFY:-false}" = "true" ]; then
    echo apt-get -y install puppet >> "$MNT/etc/rc.local"
    echo puppet agent --enable     >> "$MNT/etc/rc.local"
    echo service puppet restart    >> "$MNT/etc/rc.local"
fi

chmod +x "$MNT/etc/rc.local"

chmod +x "$MNT/install.sh"
chroot "$MNT" /install.sh
rm "$MNT/install.sh"

if [ "$OS" = "xenial" ]; then
    sed -i 's#TimeoutStartSec=5min#TimeoutStartSec=10sec#g' "$MNT/lib/systemd/system/networking.service"
fi

cleanup
CLEANUP_STAGE=0


# Install grub

guestfish -a "$IMAGEFILE" run                            \
: mount /dev/vmsys/root /                                \
: mkdir-p /boot/grub                                     \
: write /boot/grub/device.map "(hd0) /dev/sda"           \
: copy-in "parts/etc-default-grub" "/tmp"                \
: mv "/tmp/etc-default-grub" "/etc/default/grub"         \
: command "grub-install /dev/sda"                        \
: command "update-grub"


# See if we're building an RBD image, and if so, convert
if [ "${RBD_MODE:-false}" = "true" ]; then
    qemu-img convert -p -O raw "$IMAGEFILE" "rbd:$RBD_POOL/$RBD_IMAGE"
    virsh pool-refresh "$RBD_POOL"
    rm -f "$IMAGEFILE"
fi


if [ "${VIRTINST:-false}" = "true" ]; then
    if [ "${RBD_MODE:-false}" = "false" ]; then
        virt-install --disk "$IMAGEFILE,format=raw,cache=writeback,io=threads" --boot hd \
            --network bridge="$NETWORK_BRIDGE" \
            -v --accelerate -n ${VMNAME} -r "$RAM" --arch=x86_64 --vnc --os-variant="$OSVARIANT" \
            --vcpus "$CPUS" --noautoconsole --print-xml | virsh define /dev/stdin
    else
        virt-install --disk "vol=$RBD_POOL/$RBD_IMAGE,format=raw,cache=writeback,io=threads" --boot hd \
            --network bridge="$NETWORK_BRIDGE" \
            -v --accelerate -n ${VMNAME} -r "$RAM" --arch=x86_64 --vnc --os-variant="$OSVARIANT" \
            --vcpus "$CPUS" --noautoconsole --print-xml | python parts/fix-rbd-disk-xml.py $RBD_POOL | virsh define /dev/stdin
    fi

    virsh start "${VMNAME}"
fi


if [ "${PCMK:-false}" = "true" ]; then
    crm configure primitive "vm_${VMNAME}" VirtualDomain \
        params config="/etc/libvirt/qemu/${VMNAME}.xml" hypervisor="qemu:///system" migration_transport=ssh force_stop=0 \
        op start interval=0 timeout=90s \
        op stop interval=0 timeout=300s \
        op monitor interval=10 timeout=30s depth=0 \
        op migrate_from interval=0 timeout=240s \
        op migrate_to interval=0 timeout=240s \
        meta allow-migrate=true target-role=Started
fi

