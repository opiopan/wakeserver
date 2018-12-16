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

PLUGIN_NAME = 'regza'

ELFLET_KEY = 'elflet'
TRANSFER_KEY = 'transfer'
MODE_KEY = 'mode'
STRICT_POWER_KEY = 'strict-power'

HTTPTIMEOUT = 10

class Command:
    """keep command"""

CMD1 = Command()
CMD1.power = '40BF12ED'
CMD1.channel = '40BF'
CMD1.pauseplay = '40BD50AF'
CMD1.skipf = '40BE26D9'
CMD1.skipb = '40BE27D8'
CMD1.altskipf = '40BE23DC'
CMD1.altskipb = '40BE22DD'
CMD1.tv = '40BF7A85'
CMD1.bs = '40BF7C83'
CMD1.cs = '40BF7D82'
CMD1.increase = '40BF1AE5'
CMD1.decrease = '40BF1EE1'
    
CMD2 = Command()
CMD2.power = '40BD12ED'
CMD2.channel = '40BD'
CMD2.pauseplay = '40BD50AF'
CMD2.skipf = '40BC26D9'
CMD2.skipb = '40BC27D8'
CMD2.altskipf = '40BC23DC'
CMD2.altskipb = '40BC22DD'
CMD2.tv = '40BD7A85'
CMD2.bs = '40BD7C83'
CMD2.cs = '40BD7D82'
CMD2.increase = '40BD1AE5'
CMD2.decrease = '40BD1EE1'

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
            print 'regza: elflet address is not specified for {0}'.format(
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
                print 'regza: failed to access REST interface of {0}'\
                    .format(self.option.elflet)
                return False

    def togglePower(self):
        return self.issue(self.option.command.power)

    def setChannel(self, channelIn):
        channel = int(channelIn)
        if channel < 1 or channel > 12:
            print 'regza: unsupported channel number was specified: {0}'\
                .format(channel)
            return False
        cmd = self.option.command.channel + format(channel, '02x') \
              + format(~channel & 0xff, '02x')
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
            time.sleep(0.1)
            if precmd2:
                time.sleep(0.1)
                self.issue(precmd2)
                time.sleep(0.2)
        self.issue(suffix)
        time.sleep(0.1)
        
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
# regza plugin imprementation
#---------------------------------------------------------------------
class RegzaPlugin(plugin.Plugin):
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
                print 'regza: changing power state is not necessary'
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
   return [(PLUGIN_NAME, RegzaPlugin(conf))]
