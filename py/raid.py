#!/usr/bin/env python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from __future__ import division

import sys
import re

from optparse import OptionParser
from math import log, ceil



mult = ['', 'k', 'M', 'G', 'T', 'P', 'E']

units = {
    "usablesize":  "B",
    "totalsize":   "B",
    "chunksize":   "B",
    "stripewidth": "B",
    "sectorsize":  "B",
}


def headline(line):
    print "=" * len(line)
    print line
    print "=" * len(line)
    print


def from_number_with_unit(value, base=1024):
    """ Convert a string like "11234", "4.5k", "4ki" or "300G" to an int.

        The `base' param is one of 1000 or 1024 and defines whether "4k" should mean
        4000 or 4096. This is relevant because disk vendors usually define 300G to
        mean 300000000000 bytes, whereas that would only be 279G for the file system.

        Note that a suffix of "i" will always cause the base to be set to 1024, no
        matter what value has been passed in.
    """
    try:
        return int(value)
    except ValueError:
        facs = ''.join(mult)
        m = re.match(r'^(?P<value>[\d.]+)(?P<fac>[' + facs + r']?)(?P<i>i?)$', value)
        if m is None:
            raise ValueError("invalid number syntax: '%s'" % value)
        if m.group("i") == "i":
            base = 1024
        return int( float(m.group("value")) * (base ** mult.index(m.group("fac"))) )

def parse_number_with_unit(option, opt_str, value, parser):
    """ OptionParser callback that converts stuff like 256k to ints. """
    setattr( parser.values, option.dest, from_number_with_unit(value) )


def parse_disksize_with_unit(option, opt_str, value, parser):
    """ OptionParser callback that converts stuff like 300G to ints. """
    setattr( parser.values, option.dest, from_number_with_unit(value, base=1000) )


def to_number_with_unit(value, unit, base=1024):
    """ Try to convert the given value to a number string like 14MiB. """
    for exp, facunit in enumerate(mult):
        factor = base ** exp
        divided = value / factor
        if 1 <= divided < base:
            value = divided
            if base == 1024:
                unit = facunit + "i" + unit
            else:
                unit = facunit + unit
            break
    try:
        if value == int(value):
            return "%d%s" % (value, unit)
        else:
            return "{:,.3f}{:}".format(value, unit)
    except (AttributeError, ValueError): # python 2.5 and 2.6 respectively
        return str(value) + unit


def printv(label, value, unit=""):
    print "%-20s: %s%s" % (label, value, unit)

def pluralize(string, value):
    if value > 1:
        return string + "s"
    return string

class FilterLibrary(type):
    """ Meta class that keeps a library of defined checks. """
    filters = {}

    def __init__( cls, name, bases, attrs ):
        type.__init__( cls, name, bases, attrs )
        if name != "Filter" and name.endswith("Filter") and not name.startswith("Abstract"):
            FilterLibrary.filters[ name.replace("Filter", "").lower() ] = cls


class Filter(object):
    __metaclass__ = FilterLibrary

    def __init__(self, predecessor, options):
        self.confmsgs = []
        self.errors = []
        self.messages = []
        self.predecessor = predecessor
        self.options = options
        self.looksgood = True

    def getopt(self, data, field, default=None):
        """ Retrieve the field from options, then data, then default. """
        val = getattr(self.options, field)
        if val is not None:
            return val
        elif field in data:
            return data[field]
        else:
            return default

    def conf(self, data):
        """ Configuration post-processing. """
        data["looksgood"] = self.looksgood
        for name, value in data.items():
            if name in ("spares", "parity"): continue
            if type(value) in (int, float):
                self.confmsgs.append("%-20s: %s" % (name, to_number_with_unit(value, units.get(name, ""))))
            else:
                self.confmsgs.append("%-20s: %s" % (name, value))
        return data

    def message(self, *args, **kwargs):
        """ Add a message to be printed. """
        self.messages.extend(args)
        for name, value in kwargs.items():
            self.messages.append( "%-20s: %s" % (name, value) )

    def error(self, **kwargs):
        """ Add an error message to be printed and set looksgood to False. """
        self.looksgood = False
        for field, errorstr in kwargs.items():
            self.errors.append({"field": field, "errorstr": errorstr})

    def print_messages(self, verbose):
        """ Print stored messages. If verbose, the config is dumped as well. """
        if self.predecessor is not None:
            self.predecessor.print_messages(verbose)
        headline(self.__class__.__name__.replace("Filter", ""))
        if verbose:
            for message in self.confmsgs:
                print "C: %s" % message
        for message in self.messages:
            print "I: %s" % message
        for error in self.errors:
            print "E: %(field)-20s: %(errorstr)s" % error
        print

    def prepare_parser(self, parser):
        """ Stub to prepare OptionParser for derived filter classes. """
        pass


