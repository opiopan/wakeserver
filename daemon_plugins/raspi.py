#!/usr/bin/python

import os
import sys
import time
import json
import subprocess
from wakeserver import monitoring, plugin

PLUGIN_NAME = 'raspi'

#---------------------------------------------------------------------
#  plugin imprementation
#---------------------------------------------------------------------
class RaspiPlugin(plugin.Plugin):

    def __init__(self, conf):
        self.conf = conf

    def diagnose(self, server):
        # this plugin presupposes to use built-in diagnosis function
        return False

    def getAttrs(self, server, keys = None):
        attrs = {}
        for key in keys:
            attrs[key] = None
        return attrs

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        if isOn is not None:
            print('raspi: changing power status is not be supported')
            return False
        option = self.option(server)
        if 'restart-service' in attrs:
            if option is None or not 'user' in option:
                print ('raspi: "user" option must be specified in '
                       '"plugin" section for server [{}]'\
                       .format(server['name']))
                return False
            user = option['user']
            ruser = '{}@'.format(option['ruser']) \
                    if 'ruser' in option else ''
            service = attrs['restart-service']
            cmd = 'sudo systemctl restart {}'.format(service)
            args = ['/var/www/wakeserver/sbin/sussh',
                    user,
                    ruser + server['ipaddr'],
                    cmd]

            nullfile = open("/dev/null")
            proc = subprocess.Popen(args, stderr = subprocess.PIPE,
                                    stdout = subprocess.PIPE,
                                    stdin = nullfile)
            out, err = proc.communicate()
            if proc.returncode != 0:
                print('raspi: an error occurred while restarting '
                      'a service at {0}\n{1}{2}'\
                      .format(server['ipaddr'], out, err))
                return False

            print('raspi: {0} is restarted at {1}'\
                  .format(service, server['ipaddr']))
            return True
        else:
            print('raspi: unsupported attribute specified')
            return False

#---------------------------------------------------------------------
# plugin entry point
#---------------------------------------------------------------------
def wakeserverPlugin(conf):
    return [(PLUGIN_NAME, RaspiPlugin(conf))]
