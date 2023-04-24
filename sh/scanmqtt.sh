#!/bin/bash

# Trigger an HP Printer to scan a document through MQTT commands.
# Requires mosquitto-clients, hplip, qpdf and docker (to run OCR).
# Set up the printer using hp-setup, then run hp-scan without any
# arguments to obtain the printer's URL.

set -e
set -u

MQTT_HOST="127.0.0.1"
MQTT_USER="mqtt"
MQTT_PASS="supersecret"
MQTT_TPFX="ctrl/hp6970"
PRINTER="hpaio:/net/OfficeJet_Pro_6970"
NC_DIR="/var/lib/docker/volumes/nextcloud-data/_data"
OCR_LANG="deu+eng"

[ -r "$HOME/.mqtt" ] && source "$HOME/.mqtt"

export LANG=C

# Subscribes to the command topic and writes received commands to stdout.
function mqtt_in () {
    mosquitto_sub -h "$MQTT_HOST" -u "$MQTT_USER" -P "$MQTT_PASS" -t "$MQTT_TPFX/command"
}

# Waits for commands on stdin, processes them and sends status info on stdout.
function main () {
    echo "idle"
    while read CMD SRC USER ORNT; do
        echo "Received command $CMD" >&2
        case "$CMD" in
            SCAN)
                # Read SRC
                SRC_ARG=""
                if [ "$SRC" = "ADF" ]; then
                    SRC_ARG="--adf"
                fi
                echo "sanning from $SRC for $USER"
                TEMP_DIR="$(mktemp -d)"
                FILE_TIME="$(date '+%Y-%m-%d_%H-%M-%S')"
                TEMP_FILE="${TEMP_DIR}/scan_${FILE_TIME}.pdf"

                echo "scanning from $SRC to $TEMP_FILE for $USER" >&2
                hp-scan "-d${PRINTER}" $SRC_ARG -spdf -mcolor "-o${TEMP_FILE}" --size=a4 -r200 >&2

                if [ "$ORNT" = "L" ]; then
                    ROTATED_FILE="${TEMP_DIR}/scan_${FILE_TIME}_rot.pdf"
                    qpdf "$TEMP_FILE" "$ROTATED_FILE" "-rotate=+90"
                    mv "$ROTATED_FILE" "$TEMP_FILE"
                fi

                OCRED_FILE="${TEMP_DIR}/scan_${FILE_TIME}_ocr.pdf"
                if docker run --rm -v "${TEMP_DIR}:${TEMP_DIR}" jbarlow83/ocrmypdf \
                    -l "$OCR_LANG" --jobs 4 "$TEMP_FILE" "$OCRED_FILE"; then
                    echo "OCR successful"
                    mv "$OCRED_FILE" "$TEMP_FILE"
                else
                    echo "OCR failed, PDF will not be searchable"
                fi

                cp "$TEMP_FILE"    "$NC_DIR/$USER/files/Scans/"
                chown -R 33:33     "$NC_DIR/$USER/files/Scans/"
                docker exec -u 33 nextcloud ./occ files:scan --path "$USER/files/Scans/" >&2

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

docker pull jbarlow83/ocrmypdf

mqtt_in | main | mqtt_out
