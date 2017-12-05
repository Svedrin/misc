#!/bin/bash

set -e
set -u

QUERY_URL="${1:-"http://localhost:9200/"}_cat/recovery?v&h=index,source_node,bytes_recovered,bytes_total,bytes_percent"

wget -O - -q "$QUERY_URL" | awk -W interactive '
BEGIN {
	sum_bytes_recovered = 0
	sum_bytes_total     = 0
	recovery_pending    = 0
	recovery_done       = 0
}
{
	# index source_node    bytes_recovered bytes_total bytes_percent
	#  $1       $2            $3               $4        $5
	if( $5 != "100.0%" && $5 != "0.0%" )
		print
	if( $5 == "100.0%" )
		recovery_done++;
	else
		recovery_pending++;
	sum_bytes_recovered += $3
	sum_bytes_total     += $4
}
END {
	print ""
	printf "%-40s", "Sum MB recovered/total"
	printf "%16.2f", sum_bytes_recovered / 1024 / 1024
	printf "                "
	printf "%16.2f", sum_bytes_total     / 1024 / 1024
	print ""
	printf "%-40s", "Indices recovered/pending/total"
	printf "%16.2f", recovery_done
	printf "%16.2f", recovery_pending
	printf "%16.2f", recovery_done + recovery_pending
	print ""
}
'

