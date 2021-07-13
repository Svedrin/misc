#!/bin/bash

set -e
set -u

ceph osd getcrushmap -o /tmp/crushmap
crushtool -d /tmp/crushmap -o /tmp/crushmap.txt
cp /tmp/crushmap.txt /tmp/crushmap.txt.orig
${EDITOR:-vi} /tmp/crushmap.txt

# diff returns 0 if the file stayed the same
if ! diff /tmp/crushmap.txt.orig /tmp/crushmap.txt > /dev/null; then
        crushtool -c /tmp/crushmap.txt -o /tmp/crushmap
        ceph osd setcrushmap -i /tmp/crushmap
        echo "Updated crush map. Tree is now:"
        ceph osd tree
else
        echo "Crushmap not changed, not updating ceph"
fi
