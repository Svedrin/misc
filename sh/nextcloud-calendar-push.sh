#!/bin/sh
#
# Script to auto-generate calendar events in a nextcloud calendar.
#
# This is useful if you have a bunch of calendar events that you want
# to create every week, e.g. for appointments to be booked by your
# clients, so that you can then manually edit them when a client
# actually books one.
#
# The config file is meant to be simple to read and edit for
# non-technical people. It needs to look like this:
#
#     # Day     Begin   End     Category
#     monday    08:00   08:45   Town_A
#     monday    09:00   09:45   Town_A
#     monday    10:00   10:45   Town_A
#     monday    11:00   11:45   Town_A
#
#     monday    13:00   13:45   Town_B
#     monday    14:00   14:45   Town_B
#     monday    15:00   15:45   Town_B
#     monday    16:00   16:45   Town_B
#
#     tuesday   08:00   12:00   Long_Appts
#     tuesday   14:00   18:00   Long_Appts
#
# And so on. Empty lines and lines starting with a # are ignored.
# The format needs to be understood by "date -d":
#
#     date -d "$WEEKPFX <weekday> <time>"
#
# Events will not have a title or description by default.
#
# Ideally, run this script as a cron job on a day for which no appts
# are configured.

set -e
set -u

NC_URL="your-nextcloud.example.com"
NC_USERNAME="someuser"
NC_PASSWORD="somepassword"

INFILE="nextcloud-calendar-events.txt" # point to the config file
WEEKPFX="next week 4"                  # create events four weeks from today

function parse_date {
    date -d "$1" '+%Y%m%dT%H%M%S'
}

function put_cal {
    EVENT_ID="$(uuidgen -r)"
    curl -X PUT \
        --user "$NC_USERNAME:$NC_PASSWORD" \
        -H "Content-Type: text/calendar" \
        --data-binary @- \
        "https://$NC_URL/remote.php/dav/calendars/$NC_USERNAME/personal/$EVENT_ID.ics" <<EOF
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Nextcloud//Calendar 1.0//EN
BEGIN:VEVENT
UID:$EVENT_ID@$NC_URL
DTSTART:$1
DTEND:$2
CATEGORIES:$3
END:VEVENT
END:VCALENDAR
EOF
}

grep -v '^#' "$INFILE" | grep day | while read WEEKDAY START END CATEGORY; do
    DTSTART="$(parse_date "$WEEKPFX $WEEKDAY $START")"
    DTEND="$(parse_date "$WEEKPFX $WEEKDAY $END")"
    put_cal "$DTSTART" "$DTEND" "$CATEGORY"
done
