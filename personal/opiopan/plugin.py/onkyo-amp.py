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
import Queue
import binascii
from wakeserver import monitoring, plugin

PLUGIN_NAME = 'onkyo-amp'
AMPCONTROL_PORT = 60128
KEEPALIVE_INTERVAL = 30
RECIEVE_TIMEOUT = 5

VOLUME_KEY = "volume"
SELECTOR_KEY = "selector"

LOG             = '/run/wakeserver/onkyo-amp.status.new'
LOG_ORG         = '/run/wakeserver/onkyo-amp.status'

DEBUG = 'DEBUG' in os.environ

#---------------------------------------------------------------------
# ISCP packet encoder/decoder
#---------------------------------------------------------------------
class ATTR:
    power = '!1PWR'
    volume = '!1MVL'
    selector = '!1SLI'

class Command:
    HEADER_LENGTH = 16
    HEADER = struct.Struct('!4sii4s')
    PREFIX = 'ISCP'
    SUFFIX = '\x01\x00\x00\x00'

    OK = 0
    TOO_SHORT = -1
    INVALID_FORMAT = -2

    def __init__(self, kind = None, value =None):
        self.kind = kind
        self.value = value

    def recognize(self, buf, offset = 0, size = None):
        if size == None:
            size = len(buf) - offset

        if size < self.HEADER_LENGTH:
            return TOO_SHORT, None

        prefix, hlen, dlen, suffix = self.HEADER.unpack_from(buf, offset)
        if prefix != self.PREFIX or hlen != self.HEADER_LENGTH:
            print binascii.b2a_hex(buf[offset:])
            print 'prefix: {0} / hlen: {1}'.format(
                binascii.b2a(prefix), hlen)
            return self.INVALID_FORMAT, None
        if self.HEADER_LENGTH + dlen < size:
            return self.TOO_SHORT, None
        kind, value = struct.unpack_from('5s' + str(dlen - 5 - 3) + 's',
                                         buf, offset + hlen)

        self.applyAttribute(kind, value)
        return self.OK, hlen + dlen

    def applyAttribute(self, kind, value):
        self.kind = kind
        if kind == ATTR.power:
            self.value = (value == '01')
        elif kind == ATTR.volume:
            self.value = int(value, 16)
        elif kind == ATTR.selector:
            self.value = int(value, 16)
        else:
            self.kind = None
            self.value = None

    def serialize(self):
        if self.value != None:
            if self.kind == ATTR.power:
                value = '01' if self.value else '00'
            elif self.kind == ATTR.volume or self.kind == ATTR.selector:
                value = format(self.value, '02X')
            else:
                return None
        else:
            if self.kind == ATTR.power or self.kind == ATTR.volume or \
               self.kind == ATTR.selector:
                value = 'QSTN'
            else:
                return None

        data = self.kind + value + '\n'

        return self.HEADER.pack(self.PREFIX, self.HEADER_LENGTH,
                                len(data), self.SUFFIX) + data

#---------------------------------------------------------------------
# ISCP reciever / sender
#---------------------------------------------------------------------
class Reciever(threading.Thread):
    def __init__(self, controller):
        super(Reciever, self).__init__()
        self.controller = controller
        self.time = time.time()

    def run(self):
        def proc():
            data = None
            cmd = Command()
            while True:
                buf = self.controller.sock.recv(4096)
                if not buf:
                    print 'ISCP: connection closed from amplifier'
                    self.controller.resetConnection()
                    return
                self.time = time.time()
                data = data + buf if data else buf
                pos = 0
                rc = cmd.OK
                while rc == cmd.OK and len(data) > pos:
                    rc, pktlen = cmd.recognize(data, pos)
                    if rc == cmd.OK:
                        pos += pktlen
                        self.controller.applyCommand(cmd)
                    elif rc == cmd.INVALID_FORMAT:
                        print 'ISCP: protocol error'
                        self.controller.resetConnection()
                        return
                if pos == len(data):
                    pos = 0
                    data = None
                else:
                    data = data[pos:]
                    pos = 0

        if DEBUG:
            proc()
            return
                    
        try:
            proc()
        except:
            print 'ISCP: recieve error'
            self.controller.resetConnection()

class Sender(threading.Thread):
    class Terminator:
        dummy = None
    terminator = Terminator()
    
    def __init__(self, controller):
        super(Sender, self).__init__()
        self.controller = controller
        self.cmdQueue = Queue.Queue()
        self.time = time.time()

    def send(self, cmd):
        self.cmdQueue.put(cmd)

    def terminate(self):
        self.cmdQueue.put(self.terminator)

    def run(self):
        while True:
            cmd = self.cmdQueue.get()
            if cmd is self.terminator:
                return
            try:
                data = cmd.serialize()
                self.controller.sock.sendall(data)
                self.time = time.time()
                #time.sleep(0.01)
            except:
                print 'ISCP: send error'
                self.controller.resetConnection()
                return

#---------------------------------------------------------------------
# onkyo amplifier controller
#---------------------------------------------------------------------
class PHASE:
    notconnected = 0
    connected = 1
    keepalive = 2
    shuttingdown = 3

