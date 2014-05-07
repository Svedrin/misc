#!/usr/bin/env python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import feedparser
import email
import imaplib
import requests
import sys
import hashlib
import json
import os.path
import threading
import traceback

from Queue import Queue
from BeautifulSoup import BeautifulSoup
from time     import time, mktime
from datetime import datetime


conf = json.load(open(os.path.expanduser("~/.rss2imap.conf")))

# Conf is a structure such as this:
#
# {
#    "imap": {
#        "host": "localhost",
#        "user": "your IMAP login name",
#        "pass": "your IMAP password"
#    },
#    "feeds": {
#        "Golem": {    <-- IMAP directory                  v Feeds to put in there
#            "Golem Security": "http://rss.golem.de/rss.php?feed=RSS1.0&tp=sec",
#            "Golem Internet": "http://rss.golem.de/rss.php?feed=RSS1.0&tp=inet",
#            "Golem Apps":     "http://rss.golem.de/rss.php?feed=RSS1.0&tp=apps"
#        },
#        "Comics": {
#            "QC":             "http://www.questionablecontent.net/QCRSS.xml",
#            "xkcd":           "http://xkcd.com/rss.xml",
#            "wumo":           "http://feeds.feedburner.com/wulffmorgenthaler",
#            "ahoipolloi":     "http://feed43.com/ahoipolloi.xml"
#            "Dilbert":        { "url": "http://feeds.feedburner.com/DilbertDailyStrip?format=xml", "proxy": "dilbert" },
#            "tpfd":           { "url": "http://www.toothpastefordinner.com/rss/rss.php",           "proxy": "tpfd" },
#        }
#    }
# }


content_template = """
<div style="background-color: #ededed; border: 1px solid grey; margin: 5px;">
    <table>
        <tr><td><b>Feed:</b></td><td>%(feed)s</td></tr>
        <tr><td><b>Item:</b></td><td><a href="%(link)s">%(title)s</td></tr>
    </table>
</div>
%(content)s
"""


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0 Iceweasel/24.0"

class DilbertProxy(object):
    def get_content(self, entry):
        req = requests.get(entry.link, headers={"User-Agent": USER_AGENT})
        soup = BeautifulSoup(req.content)
        for soupimg in soup.findAll("img"):
            if soupimg["src"].startswith("/dyn/str_strip/") and (soupimg["src"].endswith(".strip.gif") or soupimg["src"].endswith(".strip.sunday.gif")):
                return '<img src="http://www.dilbert.com%s">' % soupimg["src"]
        raise KeyError("Comic strip image not found!")

class TpfdProxy(object):
    def get_content(self, entry):
        entdate = datetime.fromtimestamp(mktime(entry.published_parsed)).strftime("%m%d%y")
        req = requests.get(entry.link, headers={"User-Agent": USER_AGENT})
        soup = BeautifulSoup(req.content)
        for soupimg in soup.findAll("img"):
            if soupimg["src"].startswith("http://www.toothpastefordinner.com/%s/" % entdate):
                return '<img src="%s">' % soupimg["src"]
        raise KeyError("Comic strip image not found!")

proxies = {
    "dilbert": DilbertProxy(),
    "tpfd":    TpfdProxy(),
}

serv = imaplib.IMAP4(conf["imap"]["host"])
serv.login(conf["imap"]["user"], conf["imap"]["pass"])


def go(func, *args, **kwargs):
    thr = threading.Thread(target=func, args=args, kwargs=kwargs)
    thr.daemon = True
    thr.start()
    return thr

def go_nodaemon(func, *args, **kwargs):
    thr = threading.Thread(target=func, args=args, kwargs=kwargs)
    thr.daemon = False
    thr.start()
    return thr


outq    = Queue()
checkq  = Queue()
uploadq = Queue()

@go
def printer():
    while True:
        msg = outq.get()
        print "[%s] %s" % (datetime.now(), msg)



# http://stackoverflow.com/questions/19130986/python-equivalent-of-golangs-select-on-channels
def select(*queues):
    combined = Queue()
    def listen_and_forward(queue):
        while True:
            combined.put((queue, queue.get()))
    for queue in queues:
        go(listen_and_forward, queue)
    while True:
        yield combined.get()


@go
def imapmaster():
    currmbox = None
    for whichq, command in select(checkq, uploadq):
        if whichq is checkq:
            returnq, mailbox, entid, entry = command
            if mailbox != currmbox:
                currmbox = mailbox
                serv.select(mailbox)

            typ, data = serv.search(None, '(HEADER X-RSS2IMAP-ID "%s")' % entid)

            if typ != "OK":
                outq.put("Querying the IMAP server failed")
                continue

            returnq.put((entid, entry, bool(data[0])))

        elif whichq is uploadq:
            returnq, mailbox, mp, timestamp = command
            if mailbox != currmbox:
                currmbox = mailbox
                serv.select(mailbox)
            if "-q" not in sys.argv:
                outq.put("putting new message to " + mailbox)
            serv.append(mailbox, "", imaplib.Time2Internaldate(timestamp), str(mp))
            returnq.put(True)


