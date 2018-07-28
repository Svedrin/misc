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

def main():
    client_id = ubinascii.hexlify(machine.unique_id())
    with open("mqtt.json", "rb") as fd:
        conf = json.load(fd)

    cl = mqtt.MQTTClient(client_id, conf["broker"], user=conf["username"], password=conf["password"])
    cl.connect()
    i = 0

    d = dht.DHT22(machine.Pin(4))
    while True:
        d.measure()
        print("boop!", i)
        cl.publish("sensor/%s/temperature" % conf["sensor"], str(d.temperature()))
        cl.publish("sensor/%s/humidity"    % conf["sensor"], str(d.humidity()))
        cl.publish("sensor/%s/i"           % conf["sensor"], str(i))
        i += 1
        cl.check_msg()
        time.sleep(5)


# curl("http://192.168.0.168:8000/mydht.py", "mydht.py")
