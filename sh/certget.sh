#!/bin/bash
# Connects to a server and dumps its certificate.

set -e
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <ip:port>"
    exit 1
fi

echo | openssl s_client -connect "$1" 2>&1 | sed -n '/-----BEGIN/,/-----END/p'
