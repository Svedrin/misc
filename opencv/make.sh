#!/bin/bash

set -eux

TARGET="$1"

echo "Building $TARGET..."
g++ -ggdb `pkg-config --cflags --libs opencv` "$TARGET.cpp" -o "$TARGET"
