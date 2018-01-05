import math

from time import time, sleep
from collections import defaultdict

# refer to:
# https://github.com/haad/net-snmp/blob/master/agent/mibgroup/ucd-snmp/diskio.c#L694
# https://en.wikipedia.org/wiki/Moving_average#Application_to_measuring_computer_performance

INTERVAL = 5.0

FAC_LA1  = math.exp(-INTERVAL / ( 1 * 60.))
FAC_LA5  = math.exp(-INTERVAL / ( 5 * 60.))
FAC_LA15 = math.exp(-INTERVAL / (15 * 60.))


class DiskStats(object):
    def __init__(self):
        self.disk_name   = None
        self.prev_time   = None
        self.used_millis = None
        self.percent     = None
        self.la1         = None
        self.la5         = None
        self.la15        = None

    def for_disk(self, disk_name):
        if self.disk_name is None:
            self.disk_name = disk_name
        assert self.disk_name == disk_name
        return self

    def ingest(self, time, used_millis):
        def avg_if_not_none(self_la, fac, curr_percent):
            if self_la is None:
                return curr_percent
            else:
                return (self_la * fac) + (curr_percent * (1 - fac))

        if self.prev_time is not None:
            self.percent = (used_millis - self.used_millis) / 1000. / (time - self.prev_time) * 100
            self.la1     = avg_if_not_none(self.la1,  FAC_LA1,  self.percent)
            self.la5     = avg_if_not_none(self.la5,  FAC_LA5,  self.percent)
            self.la15    = avg_if_not_none(self.la15, FAC_LA15, self.percent)

        self.prev_time = time
        self.used_millis = used_millis
        return self

    def print_(self):
        if self.percent is not None:
            print "%-15s: %8.3f %8.3f %8.3f %8.3f" % (self.disk_name, self.percent, self.la1, self.la5, self.la15)
        return self


def main():
    statistico = defaultdict(DiskStats)

    while True:
        now = time()

        with open("/proc/diskstats", "rb") as fd:
            for line in fd:
                fields = line.strip().split()
                disk_name    = fields[2]
                disk_umillis = int(fields[-2])

                if not disk_name.startswith("sd"):
                    continue

                statistico[disk_name]           \
                    .for_disk(disk_name)        \
                    .ingest(now, disk_umillis)  \
                    .print_()

        print
        sleep(INTERVAL)


if __name__ == '__main__':
    main()
