import os
import sys
import time
import json
import subprocess
import httpd

BASE_DIR = '/var/www/wakeserver/html'
PORT = 8080

_monitor = None
_plugins = None

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

def wakeserver_get_handler(req, resp):
    req.parseBody()
    if 'type' in req.params and req.params['type'] == ['full']:
        resp.replyFile('/var/run/wakeserver/status.full',
                       ctype = 'text/javascript')
    else:
        resp.replyFile('/var/run/wakeserver/status',
                       ctype = 'text/javascript')

def wakeserver_power_handler(req, resp):
    global _monitor
    global _plugins
    
    req.parseBody()
    server, scheme, plugin = getServer(req)
    type = scheme['type'] if scheme and 'type' in scheme else None
    ctype = 'text/javascript'
    rdata ={'result':False, 'message': 'No server found'}
    if server == None:
        resp.replyJson(rdata, ctype)
        return
    
    power = False
    reboot = False
    args = None
    if req.path == '/cgi-bin/wakeserver-wake.cgi':
        rdata['message'] = 'No way to wakeup this server'
        power = True
        reboot = False
        on = scheme['on'] if 'on' in scheme else None
        if on == 'wol':
            args = ['/usr/bin/wakeonlan', server['macaddr']]
        elif on != 'custom':
            plugin = None
    elif req.path == '/cgi-bin/wakeserver-sleep.cgi':
        rdata['message'] = 'No way to sleep this server'
        power = False
        reboot = False
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
    elif req.path == '/cgi-bin/wakeserver-reboot.cgi':
        rdata['message'] = 'No way to reboot this server'
        power = False
        reboot = True
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
    else:
        resp.replyError(500, 'Invarid request')
        return

    if args:
        nullfile = open("/dev/null")
        proc = subprocess.Popen(args, stderr = subprocess.PIPE,
                                stdout = subprocess.PIPE,
                                stdin = nullfile)
        result = proc.communicate()
        if proc.returncode == 0:
            rdata['result'] = True
            rdata['message'] = 'Succeed'
        else:
            rdata['message'] = 'An error occurred\n\n' + result[1]
    elif plugin:
        if plugin.setStatus(server, power, reboot):
            rdata['result'] = True
            rdata['message'] = 'Succeed'
        else:
            rdata['message'] = 'An error occurred'
    
    resp.replyJson(rdata, ctype)

def wakeserver_attr_handler(req, resp):
    global _monitor
    global _plugins
    
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

def serveForever(monitor, plugins):
    global _monitor
    global _plugins
    _monitor = monitor
    _plugins = plugins
    server = httpd.Server(PORT, BASE_DIR)
    server.addHandler('/cgi-bin/wakeserver-get.cgi', wakeserver_get_handler)
    server.addHandler('/cgi-bin/wakeserver-', wakeserver_power_handler, True)
    server.addHandler('/cgi-bin/wakeserver-attribute.cgi',
                      wakeserver_attr_handler)
    server.serveForever()
