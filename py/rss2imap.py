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
from time import time


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
#            "Dilbert":        "http://feeds.feedburner.com/DilbertDailyStrip?format=xml",
#            "xkcd":           "http://xkcd.com/rss.xml",
#            "wumo":           "http://feeds.feedburner.com/wulffmorgenthaler",
#            "tpfd":           "http://www.toothpastefordinner.com/rss/rss.php",
#            "ahoipolloi":     "http://feed43.com/ahoipolloi.xml"
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


serv = imaplib.IMAP4(conf["imap"]["host"])
serv.login(conf["imap"]["user"], conf["imap"]["pass"])

for dirname, feeds in conf["feeds"].items():
    if "-q" not in sys.argv:
        print "Processing %s feeds..." % dirname
    serv.select(dirname)
    for feedname, feedurl in feeds.items():
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
                mp["From"] = "%s <rss2imap@svedr.in>" % entry.get("author", feedname)
                mp["To"]   = "ich@svedr.in"
                mp["Subject"] = entry.title
                mp["X-RSS2IMAP-ID"] = entid
                mp.attach(alt)

                if "content" in entry:
                    soup = BeautifulSoup(entry.content[0].value)
                else:
                    soup = BeautifulSoup(entry.summary)

                for soupimg in soup.findAll("img"):
                    req = requests.get(soupimg["src"])
                    if req.status_code == 200:
                        cid = hashlib.md5(soupimg["src"]).hexdigest()
                        soupimg["src"] = "cid:%s" % cid
                        img = email.mime.Image.MIMEImage(req.content)
                        img.add_header("Content-ID", "<%s>" % cid)
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
