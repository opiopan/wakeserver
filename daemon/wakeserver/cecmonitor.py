import os
import sys
import time
import json
import re
import threading
import subprocess
import Queue

MSGPATTERN = r"\({0}\): power status changed from.*' to '"
RETRY_INTERVAL = 60
ONSTR1 = "on'\n"
ONSTR2 = "in transition from standby to on'\n"
POLLING_INTERVAL = 10

OPTION_KEY = 'cec-observers'
SERVER_KEY = 'server'
DEVICE_KEY = 'device-num'
POLLING_KEY = 'polling'

controller = None
pollingThread = None

class Target:
    def __init__(self, serverName, device):
        self.serverName = serverName
        self.device = device
        self.pattern = re.compile(MSGPATTERN.format(self.device))
        self.status = False

class Command:
    COMMAND = 0
    QUIT = -1
    def __init__(self, cmdstr):
        self.kind = self.COMMAND if cmdstr else self.QUIT
        self.value = cmdstr

    def isQuit(self):
        return self.kind == self.QUIT

class CECCmdSender(threading.Thread):
    def __init__(self, proc):
        super(CECCmdSender, self).__init__()
        self.proc = proc
        self.pipe = self.proc.stdin
        self.cmdQueue = Queue.Queue()

    def send(self, cmd):
        self.cmdQueue.put(cmd)

    def quit(self):
        self.cmdQueue.put(Command(None))

    def run(self):
        while True:
            cmd = self.cmdQueue.get()
            if cmd.isQuit():
                return
            try:
                self.pipe.write(cmd.value + '\n')
            except:
                self.proc.terminate()
                return

class CECController(threading.Thread):
    def __init__(self, monitor, targets):
        super(CECController, self).__init__()
        self.monitor = monitor
        self.targets = targets
        self.status = False
        self.sender = None

    def powerOn(self, devNum):
        cmd = Command('on {0}'.format(int(devNum)))
        if self.sender:
            self.sender.send(cmd)
            return True
        else:
            return False

    def powerOff(self, devNum):
        cmd = Command('standby {0}'.format(int(devNum)))
        if self.sender:
            self.sender.send(cmd)
            return True
        else:
            return False

    def checkPower(self, devNum):
        cmd = Command('pow {0}'.format(int(devNum)))
        if self.sender:
            self.sender.send(cmd)
            return True
        else:
            return False
        
        
    def observe(self):
        proc = subprocess.Popen(['cec-client'],
                                stdout = subprocess.PIPE,
                                stdin = subprocess.PIPE)
        self.sender = CECCmdSender(proc)
        self.sender.start()
        for target in self.targets:
            cmd = Command('pow {0}'.format(target.device))
            self.sender.send(cmd)
        
        while True:
            line = proc.stdout.readline()
            if not line :
                self.sender.quit()
                self.sender.join()
                self.sender = None
                return proc.wait()
            for target in self.targets:
                result = target.pattern.search(line)
                if result:
                    ststr = line[result.end():]
                    status = ststr == ONSTR1 or ststr == ONSTR2
                    target.status = status
                    print 'CEC: {0} status = {1}'.format(
                        target.serverName, target.status)
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

class CECPollingThread(threading.Thread):
    def __init__(self, devices):
        super(CECPollingThread, self).__init__()
        self.devices = devices

    def run(self):
        global controller
        while True:
            time.sleep(POLLING_INTERVAL)
            if controller:
                for device in self.devices:
                    controller.checkPower(device)

def startCECmonitor(conf, monitor):
    global controller
    global pollingThread
    if controller:
        return
    
    option = conf.main[OPTION_KEY] if OPTION_KEY in conf.main else []
    targets = []
    pollings = []
    for target in option:
        server = target[SERVER_KEY] if SERVER_KEY in target else None
        device = target[DEVICE_KEY] if DEVICE_KEY in target else 0
        polling = target[POLLING_KEY] if POLLING_KEY in target else False
        if server:
            targets.append(Target(server, device))
            if polling:
                pollings.append(device)

    if len(targets) > 0:
        controller = CECController(monitor, targets)
        controller.start()

    if len(pollings) > 0:
        polingThread = CECPollingThread(pollings)
        polingThread.start()
