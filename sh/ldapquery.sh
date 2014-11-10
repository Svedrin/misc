#!/bin/bash

# This script uses the Samba Machine account to connect to an Active Directory
# Domain's LDAP server and query it for fun and great justice.

set -e
set -u
set -x

if ! which ldapsearch > /dev/null ; then
	echo "please apt-get install ldapscripts."
	exit 1
fi

if ! python -c "import tdb"; then
	echo "please apt-get install python-tdb."
	exit 1
fi

DOMAIN="`hostname --domain`"
DC1="`hostname --domain | cut -d. -f1`"
DC2="`hostname --domain | cut -d. -f2`"
MACHACCNAME="` hostname | sed 's/./\u&/g' `$"

MACHACCPW="$(python <<EOF
import tdb
db = tdb.open("/var/lib/samba/secrets.tdb")
for key in db.iterkeys():
    if "MACHINE_PASSWORD" in key:
        print db.get(key)[:-1]
db.close()
EOF
)"

ldapsearch -x -H "ldap://$DOMAIN" -b "DC=${DC1},DC=${DC2}" -D "${MACHACCNAME}@${DOMAIN}" -w "$MACHACCPW" "$@"
