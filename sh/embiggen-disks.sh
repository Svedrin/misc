#!/bin/bash
#
# Run after disks of a VM have been resized via the host.
# Rescan all disks, resize their first partition to 100%, and if it contains a PV, resize that as well.

set -e
set -u

DISKS="$(cd /sys/class/block; echo [svx]d?)"
for DISK in $DISKS; do
    echo 1 > "/sys/class/block/$DISK/device/rescan"
    parted "/dev/$DISK" resizepart 1 100%
    if pvdisplay "/dev/${DISK}1" &> /dev/null; then
        pvresize "/dev/${DISK}1"
    fi
done
