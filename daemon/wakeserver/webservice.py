import os
import sys
import traceback
import time
import datetime
import pytz
import json
import subprocess
import httpd
from wakeserver import network

BASE_DIR = '/var/www/wakeserver/html'
MASTER_PORT = 8080
SLAVE_PORT = 8081

_monitor = None
_plugins = None
_isMaster = True

def getServer(req):
    global _monitor
    global _plugins
    target = req.params['target'][0] if 'target' in req.params else None
    server = _monitor.serversDictOrg[target] \
             if target in _monitor.serversDictOrg else None
    scheme = server['scheme'] if server and 'scheme' in server else None
    pluginName = scheme['plugin'] if scheme and 'plugin' in scheme else \
                 scheme['type'] if scheme and 'type' in scheme else None
    plugin = _plugins.plugins[pluginName] if pluginName in _plugins.plugins \
             else None
    return server, scheme, plugin

def getServerNew(req):
    global _monitor
    global _plugins
    target = req.path[9:] # /servers/<Server Name>
    server = _monitor.serversDictOrg[target] \
             if target in _monitor.serversDictOrg else None
    status = _monitor.serversDict[target]['status'] == 'on' if server \
             else False
    scheme = server['scheme'] if server and 'scheme' in server else None
    pluginName = scheme['plugin'] if scheme and 'plugin' in scheme else \
                 scheme['type'] if scheme and 'type' in scheme else None
    plugin = _plugins.plugins[pluginName] if pluginName in _plugins.plugins \
             else None
    return server, scheme, status, plugin

def setServerStatus(server, scheme, power, reboot, plugin):
    type = scheme['type'] if scheme and 'type' in scheme else None
    err = 'No server found'
    if server == None:
        return err
    
    args = None
    if power:
        err = 'No way to wakeup this server'
        on = scheme['on'] if 'on' in scheme else None
        if on == 'wol':
            args = ['/usr/bin/wakeonlan', server['macaddr']]
        elif on != 'custom':
            plugin = None
    elif not power and not reboot:
        err = 'No way to sleep this server'
        off = scheme['off'] if 'off' in scheme else None
        cmd = ''
        if off == 'sudo-shutdown' and (type == 'osx' or type == 'unix'):
            cmd = "nohup sh -c 'sudo /sbin/shutdown -h now'&"
        elif off == 'sleep' and type == 'osx':
            cmd = 'pmset sleepnow'
        elif off != 'custom':
            plugin = None
        remote = server['ipaddr']
        if 'ruser-off' in scheme:
            remote = scheme['ruser-off'] + '@' + remote
        if cmd:
            args = ['/var/www/wakeserver/sbin/sussh',
                    scheme['user'],
                    remote,
                    cmd]
    else:
        err = 'No way to reboot this server'
        off = scheme['reboot'] if 'reboot' in scheme else None
        if off == 'sudo-shutdown' and (type == 'osx' or type == 'unix'):
            cmd = "nohup sh -c 'sudo /sbin/shutdown -r now'&"
        elif off != 'custom':
            plugin = None
        remote = server['ipaddr']
        if 'ruser-off' in scheme:
            remote = scheme['ruser-off'] + '@' + remote
        if cmd:
            args = ['/var/www/wakeserver/sbin/sussh',
                    scheme['user'],
                    remote,
                    cmd]

    if args:
        nullfile = open("/dev/null")
        proc = subprocess.Popen(args, stderr = subprocess.PIPE,
                                stdout = subprocess.PIPE,
                                stdin = nullfile)
        result = proc.communicate()
        if proc.returncode == 0:
            err = None
        else:
            err = 'An error occurred\n\n'
    elif plugin:
        if plugin.setStatus(server, power, reboot):
            err = None
        else:
            err = 'An error occurred'
    
    return err

def wakeserver_get_handler(req, resp, ctype = 'text/javascript'):
    global _monitor
    req.parseBody()
    if 'type' in req.params and req.params['type'] == ['full']:
        resp.replyFile('/var/run/wakeserver/status.full', ctype = ctype)
    else:
        resp.replyJson(_monitor.statuses, ctype = ctype)

def wakeserver_power_handler(req, resp):
    req.parseBody()
    server, scheme, plugin = getServer(req)
    err = None
    
    if req.path == '/cgi-bin/wakeserver-wake.cgi':
        err = setServerStatus(server, scheme, True, False, plugin)
    elif req.path == '/cgi-bin/wakeserver-sleep.cgi':
        err = setServerStatus(server, scheme, False, False, plugin)
    elif req.path == '/cgi-bin/wakeserver-reboot.cgi':
        err = setServerStatus(server, scheme, False, True, plugin)
    else:
        resp.replyError(500, 'Invarid request')
        return

    ctype = 'text/javascript'
    rdata ={'result':not err,
            'message': err if err else 'Succeed'}
    resp.replyJson(rdata, ctype)

def wakeserver_attr_handler(req, resp):
    req.parseBody()
    server, scheme, plugin = getServer(req)
    key = req.params['attribute'][0] if 'attribute' in req.params else None
    value = req.params['value'][0] if 'value' in req.params else None
    rdata ={'result':False, 'message': 'Cannot access attribute'}

    if plugin and key:
        rdata['message'] = 'failed to access attribute'
        rc = False
        if value:
            rc = plugin.setStatus(server, attrs = {key:value})
        else:
            attrs = plugin.getAttrs(server, [key])
            value = str(attrs[key]) if attrs and key in attrs else None
            rc = bool(value)
        if rc:
            rdata = {'result':True, 'message':'Succeed', 'value':value}
    resp.replyJson(rdata, 'text/javascript')

