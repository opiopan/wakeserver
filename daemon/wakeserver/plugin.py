#!/usr/bin/python

import os
import sys
import time
import importlib

PLUGIN_DIR = "/var/www/wakeserver/plugin.py"
PLUGIN_OLD_DIR = "/var/www/wakeserver/plugin"
DIAG_INTERVAL = 1

class Plugin:
    def diagnose(self, server):
        return False
    
    def setPower(self, server, isOn):
        return False, "This plugin object is not concrete object"

    def attribute(self, server, name, value):
        return False, "This plugin object is not concrete object"

class OldPlugin(Plugin):
    def __init__(self, name):
        self.name = name
        
    def diagnose(self, server):
        try:
            cmd = "%s/%s diag '%s' '%s' %d" % \
                  (PLUGIN_OLD_DIR, 
                   self.name,
                   server["ipaddr"], server["macaddr"],
                   DIAG_INTERVAL)
            if os.system(cmd) == 0 :
                time.sleep(DIAG_INTERVAL)
                return True;
            else:
                return False;
        except:
            print "OldPlugin(" + self.name + ") raise exception"
            return False
        return False

class PluginPool:
    def __init__(self, conf):
        self.conf = conf
        self.debug = 'DEBUG' in os.environ

        pluginDir = PLUGIN_DIR
        if 'PLUGIN' in os.environ:
            pluginDir = os.environ['PLUGIN']

        self.plugins = {}
        if os.path.isdir(pluginDir):
            files = os.listdir(pluginDir)
            for fname in files:
                name, ext = os.path.splitext(file)
                if ext == '.py':
                    try:
                        module = importlib.import_module(pluginDir +
                                                         '/' + fname)
                        plugin = module.wakeserverPlugin(self.conf)
                        self.plugins[name] = plugin
                    except:
                        print 'Initializing a plugin failed: ' + name
        if os.path.isdir(PLUGIN_OLD_DIR):
            files = os.listdir(PLUGIN_OLD_DIR)
            for fname in files:
                self.plugins[fname] = OldPlugin(fname)

        print str(len(self.plugins)) + ' plugins loaded'
