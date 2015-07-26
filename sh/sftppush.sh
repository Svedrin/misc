#!/bin/bash

set -e
set -u
# set -x

# Handy little script to manage local mirrors of a remote directory that can only be accessed through SFTP, but not scp, rsync etc.
# Provides an actually usable replacement for sftp(1), combined with a set of niceties for diffing.

# Where's the local mirror?
LOCALROOT="/home/you/somewhere"
# What's the remote directory?
TARGETROOT="sftp://you@somehost.net/somewhere"

# Define those variables in ~/.sftppushrc please...

. $HOME/.sftppushrc

if [ "$PWD" != "$LOCALROOT" ]; then
  echo "cd to $LOCALROOT first"
  exit 2
fi

if [ "$#" -lt 2 ]; then
  echo Usage: $0 "<command>" "<file ...>"
  echo
  echo Commands:
  echo "  push: copy local to remote"
  echo "  pull: copy remote to local"
  echo "  diff: diff remote with local, showing local changes"
  echo "  cat:  display contents of remote file"
  echo "  ls:   display contents of remote directory"
  echo "  kate: open remote file in kate"
  exit 1
fi

case "$1" in
  push)
    shift
    for FILEARG in "$@"; do
      kioclient --noninteractive --overwrite cp "$FILEARG" "$TARGETROOT/$FILEARG"
    done
    ;;

  pull)
    shift
    for FILEARG in "$@"; do
      kioclient --noninteractive --overwrite cp "$TARGETROOT/$FILEARG" "$FILEARG"
    done
    ;;

  diff)
    shift
    for FILEARG in "$@"; do
      kioclient --noninteractive cat "$TARGETROOT/$FILEARG" | diff -u --label "$TARGETROOT/$FILEARG" --label "$LOCALROOT/$FILEARG" - "$FILEARG"
    done
    ;;

  cat)
    shift
    for FILEARG in "$@"; do
      kioclient --noninteractive cat "$TARGETROOT/$FILEARG"
    done
    ;;

  ls)
    shift
    for FILEARG in "$@"; do
      kioclient --noninteractive ls "$TARGETROOT/$FILEARG"
    done
    ;;

  kate)
    shift
    for FILEARG in "$@"; do
      kate -u "$TARGETROOT/$FILEARG"
    done
    ;;
esac
