#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from __future__ import division

import sys
import json
import math

from time import time
from StringIO import StringIO
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

from django.http       import HttpResponse

import pymongo


def latency_histogram(request):

    mng = pymongo.MongoClient(host=["127.0.0.1"])

    mng_histograms = mng.fluxmon.raw.aggregate([{
            "$project": {
                "count": { "$literal": 1 },
                "latency": {
                    "$trunc": {"$multiply": [ {"$log": [ {"$subtract": ["$stored_at", "$measured_at"]}, 2 ]}, 10 ]}
                },
                "measured_at": 1
            }
        }, {
            "$group": {
                "_id": {
                    "date":    {"$dateToString": {"format": "%Y-%m-%d:%H", "date": "$measured_at"}},
                    "latency": "$latency"
                },
                "count": { "$sum": "$count" }
            }
        }, {
            "$group": {
                "_id": "$_id.date",
                "data": {"$push": {
                    "count": "$count",
                    "latency": "$_id.latency"
                }}
            }
        }, {
            "$sort": {
                "_id": 1
            }
        }])

    histograms = []
    hmin = None
    hmax = None

    for mng_doc in mng_histograms["result"]:
        data = dict([ (int(slot["latency"]), int(slot["count"])) for slot in mng_doc["data"] ])
        tstamp = datetime.strptime(mng_doc["_id"], "%Y-%m-%d:%H")
        biggestbkt = max( data.values() )
        histograms.append( (tstamp, data, biggestbkt) )

    # prune outliers, detect dynamic range
    pruned = 0
    for (tstamp, data, biggestbkt) in histograms:
        for bktval, bktcount in data.items():
            if bktval == 214:
                print bktcount, biggestbkt, tstamp
            if bktcount / biggestbkt < 0.05:
                # outliers <5% which would be barely visible in the graph anyway
                del data[bktval]
                pruned += 1
            else:
                if hmin is None:
                    hmin = bktval
                else:
                    hmin = min(hmin, bktval)
                hmax = max(hmax, bktval)

    print >> sys.stderr, "pruned =", pruned
    print >> sys.stderr, "hmin =", hmin
    print >> sys.stderr, "hmax =", hmax

    rows = int(hmax - hmin)
    print >> sys.stderr, "rows =", rows
    cols = len(histograms)

    # How big do you want the squares to be?
    sqsz = 8

    # Draw the graph in a pixels array which we then copy to an image
    # we need to make the image one row larger in height to fit the top row
    width  = cols * sqsz
    height = rows * sqsz
    pixels = [(0xFF, 0xFF, 0xFF)] * (width * (height + sqsz))

    for col, (tstamp, histogram, biggestbkt) in enumerate(histograms):
        for bktval, bktcount in histogram.items():
            assert hmin <= bktval <= hmax

            pixelval  = 0xFF - int(bktcount / biggestbkt * 0xFF)

            offset_x = col * sqsz
            offset_y = height - int((bktval - hmin) / (hmax - hmin) * height)

            for y in range(0, sqsz):
                for x in range(0, sqsz):
                    try:
                        pixels[(offset_y + y) * width + (offset_x + x)] = (pixelval, ) * 3
                    except IndexError:
                        print cols * sqsz, offset_x + x, " -- ", rows * sqsz, offset_y + y

    # X position of the graph
    graph_x = 70

    # im will hold the output image
    im = Image.new("RGB", (width + graph_x + 20, height + 100), "white")

    # copy pixels to an Image and paste that into the output image
    graph = Image.new("RGB", (width, height + sqsz), "white")
    graph.putdata(pixels)
    im.paste(graph, (graph_x, 0))

    # draw a rect around the graph
    draw = ImageDraw.Draw(im)
    draw.rectangle((graph_x, 0, graph_x + width - 1, height - 1), outline=0x333333)

    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 10)
    except IOError:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)

    # Y axis ticks and annotations
    for hidx in range(hmin, hmax, 5):
        bottomrow = (hidx - hmin)
        offset_y = height - bottomrow * sqsz - 1
        draw.line((graph_x - 2, offset_y, graph_x + 2, offset_y), fill=0xAAAAAA)

        ping = 2 ** (hidx / 10.)
        label = "%.2f" % ping
        draw.text((graph_x - len(label) * 6 - 10, offset_y - 5), label, 0x333333, font=font)

    # X axis ticks
    # we want those markers to always be at 0/3/6/9/12/15/18/21h, so we need to correct
    # the offset of the first histogram
    offset_h = histograms[0][0].hour % 3

    for col, (tstamp, _, _) in list(enumerate(histograms))[::3]:
        offset_x = graph_x + (col - offset_h) * 8
        if offset_x < 0:
            continue
        draw.line((offset_x, height - 2, offset_x, height + 2), fill=0xAAAAAA)
        if (tstamp - timedelta(hours=offset_h)).hour == 0:
            draw.line((offset_x, 0, offset_x, height), fill=0x000077)

    # X axis annotations
    # Create a temp image for the bottom label that we then rotate by 90° and attach to the other one
    # since this stuff is rotated by 90° while we create it, all the coordinates are inversed...
    tmpim = Image.new("RGB", (80, width + 20), "white")
    tmpdraw = ImageDraw.Draw(tmpim)

    # draw date/time markers.
    # we want those markers to always be at 0/6/12/18h, so we need to correct
    # the offset of the first histogram
    offset_h = histograms[0][0].hour % 6

    for col, (tstamp, _, _) in list(enumerate(histograms))[::6]:
        offset_x = (col - offset_h) * 8
        if offset_x < 0:
            continue
        tmpdraw.text(( 6, offset_x + 0), (tstamp - timedelta(hours=offset_h)).strftime("%Y-%m-%d"), 0x333333, font=font)
        tmpdraw.text((18, offset_x + 8), (tstamp - timedelta(hours=offset_h)).strftime("%H:%M:%S"), 0x333333, font=font)

    im.paste( tmpim.rotate(90), (graph_x - 10, height + 1) )

    # This worked pretty well for Tobi Oetiker...
    tmpim = Image.new("RGB", (170, 11), "white")
    tmpdraw = ImageDraw.Draw(tmpim)
    tmpdraw.text((0, 0), "FluxMon by Michael Ziegler", 0x999999, font=font)
    im.paste( tmpim.rotate(270), (width + graph_x + 9, 0) )

    buf = StringIO()
    im.save( buf, "PNG" )

    return HttpResponse( buf.getvalue(), content_type="image/png" )

