#!/bin/sh

echo Content-type: text/javascript; charset=utf-8
echo

if [ "$QUERY_STRING" = "type=full" ];then
    cat /run/wakeserver/status.full
else
    cat /run/wakeserver/status
fi
