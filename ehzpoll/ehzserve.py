from flask import Flask, Response
from uuid import uuid4

import subprocess
import json

app  = Flask(__name__)

@app.route("/")
def hai():
    return Response("""<a href="/metrics">metrics</a>""")

@app.route("/metrics")
def metrics():
    proc = subprocess.Popen(["/bin/ehzpoll", "/dev/ttyUSB0"], stdout=subprocess.PIPE)
    out, err = proc.communicate()
    data = dict(json.loads(out), port="/dev/ttyUSB0")
    # { "rx": 11694941.900000, "tx": 22825926.200000, "rxwatts": 3264.600000, "txwatts": 0.000000 }
    return Response('\n'.join([
        '# HELP powergrid_rx Total energy consumed',
        '# TYPE powergrid_rx counter',
        'powergrid_rx{port="%(port)s"} %(rx).3f',

        '# HELP powergrid_tx Total energy fed into the grid',
        '# TYPE powergrid_tx counter',
        'powergrid_tx{port="%(port)s"} %(tx).3f',

        '# HELP powergrid_rxwatts Current power consumption',
        '# TYPE powergrid_rxwatts gauge',
        'powergrid_rxwatts{port="%(port)s"} %(rxwatts).3f',

        '# HELP powergrid_txwatts Current power feed-in',
        '# TYPE powergrid_txwatts gauge',
        'powergrid_txwatts{port="%(port)s"} %(txwatts).3f',

        '']) % data, mimetype="text/plain")

app.secret_key = str(uuid4())
app.debug = True

app.run(host="::", port=9100)