def wakeserver_config_handler(req, resp):
    config = '/var/www/wakeserver/wakeserver.conf'
    req.parseBody()
    resp.contentType = 'text/javascript; charset=utf-8'
    if os.path.isfile(config):
        resp.replyFile(config, ctype = resp.contentType)
    else:
        resp.close()

def serversHandler(req, resp):
    req.parseBody()
    if req.method != httpd.Method.get:
        resp.replyError(500, 'Invalid method type')
    wakeserver_get_handler(req, resp, ctype = 'application/json')

def serverHandler(req, resp):
    req.parseBody()
    if req.method != httpd.Method.get and req.method != httpd.Method.post:
        resp.replyError(500, 'Invalid method type')
        return

    server, scheme, status, plugin = getServerNew(req)
    if not server:
        resp.replyError(500, 'Not found server')
        return
    
    if req.method == httpd.Method.get:
        attrs = None
        if plugin:
            attrs = plugin.getAttrs(server)
        rdata = {'isOn': status, 'attributes': attrs if attrs else {}}
        resp.replyJson(rdata)
    else:
        data = req.json
        if data:
            power = data['isOn'] if 'isOn' in data else None
            reboot = data['reboot'] if 'reboot' in data else False
            attrs = data['attributes'] if 'attributes' in data else None
            if power:
                on = scheme['on'] if 'on' in scheme else None
                if on != 'custom':
                    plugin = None
            elif power == False and not reboot:
                off = scheme['off'] if 'off' in scheme else None
                if off != 'custom':
                    plugin = None
            elif power == False and reboot:
                off = scheme['reboot'] if 'reboot' in scheme else None
                if off != 'custom':
                    plugin = None

            err = None
            if plugin:
                if not plugin.setStatus(server, power, reboot, attrs):
                    resp.replyError(500, 'cannot set status')
            else:
                err = setServerStatus(server, scheme, power, reboot, plugin)
                if err:
                    resp.replyError(500, err)
                    
def remoteHandler(req, resp):
    req.parseBody()
    if req.method != httpd.Method.post or not req.json:
        resp.replyError(500, 'Invalid method type or body')
        return
    rdata = network.applyRemote(req.json)
    if not rdata:
        resp.replyError(500, 'Invalid request body')
        return
    resp.replyJson(rdata)

def roomsHandler(req, resp):
    global _monitor
    req.parseBody()
    if req.method != httpd.Method.get:
        resp.replyError(500, 'Invalid method type')
        return

    rdata = map(lambda r:r.toJson(), _monitor.rooms.getRooms())
    resp.replyJson(list(rdata))
    
def roomHandler(req, resp):
    global _monitor
    req.parseBody()
    if req.method != httpd.Method.get:
        resp.replyError(500, 'Invalid method type')
        return

    key = req.path[7:] # /rooms/<Room Key>
    room = _monitor.rooms.getRoom(key)
    if room:
        resp.replyJson(room.toJson())
    else:
        resp.replyError(404, 'Specified room is not found')

def roomLogHandler(req, resp):
    global _monitor
    req.parseBody()
    if req.method != httpd.Method.get:
        resp.replyError(500, 'Invalid method type')
        return

    key = req.path[10:] # /roomlogs/<Room Key>
    room = _monitor.rooms.getRoom(key)
    if not room:
        resp.replyError(404, 'Specified room is not found')
        return

    date_from = None
    date_to = None
    try:
        if 'period' in req.params:
            date_to = datetime.datetime.now(pytz.utc)
            date_from = date_to - \
                        datetime.timedelta(
                            seconds=int(req.params['period'][0]))
        else:
            if 'from' in req.params:
                dt = datetime.datetime.fromtimestamp(
                    int(req.params['from'][0]))
                data_from = pytz.utc.localize(dt)
            if 'to' in req.params:
                dt = datetime.datetime.fromtimestamp(
                    int(req.params['to'][0]))
                data_to = pytz.utc.localize(dt)
    except:
        print('----------------------------------------------------------')
        print(traceback.format_exc())
        print('----------------------------------------------------------')
        resp.replyError(500, 'Invalid query parameters')
        return

    resp.replyJson(_monitor.rooms.getLog(key, date_from, date_to))
        
def serveForever(monitor, plugins, isMaster = True, baseDir = None):
    global _monitor
    global _plugins
    global _isMaster
    _monitor = monitor
    _plugins = plugins
    _isMaster = isMaster
    port = MASTER_PORT if isMaster else SLAVE_PORT
    server = httpd.Server(port, baseDir if baseDir else BASE_DIR)
    server.addHandler('/cgi-bin/wakeserver-get.cgi', wakeserver_get_handler)
    server.addHandler('/cgi-bin/wakeserver-', wakeserver_power_handler, True)
    server.addHandler('/cgi-bin/wakeserver-attribute.cgi',
                      wakeserver_attr_handler)
    server.addHandler('/cgi-bin/wakeserver-config.cgi',
                      wakeserver_config_handler)
    server.addHandler('/servers', serversHandler)
    server.addHandler('/servers/', serverHandler, True)
    server.addHandler('/remote', remoteHandler)
    server.addHandler('/rooms', roomsHandler)
    server.addHandler('/rooms/', roomHandler, True)
    server.addHandler('/roomlogs/', roomLogHandler, True)
    server.serveForever()
