# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import json
import os

class CheckResultQueue(list):
    def __init__(self, check):
        self._check = check
        self.fpath = os.path.join(check._conf.environ["spooldir"], "%s.q.json" % check["uuid"])
        if os.path.exists(self.fpath):
            fd = open(self.fpath, "rb")
            try:
                for elem in json.load(fd):
                    list.append(self, elem)
            finally:
                fd.close()

    def sync(self):
        if os.path.exists(self.fpath):
            stat = os.stat(self.fpath)
        else:
            stat = None
        fd = open(self.fpath + ".new", "wb", False) # open unbuffered tempfile
        try:
            json.dump(self, fd)
            if stat is not None:
                # keep permissions
                os.fchmod(fd.fileno(), stat.st_mode)
                if os.geteuid() == 0:
                    os.fchown(fd.fileno(), stat.st_uid, stat.st_gid)
        finally:
            fd.close()
        # atomic commit (see <http://docs.python.org/library/os.html#os.rename>)
        os.rename(self.fpath + ".new", self.fpath)

    def append(self, result):
        list.append(self, result)
        self.sync()
