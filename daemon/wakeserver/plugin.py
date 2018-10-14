#!/usr/bin/python

import os
import sys
import time
import importlib

DEBUG = 'DEBUG' in os.environ

PLUGIN_DIR = "/var/www/wakeserver/plugin.py"
PLUGIN_OLD_DIR = "/var/www/wakeserver/plugin"
DIAG_INTERVAL = 1

class Plugin:
    def diagnose(self, server):
        return False
    
    def setPower(self, server, isOn, needReboot = False):
        return False, "This plugin object is not concrete object"

    def attribute(self, server, name, value):
        return False, "This plugin object is not concrete object"

class _OldPlugin(Plugin):
    def __init__(self, name):
        self.name = name
        
    def diagnose(self, server):
        try:
            cmd = "%s/%s diag '%s' '%s' %d" % \
                  (PLUGIN_OLD_DIR, 
                   self.name,
                   server["ipaddr"], server["macaddr"],
                   DIAG_INTERVAL)
            btime = time.time()
            rc = os.system(cmd) == 0
            interval = time.time() - btime
            if interval < DIAG_INTERVAL:
                time.sleep(DIAG_INTERVAL - interval)
            return rc
        except:
            print "OldPlugin(" + self.name + ") raise exception"
            return False

class _Proxy(Plugin):
    def __init__(self, name, obj):
        self.name = name
        self.origin = obj
        
    def diagnose(self, server):
        if DEBUG:
            btime = time.time()
            rc = self.origin.diagnose(server)
            interval = time.time() - btime
            if interval < DIAG_INTERVAL:
                time.sleep(DIAG_INTERVAL - interval)
            return rc
        try:
            btime = time.time()
            rc = self.origin.diagnose(server)
            interval = time.time() - btime
            if interval < DIAG_INTERVAL:
                time.sleep(DIAG_INTERVAL - interval)
            return rc
        except:
            print "Plugin(" + self.name + ") raise exception"
            return False

    def setPower(self, server, isOn, needReboot = False):
        if DEBUG:
            return self.origin.setPower(server, isOn, needReboot)
        try:
            return self.origin.setPower(server, isOn, needReboot)
        except:
            msg = "Plugin(" + self.name + ") raise exception"
            print msg
            return False, msg

    def attribute(self, server, name, value):
        if DEBUG:
            return self.origin.attribute(server, name, value)
        try:
            return self.origin.attribute(server, name, value)
        except:
            msg = "Plugin(" + self.name + ") raise exception"
            print msg
            return False, msg
    
class PluginPool:
    def __init__(self, conf):
        self.conf = conf

        pluginDir = PLUGIN_DIR
        if 'PLUGIN' in os.environ:
            pluginDir = os.environ['PLUGIN']

        sys.path.append(pluginDir)

        self.plugins = {}
        if os.path.isdir(pluginDir):
            files = os.listdir(pluginDir)
            for fname in files:
                name, ext = os.path.splitext(fname)
                if ext == '.py':
                    def loadModule():
                        module = importlib.import_module(name)
                        plugins = module.wakeserverPlugin(self.conf)
                        for (pname, plugin) in plugins:
                            self.plugins[pname] = _Proxy(pname, plugin)
                            print pname
                    
                    if DEBUG:
                        loadModule()
                        continue
                    try:
                        loadModule()
                    except:
                        print 'Initializing a plugin failed: ' + name
                        
        if os.path.isdir(PLUGIN_OLD_DIR):
            files = os.listdir(PLUGIN_OLD_DIR)
            for fname in files:
                if not fname in self.plugins:
                    self.plugins[fname] = _OldPlugin(fname)
                    print fname

        print str(len(self.plugins)) + ' plugins loaded'
