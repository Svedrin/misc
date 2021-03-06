# MicroPython shell commands
# Installation:
# 1. connect to your micropython thingy using minicom or so
# 2. For each chunk in this script: CTRL-E, CTRL-V, CTRL-D
#    (this will execute this script and create the 'sh' module on your ESP)
# 5. CTRL-D (reboots MicroPython)
# 6. from sh import *
# 7. Enjoy!

f = open("sh.py", "wb")
f.write(r"""
import os
import sys
import network
import socket
import time

__docs = []
def __doc(n, s):
    __docs.append((n, s))

__doc('ls(path="")', "list dirs and files")
def ls(path=""):
    for entry in os.ilistdir(path):
        name, type, inode, size = entry
        if type == 0x4000:
            name += "/"
        print("%10db  %-10s" % (size, name))

__doc("cat(file)", "print file contents to stdout")
def cat(fname):
    with open(fname, "rb") as f:
        for line in f:
            sys.stdout.write(line)

__doc("cat_into(file)", "read file contents from stdin")
def cat_into(fname):
    print("paste the content, hit CTRL-D when done")
    with open(fname, "wb") as f:
        while True:
            try:
                f.write(input() + "\n")
            except EOFError:
                print("EOF")
                break

__doc("exists(path)", "check if a path exists")
def exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False

__doc("isdir(path)", "check if a path is a directory")
def isdir(path):
    try:
        return os.stat(path)[0] == 0x4000
    except OSError:
        return False

__doc("isfile(path)", "check if a path is a file")
def isfile(path):
    try:
        return os.stat(path)[0] == 0x8000
    except OSError:
        return False

__doc("touch(path)", "create a file if it doesn't exist")
def touch(path):
    if isdir(path):
        return
    with open(path, "ab") as f:
        pass

"""[1:])
f.close()

### -------------------------- SECOND CHUNK ---------------------------------

f = open("sh.py", "ab")
f.write(r"""
__doc("rm(path)", "delete a path")
def rm(path):
    if not exists(path):
        return
    if isdir(path):
        os.rmdir(path)
    else:
        os.remove(path)

__doc("df()", "display used/free space")
def df():
    _, f_frsize, f_blocks, f_bfree, f_bavail, _, _, _, _, _ = os.statvfs("")

    sz_mb = f_frsize * f_blocks / 1024. / 1024.
    av_mb = f_frsize * f_bavail / 1024. / 1024.
    us_mb = sz_mb - av_mb
    pcnt  = us_mb / sz_mb * 100

    print("Size   Used   Avail  Use%")
    print("%3.1fM   %3.1fM   %3.1fM   %3d%%" % (sz_mb, us_mb, av_mb, pcnt))

__doc("ip()", "display current IPs")
def ip():
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)

    if   sta_if.isconnected():   sta_state = "connected"
    elif sta_if.active():        sta_state = "active"
    else:                        sta_state = "inactive"

    if   ap_if.isconnected():    ap_state = "connected"
    elif ap_if.active():         ap_state = "active"
    else:                        ap_state = "inactive"

    print("Iface   State        IP              Netmask         GW              DNS")
    print("STA:    %-12s %-15s %-15s %-15s %-15s" % ((sta_state,) + sta_if.ifconfig()))
    print("AP:     %-12s %-15s %-15s %-15s %-15s" % ((ap_state, ) + ap_if.ifconfig()) )

"""[1:])
f.close()

### -------------------------- THIRD CHUNK ---------------------------------

f = open("sh.py", "ab")
f.write(r"""
__doc("wifi_station(ssid, password, ap=None)", "connect to a WiFi AP")
__doc("wifi_station(None)", "disconnect from WiFi AP")
def wifi_station(ssid, password=""):
    sta_if = network.WLAN(network.STA_IF)
    if ssid is not None:
        sta_if.active(True)
        sta_if.connect(ssid, password)
    else:
        if sta_if.connected():
            sta_if.disconnect()
        sta_if.active(False)

__doc("wifi_ap(ssid, password, ap=None)", "operate as a WiFi AP")
__doc("wifi_ap(None)", "disable WiFi AP")
def wifi_ap(ssid, password=""):
    ap_if = network.WLAN(network.AP_IF)
    if ssid is not None:
        ap_if.active(True)
        ap_if.config(essid=ssid, password=password)
    else:
        ap_if.active(False)

__doc("curl(url, outpath=None (-> stdout))", "perform an HTTP get request and print the result to stdout or a file")
def curl(url, outpath=None):
    if outpath is None:
        outfile = sys.stdout
    else:
        outfile = open(outpath, "wb")
    _, _, host, path = url.split('/', 3)
    if ":" in host:
        host, port = host.rsplit(":", 1)
    else:
        port = 80
    addr = socket.getaddrinfo(host, int(port))[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.1\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))
    headers = True
    while True:
        try:
            data = s.readline()
        except KeyboardInterrupt:
            break
        if headers:
            if data == b"\r\n":
                headers = False
        else:
            if data:
                outfile.write(data)
            else:
                break
    s.close()
    if outfile is not sys.stdout:
        outfile.close()
"""[1:])
f.close()

### -------------------------- FOURTH CHUNK ---------------------------------

f = open("sh.py", "ab")
f.write(r"""

__doc("nl(file)", "print file contents to stdout, prefixed with line numbers")
def nl(fname):
    i = 1
    with open(fname, "rb") as f:
        for line in f:
            sys.stdout.write(b"[%5i] %s" % (i, line))
            i += 1

__doc("run(fn, *args, **kwargs)", "run a main() function in a loop and log exceptions to main.log")
def run(fn, *args, **kwargs):
    while True:
        started_at = time.time()
        try:
            fn(*args, **kwargs)
        except KeyboardInterrupt:
            return
        except Exception as err:
            failed_at = time.time()
            logmsg = "[%d] %r" % (failed_at - started_at, err)
            print(logmsg)
            with open("main.log", "ab") as logfd:
                print(logmsg, file=logfd)

__doc("format_c()", "reformat the flash")
def format_c():
    if input("Sure? [yN] ") != "y":
        print("Cancelled")
        return

    from flashbdev import bdev
    os.VfsFat.mkfs(bdev)


def help_():
    print("Functions:")
    for (cmd, help) in __docs:
        print("%-50s -- %s" % (cmd, help))

"""[1:])
f.close()


