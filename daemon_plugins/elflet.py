#!/usr/bin/python

import os
import sys
import traceback
import signal
import re
import email.utils
import time
import datetime
import pytz
import json
import requests
import threading
import paho.mqtt.client as mqtt
from wakeserver import monitoring, plugin

DEBUG = 'DEBUG' in os.environ

SHADOW_PLUGIN_NAME = "elflet-shadow"
IR_PLUGIN_NAME = "elflet-ir"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
SHADOW_TOPIC = "elflet/shadow"
SENSOR_TOPIC = "elflet/sensor"
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
    def __init__(self, nodeName, shadowName, power = False, attrs = None, \
                 serverName = None):
        self.nodeName = nodeName
        self.shadowName = shadowName
        self.power = power
        self.attrs = attrs
        self.serverName = serverName
        if self.serverName and monitoring.monitor:
            monitoring.monitor.setStatus(self.serverName, self.power)
            

    def updateStatus(self, data):
        if "IsOn" in data:
            self.power = data["IsOn"]
            print 'elflet: change shadow to {0}'.format(self.power)
            if self.serverName and monitoring.monitor:
                monitoring.monitor.setStatus(self.serverName, self.power)
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
    print 'elflet-mqtt: connected as code {0}'.format(rc)
    client.subscribe(SHADOW_TOPIC)
    client.subscribe(SENSOR_TOPIC)

def on_subscribe(client, userdata, mid, granted_qos):
    print 'elflet-mqtt: accepted subscribe topic: {0}'.format(client.topic)
    
def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    if msg.topic == SHADOW_TOPIC:
        global _shadows
        nodeName = data['NodeName']
        shadowName = data['ShadowName']
        name = nodeName + '.local:' + shadowName
        if not name in _shadows:
            print 'elflet-mqtt: unmanaged shadow: {0}'.format(name)
            _shadows[name] = ElfletShadow(nodeName, shadowName)
        print 'elflet-mqtt: shadow message from {0}'.format(name)
        _shadows[name].updateStatus(data)
    elif msg.topic == SENSOR_TOPIC:
        try:
            nodeName = data['NodeName']
            date = data['date']
            temperature = float(data['temperature'])
            humidity = float(data['humidity'])
            pressure = float(data['pressure'])
            tm = email.utils.parsedate(date)
            ts = time.mktime(tm)
            dtl = datetime.datetime.fromtimestamp(ts)
            dt = pytz.utc.localize(dtl)
            if monitoring.monitor:
                monitoring.monitor.updateRoomEnv(
                    nodeName, dt, temperature, humidity, pressure)
            print('elflet-mqtt: sensor message from {0}: '
                  '{1}deg, {2}%, {3}hPa'.format(
                      nodeName, temperature, humidity, pressure))
        except:
            print(traceback.format_exc())

class Subscriber(threading.Thread):
    def __init__(self, conf):
        super(Subscriber, self).__init__()
        self.conf = conf

    def run(self):
        time.sleep(1)
        
        client = mqtt.Client(protocol=mqtt.MQTTv311)
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
                    serverName = server["name"]
                    node, shadow = getNodeNameAndShadowName(name)
                    _shadows[name] = ElfletShadow(node, shadow,
                                                  serverName = serverName)
                    print '    ' + name
        
    def run(self):
        global _shadows
        time.sleep(1)
        while True:
            for name in _shadows.keys():
                print 'elflet: checking ' + name
                data = _shadows[name].diagnose()
                if data != None:
                    print 'elflet: {0} = {1}'.format(name, data['IsOn'])
                    _shadows[name].updateStatus(data)
            time.sleep(DIAG_INTERVAL)
    
#---------------------------------------------------------------------
# elflet shadow plugin imprementation
#---------------------------------------------------------------------
class ElfletShadowPlugin(plugin.Plugin):
    needPolling = False
    
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
# elflet IR plugin imprementation
#---------------------------------------------------------------------
ELFLET_KEY = 'elflet'
TRANSFER_KEY = 'transfer'
PROTOCOL_KEY = 'protocol'
ON_BITCOUNT_KEY = 'on-bitcount'
ON_CODE_KEY = 'on-code'
OFF_BITCOUNT_KEY = 'off-bitcount'
OFF_CODE_KEY = 'off-code'

class IrOption:
    def __init__(self, server, option):
        if option:
            self.elflet = option[ELFLET_KEY] if ELFLET_KEY in option else None
            transfer = option[TRANSFER_KEY] if TRANSFER_KEY in option else None
            self.useIrtx = True if transfer == 'irtx' else None
            self.protocol = option[PROTOCOL_KEY] \
                            if PROTOCOL_KEY in option else None
            if ON_CODE_KEY in option:
                self.onCode = option[ON_CODE_KEY]
                self.onBitCount = option[ON_BITCOUNT_KEY] \
                                  if ON_BITCOUNT_KEY in option \
                                     else len(onCode) * 4
            if OFF_CODE_KEY in option:
                self.offCode = option[OFF_CODE_KEY]
                self.offBitCount = option[OFF_BITCOUNT_KEY] \
                                  if OFF_BITCOUNT_KEY in option \
                                     else len(offCode) * 4
            else:
                self.offCode = self.onCode
                self.offBitCount = self.onBitCount
        else:
            self.elflet = None
            self.protocol = None
            self.onCode = None
        if not self.elflet or not self.protocol or not self.onCode:
            self.elflet = None
            print 'elflet-ir: mandatory plugin '\
                  'options are not specified for  {0}'.format(server['name'])

class ElfletIrPlugin(plugin.Plugin):
    
    def __init__(self, conf):
        self.conf = conf

    def diagnose(self, server):
        return False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        if attrs != None and len(attrs) > 0:
            return False
        if isOn != None:
            option = IrOption(server, self.option(server))
            return self.issue(option, isOn)
        
        return True

    def getAttrs(self, server, keys = None):
        return None

    def issue(self, option, isOn):
        if not option.elflet:
            return False
        code = option.onCode if isOn else option.offCode
        bits = option.onBitCount if isOn else option.offCode
        if option.useIrtx:
            args = ['irtx', '-b', str(bits), option.elflet,
                    option.protocol.lower(), code]
            proc = subprocess.Popen(args)
            return proc.wait() == 0
        else:
            data = {
                'FormatedIRStream': {
                    'Protocol': option.protocol.upper(),
                    'BitCount': bits,
                    'Data': code
                }
            }
            url = 'http://{0}/irrc/send'.format(option.elflet)
            def proc():
                resp = requests.post(url, json = data, timeout = HTTPTIMEOUT)
                if resp.status_code != requests.codes.ok:
                    print 'elflet-ir: elflet returned error ({0})'.format(
                        resp.status_code)
                    return False
                return True

            if DEBUG:
                return proc()
            
            try:
                return proc()
            except:
                print 'elflet: failed to access REST interface of {0}'\
                    .format(self.option.elflet)
                return False
    
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
        
    return [
        (SHADOW_PLUGIN_NAME, ElfletShadowPlugin(conf)),
        (IR_PLUGIN_NAME, ElfletIrPlugin(conf))
    ]
