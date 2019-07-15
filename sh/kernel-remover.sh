#!/bin/bash

set -e
set -u

PACKAGES=""
for kernel in $(ls /lib/modules); do
    if [ "$kernel" != "$(uname -r)" ]; then
        PACKAGES="$PACKAGES linux-image-$kernel linux-headers-$kernel"
    fi
done

apt-get purge $PACKAGES
