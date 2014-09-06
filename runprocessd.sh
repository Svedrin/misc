#!/bin/bash

while sleep 1; do
    sudo -u fluxmon ./manage.py runfluxprocessd -u amqp://guest:guest@127.0.0.1/fluxmon
done
