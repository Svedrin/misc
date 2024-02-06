#!/bin/bash
#
# Script to monitor status of a systemd unit for PRTG.
# Store to /var/prtg/scripts, chmod +x and then configure your SSH probe.
#

UNIT=nginx

set -u

systemctl status "$UNIT" > /dev/null
STATUS_CODE="$?"

set -e

# RETURN_CODE see https://kb.paessler.com/en/topic/39513-is-there-a-shell-script-example-for-the-ssh-script-sensor
# STATUS_CODE see https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#Exit%20status

if [ "$STATUS_CODE" = "0" ]; then
    RETURN_CODE="0"
    STATUS_TEXT="unit $UNIT is active"
else
    RETURN_CODE="2"
    STATUS_TEXT="unit $UNIT is not active"
fi

echo "$RETURN_CODE:$STATUS_CODE:$STATUS_TEXT"
