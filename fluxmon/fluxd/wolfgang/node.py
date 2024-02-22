# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from target import Target

class Node(Target):
    objtype = "node"

    def __init__(self, conf, name, args, params):
        Target.__init__(self, conf, name, args, params)
        self.checks = []
