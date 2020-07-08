#!/usr/bin/env python3

from uuid import uuid4
from time import sleep

import json
import socket
import subprocess
import paho.mqtt.client as mqtt

def main():
    client_id = socket.gethostname()
    client = mqtt.Client(client_id=client_id)
    client.username_pw_set("user", "password")

    while True:
        try:
            client.connect("mqtt", 1883)
        except OSError:
            sleep(1)
        else:
            break

    try:
        while True:
            proc = subprocess.Popen(["/bin/ehzpoll", "/dev/ttyUSB0"], stdout=subprocess.PIPE)
            out, err = proc.communicate()
            try:
                data = json.loads(out.decode("UTF-8"))
            except ValueError:
                # Ignore failed readings, we'll get another one in three seconds anyway
                continue
            else:
                for key, val in data.items():
                    topic = "powergrid/%s/%s" % (client_id, key)
                    client.publish(topic, str(val))
                sleep(25)
    except KeyboardInterrupt:
        print("Got ^C, shutting down")

    client.disconnect()

if __name__ == '__main__':
    main()
