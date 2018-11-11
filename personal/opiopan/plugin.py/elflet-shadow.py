#!/usr/bin/python

import os
import sys
import signal
import re
import time
import json
import requests
import threading
import paho.mqtt.client as mqtt
from wakeserver import monitoring, plugin

SHADOW_PLUGIN_NAME = "elflet-shadow"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
TOPIC = "elflet/shadow"
HTTPTIMEOUT = 10
DIAG_INTERVAL = 10*60

_shadows = {}
_observer = None
_subscriber = None

#---------------------------------------------------------------------
# utility functions
#---------------------------------------------------------------------
def getNodeNameAndShadowName(addr):
    phost = re.compile(':.*')
    host = phost.sub('', addr)
    pshadow = re.compile('.*:')
    shadow = pshadow.sub('', addr)
    return host, shadow
    
#---------------------------------------------------------------------
# shadow representation class
#---------------------------------------------------------------------
class ElfletShadow:
    def __init__(self, nodeName, shadowName, power = False, attrs = None):
        self.nodeName = nodeName
        self.shadowName = shadowName
        self.power = power
        self.attrs = attrs

    def updateStatus(self, data):
        if "IsOn" in data:
            self.power = data["IsOn"]
            print 'change shadow to {0}'.format(self.power)
        if "Attributes" in data:
            self.attrs =data["Attributes"]
    def url(self):
        return "http://" + self.nodeName + "/shadow/" + self.shadowName

    def issueIRCommand(self):
        body = {"IsOn": self.power, "Attributes": self.attrs}
        try:
            resp = requests.post(self.url(),
                                 json = body,
                                 timeout = HTTPTIMEOUT)
            if resp.status_code == requests.codes.ok:
                return True, None
            else:
                return False, response.read().decode("utf-8")
        except:
            return False, "fail to POST request to " + self.url()

    def diagnose(self):
        try:
            resp = requests.get(self.url(), timeout = HTTPTIMEOUT)
            return resp.json()
        except:
            return None

#---------------------------------------------------------------------
# mqtt subscriber
#---------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    print 'mqtt: connected as code {0}'.format(rc)
    client.subscribe(client.topic)

def on_subscribe(client, userdata, mid, granted_qos):
    print 'mqtt: accepted subscribe topic: {0}'.format(client.topic)
    
def on_message(client, userdata, msg):
    global _shadows
    data = json.loads(msg.payload)
    nodeName = data['NodeName']
    shadowName = data['ShadowName']
    name = nodeName + '.local:' + shadowName
    if not name in _shadows:
        print 'mqtt: unmanaged shadow: {0}'.format(name)
        _shadows[name] = ElfletShadow(nodeName, shadowName)
    _shadows[name].updateStatus(data)
    print 'mqtt: message from {0}'.format(name)

class Subscriber(threading.Thread):
    def __init__(self, conf):
        super(Subscriber, self).__init__()
        self.conf = conf

    def run(self):
        client = mqtt.Client(protocol=mqtt.MQTTv311)
        client.topic = TOPIC
        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_message = on_message
        client.connect('localhost', port=MQTT_PORT, keepalive=MQTT_KEEPALIVE)

        client.loop_forever()
        
#---------------------------------------------------------------------
# observer thread
#---------------------------------------------------------------------
class Observer(threading.Thread):
    def __init__(self, conf):
        global _shadows
        super(Observer, self).__init__()
        self.conf = conf
        print 'elflet: detected shadows:'
        for group in self.conf.servers:
            for server in group["servers"]:
                if server["scheme"]["type"] == SHADOW_PLUGIN_NAME:
                    name = server["ipaddr"]
                    node, shadow = getNodeNameAndShadowName(name)
                    _shadows[name] = ElfletShadow(node, shadow)
                    print '    ' + name
        
    def run(self):
        global _shadows
        while True:
            for name in _shadows.keys():
                print 'checking ' + name
                data = _shadows[name].diagnose()
                if data != None:
                    _shadows[name].updateStatus(data)
                    print data['IsOn']
            time.sleep(DIAG_INTERVAL)
    
#---------------------------------------------------------------------
# elflet shadow plugin imprementation
#---------------------------------------------------------------------
class ElfletShadowPlugin(plugin.Plugin):
    def __init__(self, conf):
        self.conf = conf

    def diagnose(self, server):
        global _shadows
        name = server["ipaddr"]
        if name in _shadows:
            power = _shadows[name].power
            return power
        return False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        global _shadows
        name = server["ipaddr"]
        if name in _shadows:
            shadow = _shadows[name]
            if isOn != None:
                shadow.power = isOn
            if attrs != None:
                shadow.attrs = attrs
            shadow.issueIRCommand()
            return True
        return False

    def getAttrs(self, server, keys = None):
        global _shadows
        name = server["ipaddr"]
        if name in _shadows:
            attrs = _shadows[name].attrs
            if keys and len(keys) > 0:
                res = {}
                for key in keys:
                    if key in attrs:
                        res[key] = attrs[key]
                return res
            else:
                return attrs
        return None
    
#---------------------------------------------------------------------
# plugin entry point
#---------------------------------------------------------------------
def wakeserverPlugin(conf):
    global _observer
    global _subscriber
    
    if  _observer == None:
        _observer = Observer(conf)
        _observer.start()

    if _subscriber == None:
        _subscriber = Subscriber(conf)
        _subscriber.start()
        
    return [(SHADOW_PLUGIN_NAME, ElfletShadowPlugin(conf))]
