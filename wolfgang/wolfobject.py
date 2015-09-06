# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from uuid import uuid4

class WolfObjectMeta(type):
    """ Meta class that keeps track of known object types. """
    objtypes = {}

    def __init__( cls, name, bases, attrs ):
        type.__init__( cls, name, bases, attrs )
        if cls.objtype in WolfObjectMeta.objtypes:
            raise SyntaxError("Object Type '%s' already exists." % cls.objtype)
        WolfObjectMeta.objtypes[cls.objtype] = cls


class WolfObject(object):
    __metaclass__ = WolfObjectMeta
    objtype = "object"

    def __init__(self, conf, name, args, params):
        self._conf  = conf
        self.name   = name
        self.args   = args
        self.params = params
        if "uuid" not in self.params:
            self.params["uuid"] = str(uuid4())

    def __unicode__(self):
        return "<%s %s>" % ( self.objtype, self.name )

    __repr__ = __unicode__

    def __eq__(self, other):
        return isinstance(other, WolfObject) and self.params["uuid"] == other.params["uuid"]

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.args[key]
        return self.params[key]

    def __setitem__(self, key, val):
        if isinstance(key, int):
            self.args[key] = val
        self.params[key] = val

    def _cmp_kws(self, a, b):
        if a == "uuid":
            return -1
        if b == "uuid":
            return 1
        return cmp(a, b)

    def get_config_stanza(self):
        kws = self.params.keys()
        kws.sort(cmp=self._cmp_kws)
        return " ".join( [self.objtype, self.name] + self.args + ['\\\n    %s="%s"' % (kw, self.params[kw]) for kw in kws] )

    def find_object(self, name_or_uuid):
        return self._conf.find_object(name_or_uuid)
