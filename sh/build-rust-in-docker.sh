#!/bin/bash

# Wrapper script to build a Rust project in a Docker container instead of on your system.

set -e
set -u

if [ -z "${IN_DOCKER:-}" ]; then
    docker run --rm -it  \
        -v $PWD:/project \
        -w /project \
        -e IN_DOCKER=1 \
        -e CHOWN_TO="$(id -u):$(id -g)" \
        rust:bullseye \
        /project/build.sh "$@"
else
    apt-get update
    apt-get install -y libtermbox-dev libc6-dev build-essential python-is-python3
    cargo build "$@"
    chown -R $CHOWN_TO /project
fi
