#!/bin/bash

# I'm gonna hate myself for this thing one day

LANG=C iostat -xdm "$@" | awk -W interactive '
function colorprint(color, number){
	printf "\033[1;%sm%10.2f\033[1;m", color, number
}
BEGIN {
	skip = 1            # used to skip the first two lines
	mbs_to_tbd = 0.0864 # WolframAlpha said so
	devcount = 0        # devices counter
	# Color codes
	none    = ""
	gray    = "30"
	red     = "31"
	green   = "32"
	yellow  = "33"
}
{
	# Device: rrqm/s wrqm/s r/s w/s rMB/s wMB/s avgrq-sz avgqu-sz await r_await w_await svctm %util
	#  $1       $2     $3   $4  $5   $6   $7     $8       $9       $10   $11     $12     $13   $14
	
	if( $1 == "Device:" ){
		printf "%-10s %9s %9s %9s %9s %9s %9s %9s\n", $1, $4, $5, $7, "wTB/d", $8, $12, $14
		skip = 0
		next
	}

	# Skip everything up to the first Device: line
	if( skip )
		next

	# iostat prints an empty line between sections. if it does, print the totals
	if( $0 == "" ){
		printf "%-10s", "Total"
		printf "%10.2f", total_rs
		printf "%10.2f", total_ws
		printf "%10.2f", total_wMBs
		printf "%10.2f", total_wMBs * mbs_to_tbd
		printf "%10.2f", total_rqsz / devcount
		printf "%10.2f", total_wlat / devcount
		printf "%10.2f", total_util / devcount
		print ""
		devcount   = 0
		total_rs   = 0
		total_ws   = 0
		total_wMBs = 0
		total_rqsz = 0
		total_wlat = 0
		total_util = 0

		print ""
		next
	}
	
	# this is a device line, highlight and print its stats
	printf "%-10s", $1

	rscolor = none
	if( $4 >    0 ) rscolor = gray
	if( $4 >=  10 ) rscolor = green
	if( $4 >=  50 ) rscolor = yellow
	if( $4 >= 150 ) rscolor = red
	colorprint(rscolor, $4)
	total_rs += $4

	colorprint(none, $5)
	total_ws += $5

	colorprint(none, $7)
	colorprint(none, $7 * mbs_to_tbd)
	total_wMBs += $7

	rqszcolor = red
	if( $8 >  20 ) rqszcolor = yellow
	if( $8 >  50 ) rqszcolor = green
	if( $8 > 150 ) rqszcolor = gray
	colorprint(rqszcolor, $8)
	total_rqsz += $8

	latcolor = grayn
	if( $12 >  1 ) latcolor = green
	if( $12 >  5 ) latcolor = yellow
	if( $12 > 10 ) latcolor = red
	colorprint(latcolor, $12)
	total_wlat += $12

	utilcolor = none
	if( $14 >= 10 ) utilcolor = gray
	if( $14 >= 30 ) utilcolor = green
	if( $14 >= 50 ) utilcolor = yellow
	if( $14 >= 70 ) utilcolor = red
	colorprint(utilcolor, $14)
	total_util += $14

	print ""

	devcount++
}
'
