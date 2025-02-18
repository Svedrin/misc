#!/bin/bash
​#
# Checks if a NextCloud instance running on Port 444 is reachable, and if not, causes Synology Container Manager to restart it so it becomes reachable.
# Put it into a planned task that runs every five minutes for maximum effectiveness.

set -e
set -u
​
MYIP="$(ip route show  | awk '/^default/ {print $7}')"
​
if [ -z "$MYIP" ]; then
    echo >&2 "No IP found, exiting"
    exit 1
fi
​
RTNCODE="$(curl -k -i -s "https://$MYIP:444/login" | head -n1 | cut -d ' ' -f 2)"
​
if [ "$RTNCODE" = "404" ]; then
    echo "Restarting nextcloud"
        /usr/syno/bin/synowebapi --exec api=SYNO.Docker.Container method="stop" version=1 name="nextcloud"
        sleep 2
        /usr/syno/bin/synowebapi --exec api=SYNO.Docker.Container method="start" version=1 name="nextcloud"
fi