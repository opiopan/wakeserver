#!/usr/bin/python

import os
import sys
import signal
import time
import json
import requests
from wakeserver import monitoring, plugin

PLUGIN_NAME = "elflet-shadow"
TOPIC = "elflet/shadow"
HTTPTIMEOUT = 10
_shadwos = {}

class ElfletShadow:
    def __init__(self, nodeName, shadowName, power = False, attrs = None):
        self.nodeName = nodeName
        self.shadowName = shadowName
        self.power = power
        self.attrs = attrs

    def updateStaus(self, power, attrs):
        self.power = power
        self.attrs = attrs

    def url(self):
        return "http://" + self.nodeName + "/" + self.shadowName

    def issueIRCommand(self):
        body = {"IsOn": self.power, "Attributes": self.attrs}
        req = requests.Request(self.url(), method = "POST",
                               json = body,
                               tiemout = HTTPTIMEOUT)
        with requests.urlopen(req) as response:
            if response.status_code == requests.codes.ok:
                return True, None
            else:
                return False, response.read().decode("utf-8")
        return False, "fail to POST request to " + self.url()

    def diagnose(self):
        req = requests.Request(self.url(), method = "GET",
                               tiemout = HTTPTIMEOUT)
        with requests.urlopen(req) as response:
            return response.json()
        return None

class Observer:
    def __init__(self, conf):
        a = 0
    
class ElfletShadowPlugin(plugin.Plugin):
    def __init__(self, conf):
        self.conf = conf

def wakeserverPlugin(conf):
    
    return [(PLUGIN_NAME, ElfletShadowPlugin(conf))]
