#!/usr/bin/env python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import io
import re
import feedparser
import requests
import traceback
import os.path

from PIL import Image, ImageFont, ImageDraw

def main():
    feed = feedparser.parse("https://www.reddit.com/r/EarthPorn/.rss")

    for entry in feed.entries[3:]:
        try:
            link  = re.findall(r"""<a href="(?P<link>[^"]+)">\[link\]</a>""", entry.summary)[0]
            title = entry.title.split("[", 1)[0]

            if "-v" in sys.argv:
                print title
                print link

            if "imgur.com" in link:
                page = requests.get(link).content
                link  = re.findall(r"""<link\s+rel="image_src"\s+href="(?P<link>[^"]+)"/>""", page)[0]

            imgdata   = requests.get(link).content
            img_orig  = Image.open(io.BytesIO(imgdata))

            img_sized = img_orig.resize((1920, 1200), Image.ANTIALIAS)

            # Write the title onto the image
            font = ImageFont.truetype("DejaVuSans.ttf", 24)
            title_width = sum(font.getsize(c)[0] for c in title)
            title_xpos  = (1920 / 2.) - (title_width / 2.)

            ImageDraw.Draw(img_sized).text( (title_xpos, 120), title, (255,255,255), font=font)

            img_sized.save(os.path.expanduser("~/tmp/wallpaper-1920x1200.jpg"))
            break

        except:
            traceback.print_exc()
            continue

if __name__ == '__main__':
    main()
