#!/bin/bash

# Talk to an SMTP server and send a very dummy test mail.

set -e
set -u

if [ -z "$(which ncat)" ]; then
    echo "Please install ncat"
    exit 1
fi

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <ip> [<port:25>]"
    exit 1
fi

function send_lines {
    sleep 0.5
    while read LINE; do
        echo "$LINE"
        echo "> $LINE" >&2
        sleep 0.1
    done
}

<<EOF send_lines | ncat --crlf "$1" "${2:-25}"
EHLO $HOSTNAME
MAIL FROM:<$USER@$HOSTNAME>
RCPT TO:<icanhaz@cheezbr.gr>
DATA
Subject: srs subject
From: $USER@$HOSTNAME
To: icanhaz@cheezbr.gr

This is the body of our test mail
.
QUIT
EOF
