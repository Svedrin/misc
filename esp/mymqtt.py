# requires https://github.com/pycom/pycom-libraries/blob/master/lib/mqtt/mqtt.py

import machine
import ubinascii
import json
import mqtt


def configure():
    conf = {}
    try:
        with open("mqtt.json", "rb") as fd:
            conf.update(json.load(fd))
        print("Loaded old config successfully. To discard it and start over, delete mqtt.json.")
    except:
        print("Config does not exist or is not valid JSON.")
        pass

    conf["name"]      = input("Device name:    [%s] " % conf.get("name",     '')) or conf.get("name",     '')
    conf["broker"]    = input("Broker address: [%s] " % conf.get("broker",   '')) or conf.get("broker",   '')
    conf["username"]  = input("Username:       [%s] " % conf.get("username", '')) or conf.get("username", '')
    conf["password"]  = input("Password:       [%s] " % conf.get("password", '')) or conf.get("password", '')

    with open("mqtt.json", "wb") as fd:
        json.dump(conf, fd)


class MQTTClient(mqtt.MQTTClient):
    def __init__(self, namespace):
        with open("mqtt.json", "rb") as fd:
            conf = json.load(fd)

        self.namespace = namespace % conf
        self.client_id = ubinascii.hexlify(machine.unique_id())
        mqtt.MQTTClient.__init__(self, self.client_id, conf["broker"], user=conf["username"], password=conf["password"])

    def publish(self, topic, value):
        mqtt.MQTTClient.publish(self, self.namespace + topic, str(value))