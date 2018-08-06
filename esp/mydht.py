import dht
import machine
import mymqtt
import time
import json

def main(pin=4):
    cl = mymqtt.MQTTClient("sensor/%(name)s/")
    cl.connect()

    i = 0

    d = dht.DHT22(machine.Pin(pin))
    while True:
        d.measure()
        print("boop!", i)
        cl.publish("temperature", d.temperature())
        cl.publish("humidity",    d.humidity())
        cl.publish("i",           i)
        i += 1
        cl.check_msg()
        time.sleep(5)
