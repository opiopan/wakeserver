#!/usr/bin/python

import cgi
import json
import sys
import os

SERVERS = "/var/www/wakeserver/servers.conf"


print "Content-type: text/plain; charset=utf-8"
print

form = cgi.FieldStorage()

target = ""

if len(sys.argv) > 1:
    target = sys.argv[1]

if form.has_key("target"):
   target = form["target"].value

if target != "":
   l = open("/dev/null", "w")
   l.write(target + "\n")

   f = open(SERVERS)
   servers = json.load(f)

   l.write("json tranlated\n")
   
   for server in servers:
       if server["name"] == target:
           os.system("/usr/bin/wakeonlan " + server["macaddr"])

   l.close()
   f.close()
