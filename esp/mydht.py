# requires https://github.com/pycom/pycom-libraries/blob/master/lib/mqtt/mqtt.py

import dht
import machine
import mqtt
import time
import json
import ubinascii

def mqtt_configure():
    sensor    = input("Sensor name: ")
    broker    = input("Broker address: ")
    username  = input("Username: ")
    password  = input("Password: ")
    with open("mqtt.json", "wb") as fd:
        json.dump({
            "sensor": sensor,
            "broker": broker,
            "username": username,
            "password": password
        }, fd)

def mqtt_cb(*args):
    print("Recv!", args)

def main():
    client_id = ubinascii.hexlify(machine.unique_id())
    with open("mqtt.json", "rb") as fd:
        conf = json.load(fd)

    cl = mqtt.MQTTClient(client_id, conf["broker"], user=conf["username"], password=conf["password"])
    cl.set_callback(mqtt_cb)
    cl.connect()
    i = 0

    cl.subscribe("outTopic")
    cl.sock.settimeout(1)

    last_msmt = 0

    d = dht.DHT22(machine.Pin(4))
    while True:
        now = time.time()
        if now > last_msmt + 5:
            d.measure()
            print("boop!", i)
            cl.publish("sensor/%s/temperature" % conf["sensor"], str(d.temperature()))
            cl.publish("sensor/%s/humidity"    % conf["sensor"], str(d.humidity()))
            cl.publish("sensor/%s/i"           % conf["sensor"], str(i))
            i += 1
            last_msmt = now + 5
        try:
            cl.wait_msg()
        except OSError as err:
            if err.args[0] == 110:
                continue
            else:
                raise


# curl("http://192.168.0.168/mydht.py", "mydht.py", 8000)
