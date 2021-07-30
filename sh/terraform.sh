#!/bin/bash

set -e
set -u

# If this directory is managed by asdf, use the version that asdf
# would use.
if [ -e ".tool-versions" ]; then
    read _ TFVERSION <<< "$(grep -i terraform .tool-versions)"
    if [ -n "$TFVERSION" ]; then
        TERRFAORM_VERSION="$TFVERSION"
        echo "Running terraform version $TFVERSION from asdf"
    fi
fi

exec docker run -it --rm \
    -v "/etc/passwd:/etc/passwd:ro" \
    -v "/etc/shadow:/etc/shadow:ro" \
    -v "/etc/group:/etc/group:ro" \
    -u "$(id -u):$(id -g)" \
    -v "$HOME:$HOME" \
    -w "$PWD" \
    hashicorp/terraform:"${TERRFAORM_VERSION:-light}" "$@"
