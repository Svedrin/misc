#!/bin/bash

# Wait for a MODIFY event on a file, and when it occurs, run a specified command.

set -e
set -u

export LANG=C

FILE="/etc/some_service/config.yml"
RCMD="docker restart some_service"

# End of config

LAST_RESTART=0

function inowait () {
    inotifywait -q -m -e modify "$(dirname "$FILE")"
}

# Waits for events on stdin, processes them and sends status info on stdout.
function main () {
    FILE_BASENAME="$(basename "$FILE")"
    while read DIRNAME EVENTNAME EVENTFILE; do
        if [ "$EVENTFILE" = "$FILE_BASENAME" ]; then
            NOW="$(date +%s)"
            if [ "$((NOW-$LAST_RESTART))" -gt 30 ]; then
                LAST_RESTART="$NOW"
                # In the background, wait ten seconds, then restart the service
                { sleep 10; $RCMD; } &
            fi
        fi
    done
}

inowait | main
