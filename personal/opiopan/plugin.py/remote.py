#!/usr/bin/python

import os
import sys
import time
import json
import requests
import urllib
from wakeserver import monitoring, plugin

DEBUG = 'DEBUG' in os.environ

PLUGIN_NAME = 'remote'
REMOTE_KEY = 'remote'
HTTPTIMEOUT = 10

#---------------------------------------------------------------------
#  plugin imprementation
#---------------------------------------------------------------------
class RemotePlugin(plugin.Plugin):
    needPolling = False
    
    def __init__(self, conf):
        self.conf = conf

    def diagnose(self, server):
        name = server['name']
        server = monitoring.monitor.serversDict[name] \
                 if name in monitoring.monitor.serversDict else None
        return (server['status'] == 'on') if server else False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        option = self.option(server)
        if REMOTE_KEY in option:
            data = {}
            if isOn != None:
                data['isOn'] = isOn
            if needReboot != None:
                data['reboot'] = needReboot
            if attrs != None:
                data['attributes'] = attrs
            serverName = urllib.quote(server['name'])
            url = 'http://{0}:8081/servers/{1}'.format(option['remote'],
                                                       serverName)
            def proc():
                resp = requests.post(url, json = data, timeout = HTTPTIMEOUT)
                if not resp.status_code == requests.codes.ok:
                    print 'remote: slave returned error ({0})'.format(
                        resp.status_code)
                    return False
                return True

            if DEBUG:
                return proc()
            
            try:
                return proc()
            except:
                print 'remote: fail to access to {0}'.format(url)
                return False
        return False 

    def getAttrs(self, server, keys = None):
        option = self.option(server)
        if REMOTE_KEY in option:
            serverName = urllib.quote(server['name'])
            url = 'http://{0}:8081/servers/{1}'.format(option['remote'],
                                                       serverName)
            try:
                resp = requests.get(url, timeout = HTTPTIMEOUT)
                return resp.json()
            except:
                return None
        return None
    
#---------------------------------------------------------------------
# plugin entry point
#---------------------------------------------------------------------
def wakeserverPlugin(conf):
    return [(PLUGIN_NAME, RemotePlugin(conf))]

