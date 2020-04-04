#!/bin/bash

set -e
set -u

IMAGES_DIR=/media/bilder
MQTT_HOST="127.0.0.1"
MQTT_USER="mqtt"
MQTT_PASS="supersecret"
MQTT_TPFX="ctrl/d3100"

[ -r "$HOME/.mqtt" ] && source "$HOME/.mqtt"

export LANG=C

echo "Detecting cameras..."
if [ -z "$(gphoto2 --auto-detect | tail -n +3)" ]; then
    echo "No camera found (is it on?)"
    exit 1
fi

# Subscribes to the command topic and waits for commands.
function mqtt_in () {
    mosquitto_sub -h "$MQTT_HOST" -u "$MQTT_USER" -P "$MQTT_PASS" -t "$MQTT_TPFX/command"
}

# Waits for commands on stdin, processes them and sends status info on stdout.
function main () {
    echo "idle"
    while read CMD; do
        echo "Received command $CMD" >&2
        case "$CMD" in
            BATTERY)
                BATLEVEL="$(gphoto2 --summary | grep Battery | grep -Po '\([0-9]+\)' | tr -d '()')"
                mosquitto_pub -h "$MQTT_HOST" -u "$MQTT_USER" -P "$MQTT_PASS" -t "$MQTT_TPFX/battery" -m "$BATLEVEL"
    	    ;;

    	SHOOT)
                echo "shooting"
                DATE_DIR="$(date +%Y-%m-%d)"
                mkdir -p "$IMAGES_DIR/$DATE_DIR"
                cd "$IMAGES_DIR/$DATE_DIR"
    
                echo -n "Shooting at " >&2; date >&2
                START_SHOT="$(date +%s)"
                gphoto2 --capture-image-and-download --filename='%Y-%m-%d-%H-%M-%S.%C'
                echo "done" >&2
                echo "idle"
    	    ;;
        esac
    done
}

# Waits for status infos on stdin and publishes those via MQTT.
function mqtt_out () {
    mosquitto_pub \
        -h "$MQTT_HOST" -u "$MQTT_USER" -P "$MQTT_PASS" -t "$MQTT_TPFX/status" -l \
        --will-topic "$MQTT_TPFX/status" --will-payload "offline"
}


mqtt_in | main | mqtt_out
