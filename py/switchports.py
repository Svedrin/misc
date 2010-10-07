#!/usr/bin/env python

import re
import sys
import serial
from time import sleep

# The switch will answer:
#  Port    Admin     Mode  Speed Duplex  Bandwidth  Flow control    Link
#   1:   enabled     Auto    N/A    N/A   disabled    disabled      Down
# This regex matches a complete line and gets the fields as groups:
# ('1', 'enabled', 'Auto', 'N/A', 'N/A', 'disabled', 'disabled', 'Down')

regex = r"\s*(?P<port>\d{1,2}):\s+(?P<admin>(?:en|dis)abled)\s+(?P<mode>\w+)\s+(?P<speed>N/A|\d+)\s+(?P<duplex>Full|Half|N/A)\s+(?P<bandwidth>\w+)\s+(?P<flow_control>\w+)\s+(?P<link>Down|Up).*"

ser = serial.Serial("/dev/ttyS0", timeout=1)

for char in "port show\r\n":
	ser.write(char)
	sleep(.01)
	
ports = []
currline = ""

cped = re.compile(regex)
while True:
	data = ser.read(1)
	if not data:
		break
	if data in "\r\n":
		mm = cped.match(currline)
		if mm:
			ports.append({
				'port':    int(mm.group("port")),
				'admin':   mm.group("admin").lower() == "enabled",
				'mode':    mm.group("mode"),
				'speed':   int(mm.group("speed")) if mm.group("speed") != "N/A" else None,
				'duplex':  { 'N/A': None, 'Full': True, 'Half': False }[mm.group("duplex")],
				'flow_control': mm.group('flow_control') == "enabled",
				'link':    mm.group("link") == "Up",
				})
		currline = ""
	else:
		currline += data

ser.close()

if len(sys.argv) == 2:
	portno = int(sys.argv[1])
	for pp in ports:
		if pp['port'] == portno:
			print pp['link']
else:
	pcount = 0

	for pp in ports:
		if pp['link']:
			pcount += 1

	print "ports.value", pcount
