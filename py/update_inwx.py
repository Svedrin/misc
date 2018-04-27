# -*- coding: utf-8 -*-

import xmlrpclib
import socket
import ConfigParser
import os
import sys
import json
import yaml

config = ConfigParser.ConfigParser()
if not config.read('credentials.ini'):
    raise RuntimeError( "Failed to read config file." )


inwxurl  = config.get( "xmlrpc", "url" )
inwxuser = config.get( "xmlrpc", "user" )
inwxpass = config.get( "xmlrpc", "pass" )


"""
Dump a domain using a config such as this:

example.com:
    dump: "true"

the right-hand-side is a Python expression to filter by:

example.com:
    dump: '"www" in name'
"""

serv = xmlrpclib.Server( inwxurl )

with open(sys.argv[1], "rb") as fd:
    conf = yaml.load(fd)


for domain, command in conf.items():
    resp = serv.nameserver.info( { 'user': inwxuser, 'pass': inwxpass, 'lang': 'en', 'domain': domain })

    if resp['code'] == 2500:
        print "inwx can haz a db overload, skipping"
        sys.exit(1)

    if not "resData" in resp:
        print >> sys.stderr, "Got a strange response from inwx:", resp
        sys.exit(1)

    for action, params in command.items():
        if action == "dump":
            outyaml = {}
            for record in resp['resData']['record']:
                if eval(params, {'__builtins__': None, "true": True, "false": False}, record):
                    outyaml[record["name"]] = "%(ttl)d %(type)s %(content)s" % record
            print yaml.dump({domain: {"set": outyaml}}, default_flow_style=False)

        elif action == "set":
            for record_name, record_data in params.items():
                record_ttl, record_type, record_content = record_data.split(" ", 2)

                record = {
                    'user':    inwxuser,
                    'pass':    inwxpass,
                    'content': record_content,
                    'ttl':     record_ttl,
                    'type':    record_type
                }

                for inwxrecord in resp['resData']['record']:
                    if inwxrecord["name"] == record_name:
                        print "Set %s -> %s" % (record_name, record_data)
                        serv.nameserver.updateRecord(dict(record,
                            id = int(inwxrecord['id'])
                        ))
                        break
                else:
                    print "Add %s -> %s" % (record_name, record_data)
                    serv.nameserver.createRecord(dict(record,
                        domain = domain,
                        name   = record_name
                    ))

        elif action == "del":
            for record_name in params:
                for inwxrecord in resp['resData']['record']:
                    if inwxrecord["name"] == record_name:
                        print "Del %s (%s)" % (record_name, inwxrecord['id'])
                        serv.nameserver.deleteRecord({
                            'user': inwxuser,
                            'pass': inwxpass,
                            'id':   int(inwxrecord['id'])
                        })
                        break
                else:
                    print "Not found: %s" % record_name