def process_feed(dirname, feedname, feedinfo):
    if "-q" not in sys.argv:
        outq.put("[%s] Started processing" % feedname)

    if isinstance(feedinfo, dict):
        feedurl   = feedinfo["url"]
        feedproxy = proxies[feedinfo["proxy"]]
    else:
        feedurl   = feedinfo
        feedproxy = None

    feed = feedparser.parse(feedurl)

    pending = Queue()
    pendingupload = Queue()
    outstanding = 0
    outstandingupload = 0

    for entry in feed.entries:
        if "id" not in entry or "title" not in entry:
            continue

        entid = hashlib.sha1(entry.id).hexdigest()
        checkq.put((pending, dirname, entid, entry))
        outstanding += 1

    if "-q" not in sys.argv:
        outq.put("[%s] Waiting for %d replies" % (feedname, outstanding))

    while outstanding:
        entid, entry, found = pending.get()
        outstanding -= 1
        try:
            if found:
                if "-q" not in sys.argv and "-v" in sys.argv:
                    outq.put("[%s] Found known article '%s'" % (feedname, entry.title))
                continue

            if "-q" not in sys.argv:
                outq.put("[%s] Found new article '%s'" % (feedname, entry.title))

            # MIME Structure:
            #
            #  multipart/related
            #  + multipart/alternative
            #  | + text/html
            #  + image/png
            #  + image/jpg
            #  + ...
            #
            # The multipart/alternative seems superfluous, but (at least)
            # Thunderbird doesn't render the email correctly without it.

            mp = email.mime.Multipart.MIMEMultipart("related")
            mp["From"] = entry.get("author", feedname)
            mp["Subject"] = entry.title
            mp["X-RSS2IMAP-ID"] = entid

            alt  = email.mime.Multipart.MIMEMultipart("alternative")
            mp.attach(alt)

            if feedproxy is not None:
                content = feedproxy.get_content(entry)
            elif "content" in entry:
                content = entry.content[0].value
            else:
                content = entry.summary

            soup = BeautifulSoup(content)

            for soupimg in soup.findAll("img"):
                if "doubleclick" in soupimg["src"] or "feedsportal.com" in soupimg["src"]:
                    # you know, if ads wouldn't contain a fucking HUGE gif that
                    # completely freezes my thunderbird for a couple of seconds while
                    # it tries to display the stupid ad, this wouldn't be necessary.
                    #soupimg.replace("(ad)")
                    continue
                try:
                    req = requests.get(soupimg["src"], headers={"User-Agent": USER_AGENT})
                except requests.ConnectionError:
                    continue
                else:
                    if req.status_code == 200:
                        cid = hashlib.md5(soupimg["src"]).hexdigest()
                        try:
                            img = email.mime.Image.MIMEImage(req.content)
                        except TypeError:
                            continue
                        else:
                            img.add_header("Content-ID", "<%s>" % cid)
                            img.add_header("X-IMG-SRC", soupimg["src"])
                            soupimg["src"] = "cid:%s" % cid
                            mp.attach(img)
                    else:
                        if "-q" not in sys.argv:
                            outq.put('[%s] Failed getting "%s": %d' % (feedname, soupimg["src"], req.status_code))

            body = content_template % {
                "feed":    feedname,
                "title":   entry.title,
                "link":    entry.get("link", ""),
                "content": unicode(soup)
            }

            alt.attach(email.mime.Text.MIMEText(body, "html", "utf-8"))

            uploadq.put((pendingupload, dirname, mp, entry.get("updated_parsed", time())))
            outstandingupload += 1
        except Exception:
            traceback.print_exc()

    if "-q" not in sys.argv:
        outq.put("[%s] Waiting for %d uploads" % (feedname, outstandingupload))

    while outstandingupload:
        pendingupload.get()
        outstandingupload -= 1

    if "-q" not in sys.argv:
        outq.put("[%s] Done!" % feedname)


# try to work around some serious GIL Multicore fuckup.
# see http://www.youtube.com/watch?v=ph374fJqFPE
# the 10k we use here is purely guessed and worked pretty well on a 4-core VM.
if hasattr(sys, "setcheckinterval"):
    sys.setcheckinterval(10000)

for dirname, feeds in conf["feeds"].items():
    for feedname, feedinfo in feeds.items():
        go_nodaemon(process_feed, dirname, feedname, feedinfo)
