#!/bin/bash

# Trigger an HP Printer to scan a document through MQTT commands.
# Requires mosquitto-clients and hplip.
# Set up the printer using hp-setup, then run hp-scan without any arguments to obtain the URL.

set -e
set -u

MQTT_HOST="127.0.0.1"
MQTT_USER="mqtt"
MQTT_PASS="supersecret"
MQTT_TPFX="ctrl/hp6970"
PRINTER="hpaio:/net/OfficeJet_Pro_6970"

[ -r "$HOME/.mqtt" ] && source "$HOME/.mqtt"

export LANG=C

# Subscribes to the command topic and writes received commands to stdout.
function mqtt_in () {
    mosquitto_sub -h "$MQTT_HOST" -u "$MQTT_USER" -P "$MQTT_PASS" -t "$MQTT_TPFX/command"
}

# Waits for commands on stdin, processes them and sends status info on stdout.
function main () {
    echo "idle"
    while read CMD; do
        echo "Received command $CMD" >&2
        case "$CMD" in
            SCAN_ADF_SVEDRIN)
                echo "sanning from ADF for Michael"
                TEMP_DIR="$(mktemp -d)"
                TEMP_FILE="${TEMP_DIR}/scan_$(date '+%Y-%m-%d_%H-%M-%S').pdf"

                echo "scanning from ADF to $TEMP_FILE " >&2
                hp-scan "-d${PRINTER}" --adf -spdf -mcolor "-o${TEMP_FILE}" >&2
                cp "$TEMP_FILE" /var/lib/nextcloud/Svedrin/files/Scans/
                chown -R www-data: /var/lib/nextcloud/Svedrin/files/Scans/
                occ files:scan --path Svedrin/files/Scans/ >&2
                rm -rf "$TEMP_DIR"
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
