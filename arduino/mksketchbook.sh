#!/bin/bash

set -e
set -u

# Create a sketchbook directory structure from the sketches
# found in the current workdir.

for sketch in *.ino ; do
    sketchname="$(<<<"$sketch" cut -d. -f1)"
    mkdir -p "$HOME/sketchbook/$sketchname"
    if [ ! -e "$HOME/sketchbook/$sketchname/$sketch" ]; then
        ln -s "$PWD/$sketch" "$HOME/sketchbook/$sketchname/$sketch"
    else
        echo "$HOME/sketchbook/$sketchname/$sketch" exists
    fi
done
