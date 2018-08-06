import dht
import machine
import mymqtt
import time
import json

def main():
    cl = mymqtt.MQTTClient("sensor/%(name)s/")
    cl.connect()
    i = 0

    d = dht.DHT22(machine.Pin(4))
    while True:
        d.measure()
        print("boop!", i)
        cl.publish("temperature", d.temperature())
        cl.publish("humidity",    d.humidity())
        cl.publish("i",           i)
        i += 1
        cl.check_msg()
        time.sleep(5)
