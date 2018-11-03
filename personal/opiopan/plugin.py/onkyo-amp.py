import os
import sys
import signal
import re
import time
import json
import requests
import threading
import socket
import struct
from wakeserver import monitoring, plugin

PLUGIN_NAME='onkyo-amp-new'

class PHASE:
    notconnected = 0
    connected = 1
    error = 2
    shuttingdown = 3

#---------------------------------------------------------------------
# onkyo amplifier controller
#---------------------------------------------------------------------
class Controller(threading.Thread):
    def __init__(self, addr):
        super(addr, self).__init__()
        self.addr= addr
        self.volume = None
        self.selector = None
        self.phase = PHASE.notconnected
        self.sock = None

    def schedule(self):
        if self.phase == PHASE.notconnected:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


#---------------------------------------------------------------------
# plugin imprementation
#---------------------------------------------------------------------
class OnkyoAmpPlugin(plugin.Plugin):
    def __init__(self, conf):
        self.conf = conf

    def diagnose(self, server):
        return False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        return False

    def getAttrs(self, server, keys = None):
        return None


#---------------------------------------------------------------------
# plugin entry point
#---------------------------------------------------------------------
def wakeserverPlugin(conf):
    return [(PLUGIN_NAME, OnkyoAmpPlugin(conf))]
