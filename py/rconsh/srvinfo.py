# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

# see https://developer.valvesoftware.com/wiki/Server_Queries

import sys
import socket
import struct
import bz2
import operator

from time import time
from optparse import OptionParser
from prettytable import PrettyTable

def get_struct(fmt, inp):
    # unpack a single value according to <fmt from the input data.
    fmtlen = struct.calcsize("<" + fmt)
    data = struct.unpack( "<" + fmt, inp[:fmtlen] )[0]
    return data, inp[fmtlen:]

def get_zstring(inp):
    # unpack a zero-terminated string from the input data.
    ret = ""
    while inp:
        char = struct.unpack("c", inp[0])[0]
        inp = inp[1:]
        if char == '\0':
            break
        ret += char
    return ret, inp

def unpack(fmt, inp):
    # unpack one or more values according to fmt from the input data.
    # returns a tuple of the unpacked data and the rest of the input that hasn't been touched.
    # if fmt consists of only one specifier, data will be the value; otherwise data will be a tuple.
    data = []
    rest = inp
    for specifier in fmt:
        if specifier == "z":
            item, rest = get_zstring(rest)
        else:
            item, rest = get_struct(specifier, rest)
        data.append(item)
    if len(fmt) == 1:
        data = data[0]
    return data, rest


def a2s_info_req():
    # create an A2S Info Request.
    return struct.pack("<iB20s", -1, 0x54, "Source Engine Query")

def a2s_info_rsp(inforsp):
    # parse an A2S Info Response packet.
    fields = ("magic", "header", "protocol", "name", "map", "folder", "game", "appid",
              "players", "maxplayers", "bots", "servertype", "environment", "visibility",
              "vac", "version", "edf")

    data, rest = unpack("iBBzzzzhBBBcc??zB", inforsp)
    data = dict(zip(fields, data))

    if data["header"] != 0x49:
        raise TypeError("This is not an Info response packet")

    edf = data["edf"] # extra data flag specifies which additional fields are available

    if edf & 0x80:
        data["port"], rest = unpack("h", rest)

    if edf & 0x10:
        data["steamid"], rest = unpack("q", rest)

    if edf & 0x40:
        (data["tvport"], data["tvname"]), rest = unpack("hz", rest)

    if edf & 0x20:
        data["tags"], rest = unpack("z", rest)

    if edf & 0x01:
        data["gameid"], rest = unpack("q", rest)

    if rest:
        raise ValueError("expected end of input, found '%r'" % rest)

    return data


def a2s_getchallenge_req():
    # create an A2S Challenge Request.
    return struct.pack("<iB", -1, 0x57)

def a2s_getchallenge_rsp(inforsp):
    # parse an A2S Challenge Response.
    fields = ("magic", "header", "challenge")

    data, rest = unpack("iBi", inforsp)
    data = dict(zip(fields, data))

    if data["header"] != 0x41:
        raise TypeError("This is not a Challenge response packet")

    if rest:
        raise ValueError("expected end of input, found '%r'" % rest)

    return data


class RetryPlox(Exception):
    # Players and Rules requests may return a new challenge instead of the actual data,
    # in which case this exception is raised.
    pass


def a2s_getplayers_req(challenge):
    # create an A2S Players Request.
    return struct.pack("<iBi", -1, 0x55, challenge)

def a2s_getplayers_rsp(inforsp):
    # parse an A2S Players Response.
    data, rest = unpack("iB", inforsp)
    data = dict(zip(("magic", "header"), data))

    if data["header"] == 0x41: # got a new challenge instead of actual data
        raise RetryPlox( unpack("i", rest)[0] )

    if data["header"] != 0x44: # got something weird
        raise TypeError("This is not a Player response packet")

    data["playercount"], rest = unpack("B", rest)

    data["players"] = []
    while rest:
        playerinfo, rest = unpack("bzif", rest)
        data["players"].append( dict(zip( ("index", "name", "score", "duration"), playerinfo )) )

    return data


def a2s_getrules_req(challenge):
    # create an A2S Rules Request.
    return struct.pack("<iBi", -1, 0x56, challenge)

def a2s_getrules_rsp(inforsp):
    # parse an A2S Rules Response.
    data, rest = unpack("iB", inforsp)
    data = dict(zip(("magic", "header"), data))

    if data["header"] == 0x41: # got a new challenge instead
        raise RetryPlox( unpack("i", rest)[0] )

    if data["header"] != 0x45:
        raise TypeError("This is not a Rules response packet")

    data["rulescount"], rest = unpack("h", rest)

    data["rules"] = {}
    while rest:
        (name, value), rest = unpack("zz", rest)
        data["rules"].update( {name: value} )

    if rest:
        raise ValueError("expected end of input, found '%r'" % rest)

    return data


