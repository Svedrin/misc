#!/bin/bash
#
# Cert renewal script that updates the cert store of a UniFi Controller.
# Save as /etc/letsencrypt/renewal-hooks/post/unifi.sh and chmod +x.

set -e
set -u

# see https://lg.io/2015/12/13/using-lets-encrypt-to-secure-cloud-hosted-services-like-ubiquitis-mfi-unifi-and-unifi-video.html
# Part D

openssl pkcs12 -export \
        -inkey /etc/letsencrypt/live/example.com/privkey.pem \
        -in    /etc/letsencrypt/live/example.com/fullchain.pem \
        -out   /dev/shm/cert.p12 \
        -name unifi \
        -password pass:temppass

keytool -importkeystore \
        -deststorepass aircontrolenterprise \
        -destkeypass   aircontrolenterprise \
        -destkeystore  /var/lib/unifi/keystore \
        -srckeystore   /dev/shm/cert.p12 \
        -srcstoretype  PKCS12 \
        -srcstorepass  temppass \
        -alias         unifi \
        -noprompt

systemctl restart unifi
