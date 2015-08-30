#!/bin/bash

while true; do
    time ./manage.py runalfredd
    echo "sleeping for 5m..."
    sleep 5m
done
