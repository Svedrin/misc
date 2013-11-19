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
        entdate = datetime.fromtimestamp(mktime(feed.entries[0].published_parsed)).strftime("%m%d%y")
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

for dirname, feeds in conf["feeds"].items():
    if "-q" not in sys.argv:
        print "Processing %s feeds..." % dirname
    serv.select(dirname)
    for feedname, feedinfo in feeds.items():
        if isinstance(feedinfo, dict):
            feedurl   = feedinfo["url"]
            feedproxy = proxies[feedinfo["proxy"]]
        else:
            feedurl   = feedinfo
            feedproxy = None
        if "-q" not in sys.argv:
            print "-> %s" % feedname
        feed = feedparser.parse(feedurl)
        for entry in feed.entries:
            if "id" not in entry or "title" not in entry:
                print >> sys.stderr, "Skipping entry without title or ID."
                continue

            entid = hashlib.sha1(entry.id).hexdigest()
            typ, data = serv.search(None, '(HEADER X-RSS2IMAP-ID "%s")' % entid)

            if typ != "OK":
                print >> sys.stderr, "Querying the server failed"
                break

            if not data[0]:
                alt  = email.mime.Multipart.MIMEMultipart("alternative")

                mp = email.mime.Multipart.MIMEMultipart("related")
                mp["From"] = entry.get("author", feedname)
                mp["Subject"] = entry.title
                mp["X-RSS2IMAP-ID"] = entid
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
                    req = requests.get(soupimg["src"], headers={"User-Agent": USER_AGENT})
                    if req.status_code == 200:
                        cid = hashlib.md5(soupimg["src"]).hexdigest()
                        img = email.mime.Image.MIMEImage(req.content)
                        img.add_header("Content-ID", "<%s>" % cid)
                        img.add_header("X-IMG-SRC", soupimg["src"])
                        soupimg["src"] = "cid:%s" % cid
                        mp.attach(img)
                    else:
                        if "-q" not in sys.argv:
                            print '   Failed getting "%s": %d' % (soupimg["src"], req.status_code)

                body = content_template % {
                    "feed":    feedname,
                    "title":   entry.title,
                    "link":    entry.get("link", ""),
                    "content": unicode(soup)
                }

                alt.attach(email.mime.Text.MIMEText(body, "html", "utf-8"))

                if "-q" not in sys.argv:
                    print "   New article:", entry.title
                serv.append(dirname, "", imaplib.Time2Internaldate(time()), str(mp))

            else:
                if "-q" not in sys.argv:
                    print "   Article already known:", entry.title
