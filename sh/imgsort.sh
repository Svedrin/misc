#!/bin/bash

set -e
set -u

export LANG=C

for image in "$@"; do
    datestr="$(exiv2 -g Exif.Image.DateTime -Pv "$image")"
    year="$(cut -d: -f1 <<<$datestr)"
    mnth="$(cut -d: -f2 <<<$datestr)"
    mkdir -p $year/$mnth
    echo mv $image $year/$mnth/
    mv $image $year/$mnth/
done
