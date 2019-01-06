#!/usr/bin/python

import os
import sys
import signal
import time
import json
from wakeserver import monitoring, plugin, cecmonitor

PLUGIN_NAME = 'cec-device'
DEVICE_KEY = 'device-num'
            
#---------------------------------------------------------------------
# regza plugin imprementation
#---------------------------------------------------------------------
class CECPlugin(plugin.Plugin):
    def __init__(self, conf):
        self.conf = conf

    def diagnose(self, server):
        name = server['name']
        server = monitoring.monitor.serversDict[name] \
                 if name in monitoring.monitor.serversDict else None
        return (server['status'] == 'on') if server else False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        option = self.option(server)
        if isOn != None:
            if option and DEVICE_KEY in option and cecmonitor.controller:
                device = int(option[DEVICE_KEY])
                rc = cecmonitor.controller.powerOn(device) \
                     if isOn else cecmonitor.controller.powerOff(device)
                if not rc:
                    return False
        if attrs != None:
            return False
                
        return True

    def getAttrs(self, server, keys = None):
        rc = {}
        for key in (keys if keys else []):
            rc[key] = None
        return rc 

#---------------------------------------------------------------------
# plugin entry point
#---------------------------------------------------------------------
def wakeserverPlugin(conf):
   return [(PLUGIN_NAME, CECPlugin(conf))]
