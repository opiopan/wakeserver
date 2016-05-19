#!/bin/sh

cat << EOF
Content-type: text/javascript; charset=utf-8

EOF

cat /run/wakeserver/status
