#!/bin/bash
#
# Downloads folder sorter. Sorts all files not from the current year into 20xy/ folders.

CURY="$(date +%Y)"

find $HOME/Downloads/ -maxdepth 1 | while read FILENAME; do
    if [ -d "$FILENAME" ] && [[ "$FILENAME" = 20?? ]]; then
        continue
    fi
    FILEY="$(stat --format '%y' "$FILENAME" | cut -d- -f1)"
    if [ "$FILEY" -lt "$CURY" ]; then
        mkdir -p "$HOME/Downloads/$FILEY/"
        mv "$FILENAME" "$HOME/Downloads/$FILEY/"
    fi
done
