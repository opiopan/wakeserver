#!/bin/sh

CONFIG=/var/www/wakeserver/wakeserver.conf

echo Content-type: text/javascript; charset=utf-8
echo
if [ -f $CONFIG ];then
   cat $CONFIG
fi

