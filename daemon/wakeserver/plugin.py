#!/usr/bin/python

import os
import sys
import time
import importlib
import subprocess

DEBUG = 'DEBUG' in os.environ

PLUGIN_DIR = "/var/www/wakeserver/plugin.py"
PLUGIN_OLD_DIR = "/var/www/wakeserver/plugin"
DIAG_INTERVAL = 1

PLUGIN_OPTION_KEY = 'plugin-option'

class Plugin:
    needPolling = True

    def option(self, server):
        return server[PLUGIN_OPTION_KEY] \
            if PLUGIN_OPTION_KEY in server else None
    
    def diagnose(self, server):
        return False
    
    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        return False

    def getAttrs(self, server, keys = None):
        return None

class _OldPlugin(Plugin):
    def __init__(self, name):
        self.name = name

    def execPlugin(self, server, cmd, interval = 0, key = None, value = None):
        args = [PLUGIN_OLD_DIR + '/' + self.name,
                cmd,
                server["ipaddr"], server["macaddr"],
                str(interval)]
        if key:
            args += [key]
            if value:
                args += [value]
        try:
            #if cmd != 'diag':
            #    print 'args: {0}'.format(args)
            return subprocess.check_output(args)
        except:
            return None
        
    def diagnose(self, server):
        btime = time.time()
        rc = self.execPlugin(server, 'diag', DIAG_INTERVAL)
        interval = time.time() - btime
        if interval < DIAG_INTERVAL:
            time.sleep(DIAG_INTERVAL - interval)
        return rc != None

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        if isOn != None and attrs != None:
            return False
        if isOn != None:
            cmd = 'on'
            if not isOn:
                cmd = 'off' if not needReboot else 'reboot'
            return self.execPlugin(server, cmd) != None
        elif attrs != None and len(attrs) == 1:
            for key in attrs:
                return self.execPlugin(server, 'attribute',
                                       key = key, value = attrs[key]) != None
        else:
            return False

    def getAttrs(self, server, keys = None):
        if keys == None or len(keys) != 1:
            return None
        for key in keys:
            value = self.execPlugin(server, 'attribute', key = key)
            return {key : value.replace('\n', '')}

class _Proxy(Plugin):
    def __init__(self, name, obj):
        self.name = name
        self.origin = obj
        self.needPolling = obj.needPolling
        
    def diagnose(self, server):
        def proc():
            btime = time.time()
            rc = self.origin.diagnose(server)
            interval = time.time() - btime
            if interval < DIAG_INTERVAL:
                time.sleep(DIAG_INTERVAL - interval)
            return rc
        if DEBUG:
            return proc()
        try:
            return proc()
        except:
            print "Plugin(" + self.name + ") raise exception"
            return False

    def setStatus(self, server, isOn = None, needReboot = False, attrs = None):
        if DEBUG:
            return self.origin.setStatus(server, isOn, needReboot, attrs)
        try:
            return self.origin.setStatus(server, isOn, needReboot, attrs)
        except:
            msg = "Plugin(" + self.name + ") raise exception"
            print msg
            return False

    def getAttrs(self, server, keys = None):
        if DEBUG:
            return self.origin.getAttrs(server, keys)
        try:
            return self.origin.getAttrs(server, keys)
        except:
            msg = "Plugin(" + self.name + ") raise exception"
            print msg
            return None
    
class PluginPool:
    def __init__(self, conf, pluginDir = None):
        self.conf = conf

        sys.path.append(pluginDir if pluginDir else PLUGIN_DIR)

        pluginnames = []
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
                            pluginnames.append(pname + ': ' +
                                               pluginDir + '/' + fname)
                    
                    if DEBUG:
                        loadModule()
                        continue
                    try:
                        loadModule()
                    except:
                        print 'PLUGIN: Initializing a plugin failed: ' + name
                        
        if os.path.isdir(PLUGIN_OLD_DIR):
            files = os.listdir(PLUGIN_OLD_DIR)
            for fname in files:
                if not fname in self.plugins:
                    self.plugins[fname] = _OldPlugin(fname)
                    pluginnames.append(fname + ': ' +
                                       PLUGIN_OLD_DIR + '/' + fname)

        print 'PLUGIN: {0} plugins are loaded'.format(len(self.plugins))
        for name in pluginnames:
            print '    ' + name
