#!/usr/bin/env python

import os
import errno
import re
import sys
import serial
import time
import stat
from time import sleep

MAX_WAIT = 10
LOCKFILE = "/var/lock/ttyS0.lock"

while True:
    try:
        fd = os.open(LOCKFILE, os.O_EXCL | os.O_RDWR | os.O_CREAT)
        # we created the LOCKFILE, so we're the owner
        break

    except OSError, e:
        if e.errno != errno.EEXIST:
            # should not occur
            raise

        try:
            # the lock file exists, try to stat it to get its age
            # and read it's contents to report the owner PID
            f = open(LOCKFILE, "r")
            s = os.stat(LOCKFILE)

        except OSError, e:
            if e.errno != errno.EEXIST:
                sys.exit("%s exists but stat() failed: %s" %
                         (LOCKFILE, e.strerror))
            # we didn't create the LOCKFILE, so it did exist, but it's
            # gone now. Just try again
            continue
        
        # we didn't create the LOCKFILE and it's still there, check
        # its age
        now = int(time.time())
        if now - s[stat.ST_MTIME] > MAX_WAIT:

            pid = f.readline()
            sys.exit("%s has been locked for more than " \
                     "%d seconds (PID %s)" % (LOCKFILE, MAX_WAIT,
                     pid))


        # it's not been locked too long, wait a while and retry
        f.close()
        time.sleep(1)

f = os.fdopen(fd, "w")

f.write("%d\n" % os.getpid())
f.close()


# The switch will answer:
#  Port    Admin     Mode  Speed Duplex  Bandwidth  Flow control    Link
#   1:   enabled     Auto    N/A    N/A   disabled    disabled      Down
# This regex matches a complete line and gets the fields as groups:
# ('1', 'enabled', 'Auto', 'N/A', 'N/A', 'disabled', 'disabled', 'Down')

regex = r"\s*(?P<port>\d{1,2}):\s+(?P<admin>(?:en|dis)abled)\s+(?P<mode>\w+)\s+(?P<speed>N/A|\d+)\s+(?P<duplex>Full|Half|N/A)\s+(?P<bandwidth>\w+)\s+(?P<flow_control>\w+)\s+(?P<link>Down|Up).*"

def queryports(ser, qryports=None):
    if qryports is None:
        qryports = []

    for char in ("port show %s\r\n" % ','.join([str(pn) for pn in qryports])):
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
    return ports

if len(sys.argv) == 2:
    portno = int(sys.argv[1])
    ser = serial.Serial("/dev/ttyS0", timeout=1)
    try:
        ports = queryports( ser, [portno] )
    finally:
        ser.close()
        os.unlink(LOCKFILE)
    for pp in ports:
        if pp['port'] == portno:
            print pp['link']
            sys.exit( {True: 0, False: 2}[pp['link']] )
else:
    pcount = 0
    ser = serial.Serial("/dev/ttyS0", timeout=1)
    try:
        ports = queryports(ser)
    finally:
        ser.close()
        os.unlink(LOCKFILE)

    for pp in ports:
        if pp['link']:
            pcount += 1

    print "ports.value", pcount

