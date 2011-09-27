# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import threading
import readline
import select
import socket
from optparse import OptionParser

from SRCDS import SRCDS

class LogThread(threading.Thread):
    def __init__(self, bindaddr):
        threading.Thread.__init__(self)
        self.shutdown = False
        self.sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP )
        self.sock.bind(bindaddr)

    def run(self):
        while not self.shutdown:
            rdy_read, _, _ = select.select( [self.sock.fileno()], [], [], 0.5 )
            if rdy_read:
                data, addr = self.sock.recvfrom( 1024 )
                # \r = carriage return, \x1b[K = VT100 delete everything right of the cursor
                print "\r\x1b[K" + data[5:-2]
                # re-print whatever the user had entered before we printed the above line
                sys.stdout.write( readline.get_line_buffer() )
                sys.stdout.flush()

        self.sock.close()


if __name__ == '__main__':
    parser = OptionParser(usage="""Usage: %prog [options] <server> <password>""")

    parser.add_option( "-i", "--listenip", help="Local IP address to bind on for log messages.", default="0.0.0.0" )

    parser.add_option( "-l", "--listenport",
        help="Local port to listen for log messages. 0 disables listening completely.",
        default=31337, type="int"
        )

    parser.add_option( "-t", "--targetip",
        help=("IP address to configure on the server using logaddress_add. "
              "If omitted, will be automatically detected.")
        )

    parser.add_option( "-p", "--port",
        help="The server port.",
        default=27015, type="int"
        )

    options, progargs = parser.parse_args()

    if len(progargs) != 2:
        sys.exit("Wrong number of arguments, see -h")

    ds = SRCDS( progargs[0], options.port, progargs[1] )

    if options.listenport != 0:
        lt = LogThread( (options.listenip, options.listenport) )
        lt.start()

        if not options.targetip:
            options.targetip = ds.tcpsock.getsockname()[0]
        ds.rcon_command("logaddress_add %s:%d" % (options.targetip, options.listenport))

    try:
        while True:
            cmd = raw_input()
            if cmd == "\\q":
                break
            if cmd:
                print ds.rcon_command(cmd)
    except KeyboardInterrupt:
        print "Caught ^c, shutting down."
    finally:
        if options.listenport != 0:
            lt.shutdown = True
            ds.rcon_command("logaddress_del %s:%d" % (options.targetip, options.listenport))
        ds.disconnect()
