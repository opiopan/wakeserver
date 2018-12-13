import os
import sys
import time
import json
import socket
import subprocess

MASTER_SERVICE = '_wakeserver._tcp'
SLAVE_SERVICE = '_wakeserver_slave._tcp'
LISTSERVICE = '/var/www/wakeserver/bin/listservice'

HOSTNAME = socket.gethostname() + '.local'
MASTER_PORT = ':8080'
SLAVE_PORT = ':8081'

HOST_KEY = 'host'
SERVERS_KEY = 'servers'
NAME_KEY = 'name'
ISON_KEY = 'isOn'

isMaster = True
remotes = []

def applyRemote(data):
    global remotes
    
    if HOST_KEY in data:
        newhost = data[HOST_KEY]
        needToAppend = True
        for host in remotes:
            if newhost == host:
                needToAppend = False
                break
        if needToAppend:
            print 'NETWORK: new remote: {}'.format(newhost)
            remotes.append(newhost)
    else:
        return None

    if SERVERS_KEY in data:
        print 'NETWORK: apply data from: {}'.format(newhost)
        for server in data[SERVERS_KEY]:
            name = server[NAME_KEY] if NAME_KEY in server else None
            status = server[ISON_KEY] if ISON_KEY in server else None
            if monitoring.monitor:
                monitoring.monitor.setStatus(name, status)

    return makeSyncData()

def makeSyncData():
    global isMaster
    data = {HOST_KEY: HOSTNAME + MASTER_PORT if isMaster else SLAVE_PORT}
    
    if not isMaster:
        hosts = []
        for server in monitoring.monitor.servers:
            sdata = {NAME_KEY, server['name'],
                     STATUS_KEY, server['status'] == 'on'}
            hosts.append(sdata)
        data[SERVERS_KEY] = hosts

    return data

def initNetwork(ismaster):
    global remotes
    global isMaster
    isMaster = ismaster
    proc = subprocess.Popen([LISTSERVICE,
                             SLAVE_SERVICE if isMaster else MASTER_SERVICE],
                            stdout = subprocess.PIPE)
    while proc:
        line = proc.stdout.readline()
        if len(line) == 0:
            proc.wait()
            break
        remotes.append(line[:-1])

    print 'NETWORK: detected {0} remotes:'.format(len(remotes))
    for name in remotes:
        print '    {0}'.format(name)
