import dht
import machine
import mymqtt
import time
import json

def main(pin=4):
    cl = mymqtt.MQTTClient()
    cl.connect()

    i = 0

    d = dht.DHT22(machine.Pin(pin))
    while True:
        d.measure()
        print("boop!", i)
        cl.publish("sensor/%(name)s/temperature", d.temperature())
        cl.publish("sensor/%(name)s/humidity",    d.humidity())
        cl.publish("sensor/%(name)s/i",           i)
        i += 1
        time.sleep(5)
