#!/bin/bash

set -e
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <domain>"
    exit 1
fi

mkdir -p /certs

if [ -e "/certs/$1.key" ] || [ -e "/certs/$1.csr" ] || [ -e "/certs/$1.crt" ]; then
    echo "Cert exists, not overwriting"
    exit 1
fi

openssl req -new -newkey rsa:2048 -nodes -keyout "/certs/$1.key" -out "/certs/$1.csr"

echo "=====" CSR "====="
cat /certs/$1.csr

echo "===== Please paste in the certificate. Hit ^d when done ====="
cat > /certs/$1.crt
