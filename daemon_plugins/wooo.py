#!/usr/bin/python

import os
import sys
import signal
import re
import time
import json
import requests
import subprocess
from wakeserver import monitoring, plugin

PLUGIN_NAME = 'wooo'

ELFLET_KEY = 'elflet'
TRANSFER_KEY = 'transfer'
MODE_KEY = 'mode'
STRICT_POWER_KEY = 'strict-power'

HTTPTIMEOUT = 10

class Command:
    """keep command"""

CMD1 = Command()
CMD1.power = '50af17e8'
CMD1.pauseplay = '56a924db'
CMD1.skipf = '56a925da'
CMD1.skipb = '56a926d9'
CMD1.altskipf = '56a933cc'
CMD1.altskipb = '56a937c8'
CMD1.tv = '56a94ab5'
CMD1.bs = '56a949b6'
CMD1.cs = '56a94cb3'
CMD1.increase = '50af12ed'
CMD1.decrease = '50af15ea'
CMD1.channels = [
    '56a9718e',
    '56a9728d',
    '56a9738c',
    '56a9748b',
    '56a9758a',
    '56a97689',
    '56a97788',
    '56a97887',
    '56a97986',
    '56a9708f',
    '56a97a85',
    '56a97b84',
]
    
CMD2 = Command()
CMD2.power = '50af17e8'
CMD2.pauseplay = '56a924db'
CMD2.skipf = '56a925da'
CMD2.skipb = '56a926d9'
CMD2.altskipf = '56a933cc'
CMD2.altskipb = '56a937c8'
CMD2.tv = '56a94ab5'
CMD2.bs = '56a949b6'
CMD2.cs = '56a94cb3'
CMD2.increase = '50af12ed'
CMD2.decrease = '50af15ea'
CMD2.channels = [
    '56a9718e',
    '56a9728d',
    '56a9738c',
    '56a9748b',
    '56a9758a',
    '56a97689',
    '56a97788',
    '56a97887',
    '56a97986',
    '56a9708f',
    '56a97a85',
    '56a97b84',
]

#---------------------------------------------------------------------
# plugin option
#---------------------------------------------------------------------
class Option:
    def __init__(self, option):
        if option:
            self.elflet = option[ELFLET_KEY] if ELFLET_KEY in option else None
            transfer = option[TRANSFER_KEY] if TRANSFER_KEY in option else None
            self.useIrtx = True if transfer == 'irtx' else None
            mode = option[MODE_KEY] if MODE_KEY in option else 1
            self.command = CMD2 if mode == 2 else CMD1
            self.strictPower = option[STRICT_POWER_KEY] \
                               if STRICT_POWER_KEY in option else False
        else:
            self.elflet = None
        if not self.elflet:
            print 'wooo: elflet address is not specified for {0}'.format(
                server['name']
            )

#---------------------------------------------------------------------
# command sending function
#---------------------------------------------------------------------
class Controller:
    def __init__(self, option):
        self.option = option

    def issue(self, cmd):
        if not self.option.elflet:
            return False
        
        print 'wooo: command: {0}'.format(cmd)
        if self.option.useIrtx:
            args = ['irtx', self.option.elflet, 'nec', cmd]
            proc = subprocess.Popen(args)
            return proc.wait() == 0
        else:
            data = {
                'FormatedIRStream': {
                    'Protocol': 'NEC',
                    'Data': cmd
                }
            }
            url = 'http://{0}/irrc/send'.format(self.option.elflet)
            try:
                resp = requests.post(url, json = data, timeout = HTTPTIMEOUT)
                return resp.status_code == requests.code.ok
            except:
                print 'wooo: failed to access REST interface of {0}'\
                    .format(self.option.elflet)
                return False

    def togglePower(self):
        return self.issue(self.option.command.power)

    def setChannel(self, channelIn):
        channel = int(channelIn)
        if channel < 1 or channel > 12:
            print 'wooo: unsupported channel number was specified: {0}'\
                .format(channel)
            return False
        cmd = self.option.command.channels[channel - 1]
        return self.issue(cmd)

    def setBand(self, band):
        if band == 'terrestrial':
            cmd = self.option.command.tv
        elif band == 'bs':
            cmd = self.option.command.bs
        elif band == 'cd':
            cmd = self.option.command.cs
        else:
            return False
        return self.issue(cmd)

    def setChannelName(self, name):
        parts = name.split('-')
        if len(parts) != 2:
            return False

        band = parts[0]
        num = int(parts[1])
        precmd = None
        precmd2 = None
        suffix = None

        if band == 'TV':
            suffix = self.option.command.tv
        elif band == 'BS':
            precmd = self.option.command.tv
            suffix = self.option.command.bs
        elif band == 'BS2':
            precmd = self.option.command.tv
            precmd2 = self.option.command.bs
            suffix = self.option.command.bs
        elif band == 'CS':
            suffix = self.option.command.cs
        else:
            return False
        if num < 1 or num > 12:
            return False

        if precmd:
            self.issue(precmd)
            time.sleep(0.3)
            if precmd2:
                time.sleep(0.3)
                self.issue(precmd2)
                time.sleep(0.3)
        self.issue(suffix)
        time.sleep(0.3)
        
        return self.setChannel(num)

    def setPlayer(self, type):
        if type == 'pauseplay':
            cmd = self.option.command.pauseplay
        elif type == 'skipf':
            cmd = self.option.command.skipf
        elif type == 'skipb':
            cmd = self.option.command.skipb
        elif type == 'altskipf':
            cmd = self.option.command.altskipf
        elif type == 'altskipb':
            cmd = self.option.command.altskipb
        else:
            return False
        return self.issue(cmd)

    def setVolumeRelative(self, direction):
        if direction == 'increase':
            cmd = self.option.command.increase
        elif direction == 'decrease':
            cmd = self.option.command.decrease
        else:
            return False
        return self.issue(cmd)
            
#---------------------------------------------------------------------
# wooo plugin imprementation
#---------------------------------------------------------------------
class WoooPlugin(plugin.Plugin):
    def __init__(self, conf):
        self.conf = conf

    def diagnose(self, server):
        name = server['name']
        server = monitoring.monitor.serversDict[name] \
                 if name in monitoring.monitor.serversDict else None
        return (server['status'] == 'on') if server else False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        option = Option(self.option(server))
        controller = Controller(option)

        if (isOn != None):
            if self.diagnose(server) == isOn and option.strictPower:
                print 'wooo: changing power state is not necessary'
                return False
            if not  controller.togglePower():
                return False

        for key in (attrs if attrs else {}):
            if key == 'tvchannel':
                if not controller.setChannel(attrs[key]):
                    return False
            elif key == 'tvchannelname':
                if not controller.setChannelName(attrs[key]):
                    return False
            elif key == 'player':
                if not controller.setPlayer(attrs[key]):
                    return False
            elif key == 'volumerelative':
                if not controller.setVolumeRelative(attrs[key]):
                    return False
        return True

    def getAttrs(self, server, keys = None):
        if not keys:
            keys = ['tvchannel', 'tvchannelname', 'player', 'volumerelative']
        rc = {}
        for key in keys:
            if key == 'tvchannel':
                rc[key] = 99
            else:
                rc[key] = 'unknown'
        return rc 

#---------------------------------------------------------------------
# plugin entry point
#---------------------------------------------------------------------
def wakeserverPlugin(conf):
   return [(PLUGIN_NAME, WoooPlugin(conf))]
