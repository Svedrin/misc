#!/bin/bash

set -e
set -u

export LANG=C

for image in "$@"; do
    datestr="$(exiv2 -g Exif.Image.DateTime -Pv "$image")"
    year="$(cut -d: -f1 <<<$datestr)"
    mnth="$(cut -d: -f2 <<<$datestr)"
    if [ -z "$datestr" ] || [ -z "$year" ] || [ -z "$mnth" ]; then
        echo "$image: failed to read date from EXIF data" >&2
        continue
    fi
    mkdir -p $year/$mnth
    echo mv $image $year/$mnth/
    mv $image $year/$mnth/
done
