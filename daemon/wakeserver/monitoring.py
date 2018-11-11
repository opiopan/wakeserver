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
NORMAL_MAX =       7

class Monitor(threading.Thread) :
    def __init__(self, conf, pool):
        super(Monitor, self).__init__()
        self.conf = conf.servers
        self.plugins = pool.plugins
        self.servers = []
        self.serversDict = {}
        self.serversDictOrg = {}
        self.statuses = []
        self.operativeServers = []
        self.normalServers = []

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
                    if diag == "normallyoff":
                        server["status"] = "off"
                    elif diag == "alwayson":
                        server["status"] = "on"
                    else:
                        server["status"] = "off"
                        if "on" in server["scheme"] or \
                                "off" in server["scheme"]:
                            self.operativeServers.append(i)
                        else:
                            self.normalServers.append(i)
                self.statuses.append({"status": server["status"]})
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
                      hfThreadNum, i, self.plugins)))
            self.hfThread[i].start()

        self.nmThread = []
        for i in range(nmThreadNum):
            self.nmThread.append(threading.Thread(
                target=diagServers, name="th_nm",
                args=(self.servers, self.statuses,
                      self.normalServers, INTERVAL,
                      nmThreadNum, i, self.plugins)))
            self.nmThread[i].start()

    def run(self):
        while True:
            time.sleep(INTERVAL_WRITE)
            with open(STATUS_FILE_NEW, "w") as f:
                json.dump(self.statuses, f)
            os.rename(STATUS_FILE_NEW, STATUS_FILE)

def diagServers(servers, statuses, targets, interval, groupNum, current,
                plugins):
    while True:
        for i in range(current, len(targets), groupNum):
            server = servers[targets[i]]
            status = statuses[targets[i]]
            diag = server["scheme"]["diag"]
            cmd = ""

            if diag == "custom":
                name = server["scheme"]["type"]
                if name in plugins:
                    if plugins[name].diagnose(server):
                        server["status"] = "on"
                        status["status"] = "on"
                    else:
                        server["status"] = "off"
                        status["status"] = "off"
                continue
            
            if diag == "ping" or diag == "arp":
                cmd = ['ping', '-c1', '-W%d' % (interval), server['ipaddr']]
                arp = "arp %s | tail -1" % (server["ipaddr"])

            if cmd != "":
                if subprocess.call(cmd) == 0 :
                    server["status"] = "on"
                    status["status"] = "on"
                    time.sleep(interval)
                else:
                    active = False
                    if diag == "arp" and \
                            subprocess.check_output(arp, shell = True).\
                       split()[1] != '(incomplete)':
                        server["status"] = "on"
                        status["status"] = "on"
                    else:
                        server["status"] = "off"
                        status["status"] = "off"
