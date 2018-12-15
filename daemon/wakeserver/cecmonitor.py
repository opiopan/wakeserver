import os
import sys
import time
import json
import re
import threading
import subprocess

MSGPATTERN = r"\({0}\): power status changed from.*' to '"
RETRY_INTERVAL = 60
ONSTR1 = "on'\n"
ONSTR2 = "in transition from standby to on'\n"

OPTION_KEY = 'cec-observers'
SERVER_KEY = 'server'
DEVICE_KEY = 'device-num'

controller = None

class Target:
    def __init__(self, serverName, device):
        self.serverName = serverName
        self.device = device
        self.pattern = re.compile(MSGPATTERN.format(self.device))
        self.status = False

class CECController(threading.Thread):
    def __init__(self, monitor, targets):
        super(CECController, self).__init__()
        self.monitor = monitor
        self.targets = targets
        self.status = False

    def observe(self):
        proc = subprocess.Popen(['cec-client'],
                                stdout = subprocess.PIPE,
                                stdin = subprocess.PIPE)
        while True:
            line = proc.stdout.readline()
            if not line :
                return proc.wait()
            for target in self.targets:
                result = target.pattern.search(line)
                if result:
                    ststr = line[result.end():]
                    status = ststr == ONSTR1 or ststr == ONSTR2
                    target.status = status
                    print 'CEC: TV status = {0}'.format(target.status)
                    self.monitor.setStatus(target.serverName, target.status)
                    break

    def run(self):
        proc = subprocess.Popen(['tvservice', '-off'],
                                stdout = subprocess.PIPE)
        if proc:
            sys.stdout.write('CEC: {0}'.format(proc.stdout.readline()))
            proc.wait()
        while True:
            self.observe()
            print 'CEC: cec-client has been finished, restart in {0} sec'.\
                format(RETRY_INTERVAL)
            time.sleep(RETRY_INTERVAL)


def startCECmonitor(conf, monitor):
    global controller
    if controller:
        return
    
    option = conf.main[OPTION_KEY] if OPTION_KEY in conf.main else []
    targets = []
    for target in option:
        server = target[SERVER_KEY] if SERVER_KEY in target else None
        device = target[DEVICE_KEY] if DEVICE_KEY in target else 0
        if server:
            targets.append(Target(server, device))

    if len(targets) > 0:
        controller = CECController(monitor, targets)
        controller.start()
