#!/usr/bin/python
# kate: space-indent on; indent-width 4; replace-tabs on;

"""
zsync -- synchronize Zarafa contacts to the local machine and search for CallerIDs.

zsync is a tool that uses the Zarafa WebApp to download a user's contact list, cache
it on the local system, and search through them in order to resolve CallerIDs to names.

Setup:

1. Create a file named ~/.zsync/zsyncrc and configure the following variables in it:

    [zarafa-webapp]
    url      = https://your.zarafa-server.com/webapp
    username = your username
    password = your password

    [asterisk]
    envvar = ASTERISK_CALLERID_NUM
    unify_fallback = yes

2. Modify the Asterisk dialplan to call the script for name resolution, like so:

    same => n,Set(ENV(ASTERISK_CALLERID_NUM)=${CALLERID(num)})
    same => n,Set(CALLERID(name)=${SHELL(/usr/local/bin/zsync cachesearch):0:-1})

   CALLERID(num) can be passed using an environment variable to prevent malicious
   callerids from modifying the shell command.

3. Create a cron job that regularly calls "zsync cacheupdate".

4. Check out this PHP script that returns the callee's name for outgoing calls:

    https://bitbucket.org/Svedrin/misc/src/tip/php/getrpid.php
"""

import requests
import json
import sys
import re
import os

from ConfigParser import ConfigParser

CONF = ConfigParser()
CONF.read(os.path.expanduser("~/.zsync/zsyncrc"))

def unify_number(number):
    """ Turns any number given into +49123456, be it 0123456, 0049123456 or +49123456 already. """
    if number.startswith("00"):
        return "+" + number[2:]
    if number.startswith("0"):
        return "+49" + number[1:]
    return number

def get_contacts():
    """ Generator that connects to the Zarafa WebApp and queries all contacts from it. """
    root_url = CONF.get("zarafa-webapp", "url")
    username = CONF.get("zarafa-webapp", "username")
    password = CONF.get("zarafa-webapp", "password")

    index = requests.get(root_url + "/index.php", verify=False)
    sessioncookie = index.cookies["ZARAFA_WEBAPP"]

    logon = requests.post(root_url + "/index.php?logon", verify=False,
                          data={"username": username, "password": password},
                          cookies={"ZARAFA_WEBAPP": sessioncookie})

    settings = json.loads(re.findall(r'settings = ({.*});', logon.content)[0])

    if not CONF.has_option("zarafa", "store_entryid") or not CONF.has_option("zarafa", "entryid"):
        contact_folders = settings["zarafa"]["v1"]["state"]["models"]["contact"]["last_used_folders"]
        store_entryid   = contact_folders.keys()[0]
        entryid         = contact_folders[store_entryid][0]
    else:
        store_entryid   = CONF.get("zarafa", "store_entryid")
        entryid         = CONF.get("zarafa", "entryid")

    start = 0
    while True:
        contacts = requests.post("%s/zarafa.php?sessionid=%s&subsystem=webapp_1399492215843" % (root_url, sessioncookie), verify=False,
                                data=json.dumps({
                                    "zarafa": {
                                        "contactlistmodule": {
                                            "contactlistmodule1": {
                                                "list": {
                                                    "restriction": {
                                                        "start": start,
                                                        "limit": 50
                                                    },
                                                    "store_entryid": store_entryid,
                                                    "entryid": entryid,
                                                    "sort": [{"field": "fileas", "direction": "ASC"}],
                                                    "groupdir": "ASC"
                                                }
                                            }
                                        }
                                    }
                                }),
                                cookies={"ZARAFA_WEBAPP": sessioncookie})

        start += 50

        contactlist = contacts.json()["zarafa"]["contactlistmodule"]["contactlistmodule1"]["list"]["item"]

        if not contactlist:
            raise StopIteration

        for contactinfo in contactlist:
            yield contactinfo

def update_cache():
    """ Update the contacts.json cache file. """
    with open(os.path.expanduser("~/.zsync/contacts.json"), "wb") as cachefd:
        json.dump(list(get_contacts()), cachefd)

def get_cached_contacts():
    """ Generator that gets contacts from the contacts.json cache file. """
    with open(os.path.expanduser("~/.zsync/contacts.json"), "rb") as cachefd:
        for contactinfo in json.load(cachefd):
            yield contactinfo

def find_callerid(number, source):
    """ Finds the callerid to be displayed, searching the directory given in `source'. """

    target_number = unify_number(number)

    for contactinfo in source():
        for field in ("cellular_telephone_number", "business2_telephone_number", "business_telephone_number", "home_telephone_number", "home2_telephone_number"):
            if field in contactinfo["props"]:
                if unify_number(contactinfo["props"][field]) == target_number:
                    return contactinfo["props"]["fileas"]

    if CONF.getboolean("asterisk", "unify_fallback"):
        return target_number
    else:
        return number

def get_number():
    """ Get the number to look for from the environment variable named in the config,
        if that environment variable is set; otherwise, try to get it from the command
        line arguments.
    """
    envvar = CONF.get("asterisk", "envvar")
    if envvar in os.environ:
        return os.environ[envvar]
    elif len(sys.argv) > 2:
        return sys.argv[2]
    else:
        raise ValueError("this command requires a telephone number to look for")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print ("Usage: zsync.py <command> [<args>]\n\n"
               "Valid commands are:\n"
               " * search:      Searches Zarafa for an entry\n"
               " * cacheupdate: Updates the contact cache\n"
               " * cachesearch: Searches the contact cache for an entry\n"
               "The search and cachesearch commands expect the telephone number to search for as their argument.")
        sys.exit(1)

    command = sys.argv[1]

    if command == "search":
        print find_callerid(get_number(), get_contacts)
    elif command == "cacheupdate":
        update_cache()
    elif command == "cachesearch":
        print find_callerid(get_number(), get_cached_contacts)
    else:
        print "unknown command"
