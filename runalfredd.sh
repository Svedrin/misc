#!/bin/bash

while true; do
    ./manage.py runalfredd
    echo "sleeping for 5m..."
    sleep 5m
done
