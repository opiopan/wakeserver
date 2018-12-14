#!/usr/bin/python

import os
import sys
import time
import json
import threading
import subprocess

STATUS_FILE =      "/run/wakeserver/status"
STATUS_FILE_NEW =  "/run/wakeserver/status.new"
STATUS_FILE_FULL = "/run/wakeserver/status.full"
INTERVAL =         1
INTERVAL_WRITE =   2
OPERATIVE_MAX =    3
NORMAL_MAX =       15

monitor = None

class Monitor(threading.Thread) :
    def __init__(self, conf, pool, network, isMaster):
        super(Monitor, self).__init__()
        self.conf = conf.servers
        self.network = network
        self.isMaster = isMaster
        self.plugins = pool.plugins
        self.servers = []
        self.serversDict = {}
        self.serversDictOrg = {}
        self.statuses = []
        self.statusesDict ={}
        self.operativeServers = []
        self.normalServers = []
        self.realtimeServers = []

        i = 0
        for group in self.conf:
            servers = group["servers"];
            for server in servers:
                self.servers.append(server)
                self.serversDict[server['name']] = server
                newserver = dict(server)
                newserver['scheme'] = dict(server['scheme']) \
                                      if 'scheme' in server else {}
                self.serversDictOrg[server['name']] = newserver
                if "user" in server["scheme"]:
                    del server["scheme"]["user"]
                if "diag" in server["scheme"]:
                    diag = server["scheme"]["diag"]
                    pname = server['scheme']['type'] \
                            if diag == 'custom' else None
                    plugin = self.plugins[pname] \
                             if pname in self.plugins else None
                    realTime = plugin and (not plugin.needPolling)
                    if diag == "normallyoff" or diag == 'slave':
                        server["status"] = "off"
                        print 'MONITOR: skip polling: {0}'.format(
                            server['name'])
                    elif diag == "alwayson":
                        server["status"] = "on"
                        print 'MONITOR: skip polling: {0}'.format(
                            server['name'])
                    elif realTime:
                        server["status"] = 'off'
                        self.realtimeServers.append(i)
                        print 'MONITOR: skip polling: {0}'.format(
                            server['name'])
                    else:
                        server["status"] = "off"
                        if "on" in server["scheme"] or \
                                "off" in server["scheme"]:
                            self.operativeServers.append(i)
                        else:
                            self.normalServers.append(i)
                stObj = {"status": server["status"]}
                self.statuses.append(stObj)
                self.statusesDict[server['name']] = stObj
                i = i + 1

        with open(STATUS_FILE_FULL, "w") as f1, open(STATUS_FILE, "w") as f2:
            json.dump(self.conf, f1)
            json.dump(self.statuses, f2)

        hfThreadNum = int((len(self.operativeServers) + OPERATIVE_MAX - 1) / \
                              OPERATIVE_MAX)
        nmThreadNum = int((len(self.normalServers) + NORMAL_MAX - 1) / \
                              NORMAL_MAX)

        self.hfThread = []
        for i in range(hfThreadNum):
            self.hfThread.append(threading.Thread(
                target=diagServers, name="th_hf",
                args=(self.servers, self.statuses, 
                      self.operativeServers, INTERVAL,
                      hfThreadNum, i, self.plugins, self)))
            self.hfThread[i].start()

        self.nmThread = []
        for i in range(nmThreadNum):
            self.nmThread.append(threading.Thread(
                target=diagServers, name="th_nm",
                args=(self.servers, self.statuses,
                      self.normalServers, INTERVAL,
                      nmThreadNum, i, self.plugins, self)))
            self.nmThread[i].start()

    def setStatus(self, name, status):
        if name in self.serversDict:
            stStr = 'on' if status else 'off'
            server = self.serversDict[name]
            if server['status'] != stStr:
                print 'MONITOR: change "{0}" status to {1}'.\
                    format(name, stStr)
                server['status']  = stStr
                self.statusesDict[name]['status'] = stStr
                if not self.isMaster:
                    self.network.syncRemote(server)

    def setStatusByIndex(self, index, status):
        stStr = 'on' if status else 'off'
        server = self.servers[index]
        status = self.statuses[index]
        name = server['name']
        if server['status'] != stStr:
            server['status']  = stStr
            status['status'] = stStr
            print 'MONITOR: change "{0}" status to {1}'.\
                format(name, stStr)
            if not self.isMaster:
                self.network.syncRemote(server)
        
                
    def run(self):
        for i in self.realtimeServers:
            server = self.servers[i]
            pname = server['scheme']['type']
            plugin = self.plugins[pname]
            status = 'on' if plugin.diagnose(server) else 'off'
            server['status'] = status
            self.statuses[i]['status'] = status
        
        while True:
            time.sleep(INTERVAL_WRITE)
            with open(STATUS_FILE_NEW, "w") as f:
                json.dump(self.statuses, f)
            os.rename(STATUS_FILE_NEW, STATUS_FILE)

def diagServers(servers, statuses, targets, interval, groupNum, current,
                plugins, monitor):
    while True:
        for i in range(current, len(targets), groupNum):
            index = targets[i]
            server = servers[index]
            status = statuses[index]
            diag = server["scheme"]["diag"]
            cmd = ""

            if diag == "custom":
                name = server["scheme"]["type"]
                if name in plugins:
                    if plugins[name].diagnose(server):
                        monitor.setStatusByIndex(index, True)
                    else:
                        monitor.setStatusByIndex(index, False)
                continue
            
            if diag == "ping" or diag == "arp":
                cmd = ['ping', '-c1', '-W%d' % (interval), server['ipaddr']]
                arp = "arp %s | tail -1" % (server["ipaddr"])

            if cmd != "":
                try:
                    subprocess.check_output(cmd)
                    monitor.setStatusByIndex(index, True)
                    time.sleep(interval)
                except:
                    active = False
                    if diag == "arp" and \
                            subprocess.check_output(arp, shell = True).\
                       split()[1] != '(incomplete)':
                        monitor.setStatusByIndex(index, True)
                    else:
                        monitor.setStatusByIndex(index, False)