class DisksFilter(Filter):
    def __call__(self):
        self.message("Using %d disks." % self.options.disks)

        return self.conf({
            "devices":        self.options.disks,
            "urerate":        self.options.urerate,
            "type":           "disk",
            "usablesize":     self.options.disksize,
            "totalsize":      self.options.disksize,
            "sectorsize":     self.options.sectorsize,
            "spares": [],
            "parity": [],
            "looksgood": True
        })

    def prepare_parser(self, parser):
        parser.add_option("-d", "--disks", default=5, type="int",
            help="Total number of disks.")
        parser.add_option("-D", "--disksize", default=0,
            action="callback", callback=parse_disksize_with_unit, type="str",
            help="Disk size. Default: 0 (Unknown).")
        parser.add_option("-u", "--urerate", default=14, type="int",
            help='Probability for an Unrecoverable Read Error (URE), specified as "one per 10^X Bits read". Default: 14.')
        parser.add_option("-s", "--sectorsize",  default=512,
            action="callback", callback=parse_number_with_unit, type="str",
            help="Block size of your disks (that is, the smallest amount of data that can be "
                "written on any one disk without triggering a read-modify-write cycle on that disk). Default: 512B.")



class AbstractRaidFilter(Filter):
    def __call__(self):
        data = self.predecessor()
        self.looksgood = data["looksgood"]

        chunksize = self.getopt(data, "chunksize", 256 * 1024)

        if self.options.raiddisks is not None:
            raiddisks = self.options.raiddisks
        else:
            raiddisks = self.get_default_nrdisks(data["devices"], chunksize)

        if raiddisks <= 1:
            raise ValueError("Invalid RAID array configuration: RAID disks = %d" % raiddisks)

        nr_raids  = data["devices"] // raiddisks
        datadisks = self.get_datadisks(raiddisks)
        if datadisks < 1:
            raise ValueError("Invalid RAID array configuration: data disks = %d" % datadisks)

        self.message("Creating %d %s with %d disks (%d data disks) per array" % (nr_raids, pluralize("array", nr_raids), raiddisks, datadisks))

        self.message(
            "mdadm --create --verbose --chunk=%d /dev/mdX --level=%d --raid-devices=%d <device ...>" % (
            chunksize / 1024, self.level, raiddisks))

        if datadisks not in (2, 4):
            self.error(devices="Should have exactly two or four data disks")

        if data["devices"] % raiddisks != 0:
            data["spares"].append({
                "type":    data["type"],
                "devices": data["devices"] % raiddisks
                })
        elif self.level != 0:
            self.error(devices="No spares")

        if datadisks < raiddisks:
            data["parity"].append({
                "type":    data["type"],
                "devices": (raiddisks - datadisks) * nr_raids
                })

            if raiddisks - datadisks == 1:
                databits = data["usablesize"] * datadisks * 8
                # The probability for one random read on a single disk to fail is 1/10**<urerate>.
                # If we have more than one parity disk, this needs to fail on *all* disks in order
                # for the read to have failed, meaning the probability for that is
                # P(fail on one disk) ** <number of parity disks>.
                # So the probability for one read to succeed is (1 - above), and the probability
                # for ALL reads to succeed is (1 - above) ** (number of bits we have to read).
                # TODO: Sadly, P(fail on one disk) ** <number of parity disks> is so close to zero
                #       (around 1e-196) that 1 - P(fail on one disk) ** <number of parity disks> is
                #       always 1.0. Wat do?
                rebuildp = (1 - (1/10**data["urerate"])) ** databits
                self.message( "This array has a probability of %.2f%% for a rebuild to succeed." % (rebuildp * 100) )

        return self.conf({
            "devices":     nr_raids,
            "type":        "raid",
            "datadisks":   datadisks,
            "totaldisks":  raiddisks,
            "physdatadisks":  data["physdatadisks"]  * datadisks if "physdatadisks"  in data else datadisks,
            "phystotaldisks": data["phystotaldisks"] * datadisks if "phystotaldisks" in data else raiddisks,
            "usablesize":  data["usablesize"] * datadisks,
            "totalsize":   data["totalsize"]  * raiddisks,
            "chunksize":   chunksize,
            "stripewidth": chunksize * datadisks,
            "sectorsize":  data["sectorsize"],
            "spares":      data["spares"],
            "parity":      data["parity"],
            "urerate":     data["urerate"],
        })

    def prepare_parser(self, parser):
        parser.add_option("-d", "--raiddisks", default=None, type="int",
            help="Total number of disks per RAID array.")
        parser.add_option("-c", "--chunksize",  default=None, action="callback", callback=parse_number_with_unit, type="str",
            help="Chunk size.")

