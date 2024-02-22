# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from wolfobject import WolfObject

class Target(WolfObject):
    objtype = "target"

    def __init__(self, conf, name, args, params):
        WolfObject.__init__(self, conf, name, args, params)
        self.target_checks = []