class Controller(threading.Thread):
    def __init__(self, server):
        super(Controller, self).__init__()
        self.addr= server["ipaddr"]
        self.serverName = server["name"]
        option = server['plugin-option'] if 'plugin-option' in server else None
        self.tvName = option['tv-name'] \
                      if option and 'tv-name' in option else None
        self.tvSelector = option['tv-selector'] \
                          if option and 'tv-selector' in option else None
        self.power = None
        self.volume = None
        self.selector = None
        self.phase = PHASE.notconnected
        self.sock = None
        self.sockError = False
        self.resetEvent = threading.Event()
        self.resetEvent.clear()
        self.sender = None
        self.reciever = None

    def resetConnection(self):
        self.sockError = True
        self.resetEvent.set()

    def applyCommand(self, cmd):
        reflectToTV = False
        if cmd.kind == ATTR.power:
            print 'ISCP: power = {0}'.format(cmd.value)
            old = self.power
            self.power = cmd.value
            reflectToTV = True
            if monitoring.monitor:
                monitoring.monitor.setStatus(self.serverName, self.power)
            if self.power != old:
                self.updateLog()
        elif cmd.kind == ATTR.volume:
            print 'ISCP: volume = {0}'.format(cmd.value)
            self.volume = cmd.value
        elif cmd.kind == ATTR.selector:
            print 'ISCP: selector = {0}'.format(cmd.value)
            self.selector = cmd.value
            self.updateLog()
            if monitoring.monitor:
                monitoring.monitor.setStatus(self.serverName, self.power)
            reflectToTV = True
        if reflectToTV and self.tvName and self.tvSelector:
            status = self.power and self.selector == self.tvSelector
            if monitoring.monitor:
                monitoring.monitor.setStatus(self.tvName, status)

    def updateLog(self):
        if self.power == None or self.selector == None:
            return
        
        with open(LOG, 'w') as log:
            if self.power:
                print >> log, 'on !1SLI{:02X}'.format(self.selector)
                print 'ISCP: on -> log'
            else:
                print >> log, 'off'
                print 'ISCP: off -> log'
        os.rename(LOG, LOG_ORG)

    def setStatus(self, power = None, volume = None, selector = None):
        if not self.sender:
            return False
        
        if power != None:
            self.sender.send(Command(ATTR.power, power))
        if volume != None:
            self.sender.send(Command(ATTR.volume, volume))
        if selector != None:
            self.sender.send(Command(ATTR.selector, selector))
        return True
        
    def schedule(self):
        if self.phase == PHASE.notconnected:
            try:
                self.resetEvent.clear()
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.addr, AMPCONTROL_PORT))
                print 'ISCP: connected to ' + self.addr
                self.sender = Sender(self)
                self.reciever = Reciever(self)
                self.sender.start()
                self.reciever.start()
                self.sender.send(Command(ATTR.power))
                self.sender.send(Command(ATTR.selector))
                self.sender.send(Command(ATTR.volume))
                self.phase = PHASE.connected
            except:
                print 'ISCP: cannot connect to amplifier, reconnect in 10 sec.'
                time.sleep(10)
                
        elif self.phase == PHASE.connected:
            if self.resetEvent.wait(10):
                print 'ISCP: reset request is accepted'
                self.phase = PHASE.shuttingdown
            elif self.reciever.time > self.sender.time and \
                 time.time() - self.reciever.time > KEEPALIVE_INTERVAL:
                self.phase = PHASE.keepalive
            elif self.reciever.time < self.sender.time and \
                 time.time() - self.sender.time > RECIEVE_TIMEOUT:
                print 'ISCP: response timeout'
                self.phase = PHASE.shuttingdown
                
        elif self.phase == PHASE.keepalive:
            self.sender.send(Command(ATTR.power))
            self.sendTime = time.time()
            self.phase = PHASE.connected

        elif self.phase == PHASE.shuttingdown:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sender.terminate()
            self.sender.join()
            self.reciever.join()
            self.sender = None
            self.reciever = None
            self.sock.close()
            self.sock = None
            self.phase = PHASE.notconnected
            print 'ISCP: disconnected, reconnect in 5 sec.'
            time.sleep(5)
            
    def run(self):
        time.sleep(2)
        while True:
            self.schedule()

#---------------------------------------------------------------------
# plugin imprementation
#---------------------------------------------------------------------
class OnkyoAmpPlugin(plugin.Plugin):
    needPolling = False
    
    def __init__(self, conf):
        self.conf = conf
        self.controllers = {}
        print 'onkyo-amp: detected devices:'
        for group in self.conf.servers:
            for server in group["servers"]:
                if server["scheme"]["type"] == PLUGIN_NAME:
                    addr = server["ipaddr"]
                    serverName = server["name"]
                    controller = Controller(server)
                    self.controllers[addr] = controller
                    controller.start()
                    print '    ' + addr

    def diagnose(self, server):
        addr = server["ipaddr"]
        if addr in self.controllers:
            controller = self.controllers[addr]
            return controller.power
        else:
            return False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        addr = server["ipaddr"]
        if addr in self.controllers:
            controller = self.controllers[addr]
            volume = None
            selector = None
            if attrs:
                if VOLUME_KEY in attrs:
                    volume = int(attrs[VOLUME_KEY])
                if SELECTOR_KEY in attrs:
                    selector = int(attrs[SELECTOR_KEY])
            controller.setStatus(isOn, volume, selector)
            return True
        else:
            return False

    def getAttrs(self, server, keys = None):
        if not keys:
            keys = [VOLUME_KEY, SELECTOR_KEY]
        addr = server["ipaddr"]
        if addr in self.controllers:
            controller = self.controllers[addr]
            rc = {}
            for key in keys:
                if key == VOLUME_KEY:
                    rc[key] = controller.volume \
                              if controller.volume else 0
                if key == SELECTOR_KEY:
                    rc[key] = controller.selector \
                              if controller.selector else 0
            return rc
        else:
            return None

#---------------------------------------------------------------------
# plugin entry point
#---------------------------------------------------------------------
_plugin = None

def wakeserverPlugin(conf):
    global _plugin
    _plugin = OnkyoAmpPlugin(conf)
    return [(PLUGIN_NAME, _plugin)]
