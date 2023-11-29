#!/bin/bash
#
# Upload files to a NextCloud shared folder.
#
# See also https://help.nextcloud.com/t/uploading-to-a-public-link-via-a-script/20294/2
#

set -e
set -u

# Default URL to the shared folder where you want files to be uploaded to.
SHARED_FOLDER="https://nextcloud.example.com/s/asdfASDFasdf123"

# Allow the URL to be specified on the command line
if [ "$1" = "-u" ]; then
    SHARED_FOLDER="$2"
    shift 2
fi

if [ -z "${1:-}" ]; then
    echo "Usage: $0 [-u <shared_folder_url>] <file | file:uploaded_name ...>"
    echo "Upload files to a NextCloud shared folder located at $SHARED_FOLDER"
    exit 1
fi

FOLDER_ID="$(<<<$SHARED_FOLDER cut -d/ -f 5  )"
NC_URL="$(   <<<$SHARED_FOLDER cut -d/ -f 1-3)"

while [ -n "${1:-}" ]; do
    # split $1 at a : (if any)
    LOCALNAME="$( <<<"$1" cut -d: -f1)"
    REMOTENAME="$(<<<"$1" cut -d: -f2 -s)"
    # if that didn't return anything (because no :something was specified),
    # fall back to basename
    if [ -z "$REMOTENAME" ]; then
        REMOTENAME="$(basename "$1")"
    fi
    # Now upload
    curl -k -T "$LOCALNAME" \
         -u "$FOLDER_ID:" \
         -H 'X-Requested-With: XMLHttpRequest' \
         "$NC_URL/public.php/webdav/$REMOTENAME"
    shift
done
