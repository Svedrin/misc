# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os

from wolfobject import WolfObjectMeta
from observer   import Dispatcher
from threading  import RLock

class ConfigSyntaxError(Exception):
    pass


def confparse(fpath, add_object):
    with open(fpath, "rb") as fd:
        ST_BEGINSTANZA, ST_OBJTYPE, ST_OBJNAME, ST_ARGS, ST_PARAMVALUE, ST_PARAMQUOTEDVALUE, ST_COMMENT = range(7)
        state = ST_BEGINSTANZA

        lineno  = 1
        objtype = ""
        objname = ""
        args    = []
        params  = {}
        currarg = ""
        currval = ""
        escaped = False

        while True:
            buf = fd.read(4096)
            if not buf:
                break

            for char in buf:
                if char == "\r":
                    continue

                if state == ST_BEGINSTANZA:
                    if char == '#':
                        state = ST_COMMENT
                    elif char in (" ", "\t"):
                        continue
                    elif char == "\n":
                        lineno += 1
                        continue
                    else:
                        state = ST_OBJTYPE
                        objtype += char

                elif state == ST_OBJTYPE:
                    if char in (" ", "\t"):
                        state = ST_OBJNAME
                    elif char == "\n":
                        raise ConfigSyntaxError("Unexpected EOL after object type '%s' in line %d" % (objtype, lineno))
                    else:
                        objtype += char

                elif state == ST_OBJNAME:
                    if char in (" ", "\t"):
                        state = ST_ARGS
                    elif char == "\n":
                        add_object(objtype, objname, [], {})
                        objtype = ""
                        objname = ""
                        state = ST_BEGINSTANZA
                        lineno += 1
                    else:
                        objname += char

                elif state == ST_ARGS:
                    if char in (" ", "\t", "\n"):
                        if currarg:
                            args.append(currarg)
                            currarg = ""
                        if char == "\n":
                            if not escaped:
                                add_object(objtype, objname, args, params)
                                objtype = ""
                                objname = ""
                                args = []
                                params = {}
                                state = ST_BEGINSTANZA
                            else:
                                escaped = False
                            lineno += 1
                    elif char == "\\":
                        if not escaped:
                            escaped = True
                        else:
                            currarg += "\\"
                            escaped = False
                    elif char == "=":
                        state = ST_PARAMVALUE
                    else:
                        currarg += char

                elif state == ST_PARAMVALUE:
                    if char == '"':
                        state = ST_PARAMQUOTEDVALUE
                    elif char in (" ", "\t", "\n"):
                        params[currarg] = currval
                        currarg = ""
                        currval = ""
                        if char == "\n":
                            add_object(objtype, objname, args, params)
                            objtype = ""
                            objname = ""
                            args = []
                            params = {}
                            state = ST_BEGINSTANZA
                            lineno += 1
                        else:
                            state = ST_ARGS
                    else:
                        currval += char

                elif state == ST_PARAMQUOTEDVALUE:
                    if char == '"':
                        params[currarg] = currval
                        currarg = ""
                        currval = ""
                        state = ST_ARGS
                    else:
                        currval += char

                elif state == ST_COMMENT:
                    if char == "\n":
                        state = ST_BEGINSTANZA



class WolfConfig(object):
    def __init__(self, fpath):
        self.fpath   = fpath
        self.objects = {}
        self.objmap  = {}
        self._lock   = RLock()
        self.event   = Dispatcher()
        self.event["object_added"] = False
        self.event["object_param_changed"] = False
        self.environ = {}

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def _add_object(self, objtype, objname, args, params):
        if objname in self.objects:
            raise ValueError("An object named '%s' already exists." % objname)
        obj = WolfObjectMeta.objtypes[objtype]( self, objname, args, params )
        self.objects[objname] = obj
        self.objmap[obj.params["uuid"]] = obj
        return obj

    def add_object(self, objtype, objname, args, params):
        self.lock()
        try:
            obj = self._add_object(objtype, objname, args, params)
            self.write()
            self.event("object_added", obj)
            return obj
        finally:
            self.unlock()

    def set_object_param(self, uuid, param, value):
        self.lock()
        try:
            self.objmap[uuid][param] = value
            self.write()
            self.event("object_param_changed", self.objmap[uuid], param, value)
        finally:
            self.unlock()

    def find_object(self, name_or_uuid):
        if name_or_uuid in self.objmap:
            return self.objmap[name_or_uuid]
        if name_or_uuid in self.objects:
            return self.objects[name_or_uuid]
        raise KeyError("No such object: '%s'" % name_or_uuid)

    def find_objects_by_type(self, objtype):
        return [obj for obj in self.objects.values() if obj.objtype == objtype]

    def parse(self):
        return confparse(self.fpath, self._add_object)

    def write(self):
        if os.path.exists(self.fpath):
            stat = os.stat(self.fpath)
        else:
            stat = None
        fd = open(self.fpath + ".new", "wb", False) # open unbuffered tempfile
        try:
            print >> fd, "# kate: space-indent on; indent-width 4; replace-tabs on;\n"
            serialize_order = [
                "cluster", "node", "target", "connection", "notify", "contact", "contactgroup",
                "checkplugin", "check", "aggregate", "view"
                ]
            objs_by_type = {}
            for obj in self.objmap.values():
                if obj.objtype not in objs_by_type:
                    objs_by_type[obj.objtype] = [obj]
                else:
                    objs_by_type[obj.objtype].append(obj)
            for objtype in serialize_order:
                if objtype not in objs_by_type:
                    continue
                for obj in objs_by_type[objtype]:
                    print >> fd, obj.get_config_stanza()
                print >> fd, ""
            if stat is not None:
                # keep permissions
                os.fchmod(fd.fileno(), stat.st_mode)
                if os.geteuid() == 0:
                    os.fchown(fd.fileno(), stat.st_uid, stat.st_gid)
        finally:
            fd.close()
        os.rename(self.fpath + ".new", self.fpath)
