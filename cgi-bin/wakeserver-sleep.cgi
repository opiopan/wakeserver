#!/usr/bin/python

import cgi
import json
import sys
import os
import subprocess

SERVERS = "/var/www/wakeserver/servers.conf"

form = cgi.FieldStorage()

target = ""

if len(sys.argv) > 1:
    target = sys.argv[1]

if form.has_key("target"):
   target = form["target"].value

response = {"result": False, 
            "message": "No server found"}

if target != "":
   with open(SERVERS) as f, open("/dev/null", "w") as l:
       l.write(target + "\n")

       f = open(SERVERS)
       groups = json.load(f)

       l.write("json tranlated\n")
   
       for group in groups:
           for server in group["servers"]:
               if server["name"] == target:
                   response["message"] = "No way to sleep this server"
                   scheme = server["scheme"]
                   if "off" in scheme:
                       cmd = ""
                       if (scheme["type"] == "osx" or \
                               scheme["type"] == "unix") \
                               and scheme["off"] == "sudo-shutdown":
                           cmd = "nohup sh -c 'sudo /sbin/shutdown -h now'&"
                       elif scheme["type"] == "osx" and \
                               scheme["off"] == "sleep":
                           cmd = "pmset sleepnow"

                       remote = server["ipaddr"]
                       if "ruser-off" in scheme:
                           remote = scheme["ruser-off"] + "@" + remote

                       all = []
                       if cmd:
                           all = ["/var/www/wakeserver/sbin/sussh",
                                  scheme["user"],
                                  remote,
                                  cmd]

                       if scheme["off"] == "custom":
                           cmd = "/var/www/wakeserver/plugin/" + scheme["type"]
                           all = [cmd,
                                  "off",
                                  server["ipaddr"],
                                  server["macaddr"],
                                  "0"]

                       if len(all) > 0:
                           nullfile = open("/dev/null")
                           proc = subprocess.Popen(
                               all, stderr=subprocess.PIPE, \
                                   stdout=subprocess.PIPE, \
                                   stdin=nullfile)
                           result = proc.communicate()
                           if proc.returncode == 0:
                               response["result"] = True
                               response["message"] = "Succeed"
                           else:
                               response["message"] = \
                                   "An error occurred at server\n\n" +\
                                   result[1]


print "Content-type: text/javascript; charset=utf-8"
print
print json.dumps(response)
