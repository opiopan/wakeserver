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
                   if "on" in scheme:
                       cmd = ""
                       all = []
                       if scheme["on"] == "wol":
                           cmd = "/usr/bin/wakeonlan"
                           all = [cmd, server["macaddr"]]
                       elif scheme["on"] == "custom":
                           cmd = "/var/www/wakeserver/plugin/" + scheme["type"]
                           all = [cmd,
                                  "on",
                                  server["ipaddr"],
                                  server["macaddr"],
                                  "0"]
                       if cmd:
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