class Raid0Filter(AbstractRaidFilter):
    level = 0

    def get_default_nrdisks(self, nr_disks, chunksize):
        return min(nr_disks, 1024**2 / chunksize)

    def get_datadisks(self, nr_disks):
        return nr_disks

class Raid1Filter(AbstractRaidFilter):
    level = 1

    def get_default_nrdisks(self, nr_disks, chunksize):
        return 2

    def get_datadisks(self, nr_disks):
        return 1

class Raid5Filter(AbstractRaidFilter):
    level = 5

    def get_default_nrdisks(self, nr_disks, chunksize):
        return min(nr_disks, 1024**2 / chunksize + 1)

    def get_datadisks(self, nr_disks):
        return nr_disks - 1

class Raid6Filter(AbstractRaidFilter):
    level = 6

    def get_default_nrdisks(self, nr_disks, chunksize):
        return min(nr_disks, 1024**2 / chunksize + 2)

    def get_datadisks(self, nr_disks):
        return nr_disks - 2

class Raid10Filter(Raid1Filter, Raid0Filter):
    level = 10

    def get_default_nrdisks(self, nr_disks, chunksize):
        return min(nr_disks // 2, 1024**2 / chunksize) * 2

    def get_datadisks(self, nr_disks):
        return nr_disks / 2



class LvmFilter(Filter):
    def __call__(self):
        data = self.predecessor()
        self.looksgood = data["looksgood"]
        if data["devices"] > 1:
            self.message("Consider using raid0 instead of adding multiple PVs.")
        if log(self.options.extentsize, 2) % 1 != 0:
            self.error(extentsize="Invalid extent size (not a power of two).")
        elif self.options.extentsize != 4 * 1024**2:
            self.message("vgcreate --physicalextentsize=%dB" % (self.options.extentsize))
        if "chunksize" in data and self.options.extentsize % data["chunksize"] != 0:
            self.error(chunksize="Extents are not aligned to the beginning of a chunk")
        if "stripewidth" in data:
            if self.options.extentsize % data["stripewidth"] != 0:
                self.error(extentsize="Extent borders are not aligned to the beginning and end of a stripe")
            if 1024**2 % data["stripewidth"] != 0:
                self.error(stripewidth="PV data areas won't be aligned correctly (offset of 1MiB is not the beginning of a stripe).")
            if data["stripewidth"] == 1024**2:
                self.message("Stripe width is optimal")
        data["devices"] = self.options.lvs
        if self.options.lvsize:
            if self.options.lvsize % self.options.extentsize == 0:
                data["usablesize"] = self.options.lvsize
            else:
                fullextents = self.options.lvsize // self.options.extentsize
                data["usablesize"] = self.options.extentsize * (fullextents + 1)
        data["type"] = "lv"
        return self.conf(data)

    def prepare_parser(self, parser):
        parser.add_option("-l", "--lvs", default=1, type="int",
            help="Number of LVs to be created.")
        parser.add_option("-L", "--lvsize", default=None,
            action="callback", callback=parse_number_with_unit, type="str",
            help="Size of LVs to be created.")
        parser.add_option("-e", "--extentsize", default=4*1024**2,
            action="callback", callback=parse_number_with_unit, type="str",
            help="Extent size used by LVM in order to allocate volumes. Default: 4MiB.")



class PtFilter(Filter):
    def __call__(self):
        data = self.predecessor()
        self.looksgood = data["looksgood"]
        if "stripewidth" in data:
            if 1024**2 % data["stripewidth"] != 0:
                self.error(stripewidth="Sector 2048 is not aligned correctly (offset of 1MiB is not the beginning of a stripe).")
            if data["stripewidth"] == 1024**2:
                self.message("Stripe width is optimal")
            if self.options.partoffset * data["sectorsize"] % data["stripewidth"] != 0:
                stripes  = int(self.options.partoffset * data["sectorsize"] / data["stripewidth"])
                optstart = int((stripes + 1) * data["stripewidth"] / data["sectorsize"])
                self.error(partoffset="Partition start is not aligned to the beginning of a stripe (should be %ds)." % optstart)
        data["type"] = "partition"
        return self.conf(data)

    def prepare_parser(self, parser):
        parser.add_option("-o", "--partoffset", default=2048, type="int",
            help="Partition start offset, in Sectors. Default: 2048.")



class DrbdFilter(Filter):
    def __call__(self):
        data = self.predecessor()
        if "usablesize" in data and data["usablesize"]:
            # 1*512/1024**2 = 1/2048
            metadata = (ceil(data["usablesize"] / 512 / 2**18) * 8 + 72) * 512
            self.message(metadata=to_number_with_unit(metadata, "B"))
            data["usablesize"] -= metadata
        return self.conf(data)



class AbstractFileSystemFilter(Filter):
    def prepare_parser(self, parser):
        parser.add_option("-b", "--blocksize", default=4096,
            action="callback", callback=parse_number_with_unit, type="str",
            help="File system block size. Default: 4kiB.")

class ExtFilter(AbstractFileSystemFilter):
    def __call__(self):
        data = self.predecessor()
        self.looksgood = data["looksgood"]
        if "chunksize" in data:
            stride = data["chunksize"] / self.options.blocksize
            stripe_width_blocks = stride * data["datadisks"]
            self.message("mke2fs -j -b %d -E stride=%d,stripe_width=%d <device>" % (self.options.blocksize, stride, stripe_width_blocks))
        data["type"] = "filesystem"
        return self.conf(data)

class XfsFilter(AbstractFileSystemFilter):
    def __call__(self):
        data = self.predecessor()
        self.looksgood = data["looksgood"]

        if "chunksize" in data:
            chunksz = to_number_with_unit(data["chunksize"], "B").replace("iB", "") # mkfs doesn't like iB at the end
            sectsz = ""
            if True or data["sectorsize"] != 512:
                sectsz = "-s size=%d " % data["sectorsize"]
            self.message("mkfs -t xfs -b size=%d %s-d su=%s -d sw=%d -l su=%s <device>" % (self.options.blocksize,
                sectsz, chunksz, data["datadisks"], chunksz))

        data["type"] = "filesystem"
        return self.conf(data)


class ZfsFilter(AbstractFileSystemFilter):
    def __call__(self):
        data = self.predecessor()
        self.looksgood = data["looksgood"]

        if "usablesize" in data and data["usablesize"]:
            self.message(ddt_size=to_number_with_unit(data["usablesize"] / (256 * 1024) * 320, "B"))

        data["type"] = "filesystem"
        return self.conf(data)


def parse_args(args=None, filter=None):
    """ Parse arguments for a given filter. """
    parser = OptionParser(usage="Usage: %prog [<program options>] <filter [<filter options>] ...>\n\n"
        "Options that require a number of Bytes as an argument also accept values given \n"
        "as e.g. 256k = 256 * 1024 Bytes. Units that are understood are k, M, G, T, P, E.\n\n"
        "Note that you will only want to change the number of disks in your array (-d) \n"
        "and the RAID level. Leave the other values to their defaults (and make sure those\n"
        "defaults are actually used in your system).\n\n"
        "For a list of available filters, use --listfilters. For help on a specific filter, use\n"
        "%prog <filter> -h.")

    parser.add_option("-v", "--verbose", default=False,
        action="store_true", help="Print Informational and Configuration messages.")

    parser.add_option("--listfilters", default=False,
        action="store_true", help="List available filters.")

    if filter is not None:
        filter.prepare_parser(parser)

    return parser.parse_args(args=args)


def main():
    topfilter = DisksFilter(None, None)
    currargs  = []
    listfilters = False
    verbose = False

    if len(sys.argv) == 1:
        parse_args(["-h"], topfilter)

    sys.argv.append("END")
    for arg in sys.argv[1:]:
        if arg in ('-h', '--help'):
            if topfilter is None:
                parse_args()
                return 0

        if not arg.startswith('-'):
            if arg == "END" or arg in FilterLibrary.filters:
                options, posargs = parse_args(currargs, topfilter)
                if posargs:
                    raise ValueError("Found some positional arguments, but filters don't take any: " + str(posargs))
                topfilter.options = options
                if arg == "END":
                    break
                topfilter = FilterLibrary.filters[arg](topfilter, None)
                currargs  = []
            else:
                # looks like this was an argument for an option of the last filter
                currargs.append(arg)
        elif arg in ('-v', '--verbose'):
            verbose = True
        elif arg == '--listfilters':
            listfilters = True
        else:
            currargs.append(arg)

    if listfilters:
        print "Available filters:"
        for filtername in FilterLibrary.filters:
            print filtername
        return 0

    data = topfilter()
    topfilter.print_messages(verbose)

    headline("Overall evaluation")
    printv( "Things look good", "Yes" if data["looksgood"] else "No" )
    printv( "Resulting device", pluralize("%(devices)d %(type)s" % data, data["devices"]) )

    if data["usablesize"]:
        if data["devices"] == 1:
            printv( "Usable space", to_number_with_unit(data["usablesize"], "B") )
            printv( "Total space", to_number_with_unit(data["totalsize"], "B") )
        else:
            printv( "Usable space (per device)", to_number_with_unit(data["usablesize"], "B") )
            printv( "Total space (per device)", to_number_with_unit(data["totalsize"], "B") )
            printv( "Usable space (all devices)", to_number_with_unit(data["usablesize"] * data["devices"], "B") )
            printv( "Total space (all devices)", to_number_with_unit(data["totalsize"] * data["devices"], "B") )

    if data["spares"]:
        print
        print "Spares:"
        for spare in data["spares"]:
            print pluralize("* %(devices)d %(type)s" % spare, spare["devices"])

    if data["parity"]:
        print
        print "Parity:"
        for spare in data["parity"]:
            print pluralize("* %(devices)d %(type)s" % spare, spare["devices"])

    return 0



if __name__ == '__main__':
    sys.exit(main())
