#!/usr/bin/python

import cgi
import json
import sys
import os
import subprocess

SERVERS = "/var/www/wakeserver/servers.conf"

form = cgi.FieldStorage()

target = ""
attribute = ""
value = ""

if len(sys.argv) > 1:
    target = sys.argv[1]
    attribute = sys.argv[2]
    if len(sys.argv) > 3:
        value = sys.argv[3]

if form.has_key("target"):
   target = form["target"].value
   attribute = form["attribute"].value
   if "value" in form:
       value = form["value"].value

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
                   response["message"] = "No way to invoke command"
                   scheme = server["scheme"]
                   cmd = "/var/www/wakeserver/plugin/" + scheme["type"]
                   all = [cmd,
                          "attribute",
                          server["ipaddr"],
                          server["macaddr"],
                          "0",
                          attribute]
                   if value != "":
                       all.append(value)

                   nullfile = open("/dev/null")
                   proc = subprocess.Popen(
                       all, stderr=subprocess.PIPE, \
                           stdout=subprocess.PIPE, \
                           stdin=nullfile)
                   result = proc.communicate()
                   if proc.returncode == 0:
                       response["result"] = True
                       response["message"] = "Succeed"
                       response["value"] = result[0].replace('\n', '')
                   else:
                       response["message"] = \
                           "An error occurred at server\n\n" +\
                           result[1]


print "Content-type: text/javascript; charset=utf-8"
print
print json.dumps(response)
