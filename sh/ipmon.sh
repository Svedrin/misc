#!/bin/bash
#
# Runs "ip monitor address", monitoring for IP change events; parses each line and prints the event.
# Use as a starting point for when you actually want to do things when your IP changes,
# by replacing the prettyprinter with something more useful.

set -e
set -u

prtyprnt () {
    printf "%-7s %-10s %-8s %-50s %-15s %-15s %s\n" "$@"
}

prtyprnt "State" "Iface" "Family" "Address" "Valid_Lft" "Preferred_Lft" "Flags"

ip -oneline monitor address | sed -u 's#\\##' | while read -ra words; do
    declare i=0

    declare DELETED="active"
    declare FLAGS=""

    if [ "${words[$i]:-}" = "Deleted" ]; then
        DELETED="deleted"
        i=$((i + 1))
    fi
    # $i = id
    declare  IFACE="${words[$i+1]:-}"
    declare FAMILY="${words[$i+2]:-}"
    declare   ADDR="${words[$i+3]:-}"
    i=$((i + 4))
    declare VALIDLFT=""
    declare PREFDLFT=""

    while [ -n "${words[$i]:-}" ]; do
        if [ "${words[$i]:-}" = "\\" ]; then
            : # nothing here, but increase the counter
        elif [ "${words[$i]:-}" = "valid_lft" ]; then
            VALIDLFT="${words[$i+1]:-}"
            i=$((i + 1))
        elif [ "${words[$i]:-}" = "preferred_lft" ]; then
            PREFDLFT="${words[$i+1]:-}"
            i=$((i + 1))
        else
            FLAGS="$FLAGS "${words[$i]:-}""
        fi
        i=$((i + 1))
    done
    prtyprnt "$DELETED" "$IFACE" "$FAMILY" "$ADDR" "$VALIDLFT" "$PREFDLFT" "${FLAGS:1}"

done
