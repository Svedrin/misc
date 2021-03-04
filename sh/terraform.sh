#!/bin/bash

set -e
set -u

exec docker run -it --rm \
    -v "/etc/passwd:/etc/passwd:ro" \
    -v "/etc/shadow:/etc/shadow:ro" \
    -v "/etc/group:/etc/group:ro" \
    -u "$(id -u):$(id -g)" \
    -v "$HOME:$HOME" \
    -w "$PWD" \
    hashicorp/terraform:light "$@"
