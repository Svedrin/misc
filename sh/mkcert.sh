#!/bin/bash

set -e
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <domain ...>"
    exit 1
fi

DOMAIN="$1"
ALTNAMES="DNS:$1"
shift

while [ -n "${1:-}" ]; do
    ALTNAMES="${ALTNAMES},DNS:$1"
    shift
done

openssl req -x509 \
    -newkey rsa:4096 \
    -keyout "${DOMAIN}-key.pem" \
    -out    "${DOMAIN}-crt.pem" \
    -days   3650 \
    -noenc  \
    -subj   "/CN=${DOMAIN}/O=Self-Signed/C=DE" \
    -addext "subjectAltName = $ALTNAMES"
