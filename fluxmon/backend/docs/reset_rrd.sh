#!/bin/bash

rrdfile=${1:-}

if [ -z "$rrdfile" ]; then
	echo "Usage: $0 <rrdfile>"
	exit 1
fi

for dsname in $(rrdtool info $rrdfile | grep '^ds\[' | cut -d[ -f2 | cut -d] -f1 | sort | uniq); do
	rrdtool tune $rrdfile --aberrant-reset $dsname
done