def recvresponse(sock):
    # read from the socket until we have a complete response, either because the packet
    # we received isn't chunked and thereby complete in the first place, or because we
    # have received all chunks.
    chunks = []
    while True:
        inforsp, _ = sock.recvfrom(4096)
        magic, rest = unpack("i", inforsp)
        if magic == -1:     # packet is *not* chunked, return as-is
            return inforsp
        elif magic == -2:   # packet *is* chunked and maybe compressed
            (pkid, total, number, size), chunk = unpack("iBBh", rest)
            compressed = pkid & (1<<32)
            if number == 0 and compressed:
                # the first packet contains extra stuff if compressed, read it out
                (size, checksum), chunk = unpack("ii", chunk)
            # add our data and its packet index to the list so we can re-order packets
            # if necessary (remember this is UDP)
            chunks.append( (number, chunk) )
            if len(chunks) == total:
                break
        else:
            raise ValueError("Invalid Magic Int '%r'" % magic)

    # reorder and join packets
    chunks.sort(key=operator.itemgetter(0))
    data = "".join([c[1] for c in chunks])

    if compressed:
        data = bz2.decompress( data )

    magic, rest = unpack("i", data)
    if magic == -1: # check that data now contains a verbatim packet
        return data

    raise ValueError("invalid chunked packet")


class SRCDS(object):
    def __init__(self, address, port=27015):
        self.sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP)
        self.sock.settimeout(2.0)
        self.srvaddr = (address, port)
        self.invalidate()

    def invalidate(self):
        """ Invalidate all cached information. """
        self._info      = None
        self._challenge = None
        self._players   = None
        self._rules     = None

    @property
    def info(self):
        """ General server info. """
        if self._info is None:
            ping = time()
            self.sock.sendto(a2s_info_req(), self.srvaddr)
            inforsp = recvresponse(self.sock)
            pong = time()
            self._info = a2s_info_rsp(inforsp)
            self._info["ping"] = pong - ping
        return self._info

    @property
    def challenge(self):
        """ Challenge for querying players and cvars. """
        if self._challenge is None:
            self.sock.sendto(a2s_getchallenge_req(), self.srvaddr)
            inforsp = recvresponse(self.sock)
            self._challenge = a2s_getchallenge_rsp(inforsp)["challenge"]
        return self._challenge

    @property
    def players(self):
        """ Players. """
        if self._players is None:
            challenge = self.challenge
            while True:
                try:
                    self.sock.sendto(a2s_getplayers_req(challenge), self.srvaddr)
                    inforsp = recvresponse(self.sock)
                    self._players = a2s_getplayers_rsp(inforsp)["players"]
                except RetryPlox, err:
                    challenge = err.args[0]
                else:
                    break
        return self._players

    @property
    def rules(self):
        """ Rules (aka CVars). """
        if self._rules is None:
            challenge = self.challenge
            while True:
                try:
                    self.sock.sendto(a2s_getrules_req(challenge), self.srvaddr)
                    inforsp = recvresponse(self.sock)
                    self._rules = a2s_getrules_rsp(inforsp)["rules"]
                except RetryPlox, err:
                    challenge = err.args[0]
                else:
                    break
        return self._rules



def main():
    parser = OptionParser(usage="%prog [options] <server>")

    parser.add_option( "-p", "--port",
        help="The server port.",
        default=27015, type="int"
        )

    parser.add_option( "-P", "--players",
        help="List players on the server.",
        default=False, action="store_true"
        )

    parser.add_option( "-r", "--rules",
        help="List server rules (that is, CVars).",
        default=False, action="store_true"
        )

    parser.add_option( "-g", "--getrule",
        help="Get the value for one specific rule only (implies -r).",
        default=None
        )

    options, progargs = parser.parse_args()

    if len(progargs) != 1:
        return "Wrong number of arguments, see -h"

    ds = SRCDS(progargs[0], options.port)

    table = PrettyTable(["Field", "Value"])
    table.align["Field"] = "l"
    table.align["Value"] = "l"
    for item in ds.info.items():
        table.add_row(item)
    print table.get_string(sortby="Field")

    if options.players:
        table = PrettyTable(["Name", "Score", "Online since"])
        table.align["Name"] = "l"
        table.align["Score"] = "r"
        table.align["Online since"] = "l"
        for player in ds.players:
            table.add_row([ player["name"], player["score"], player["duration"] ])
        print table.get_string(sortby="Score")

    if options.rules or options.getrule:
        if options.getrule is None:
            table = PrettyTable(["CVar", "Value"])
            table.align["CVar"] = "l"
            table.align["Value"] = "l"
            for item in ds.rules.items():
                table.add_row(item)
            print table.get_string(sortby="CVar")
        else:
            print "%s = %s" % (options.getrule, ds.rules[options.getrule])


if __name__ == '__main__':
    sys.exit(main())
