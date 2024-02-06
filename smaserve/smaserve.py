from flask import Flask, Response
from uuid import uuid4

import subprocess
import re

app  = Flask(__name__)

@app.route("/")
def hai():
    return Response("""<a href="/metrics">metrics</a>""")

@app.route("/metrics")
def metrics():
    proc = subprocess.Popen(
               ["/usr/bin/timeout", "25s",
                "/usr/local/share/smaspot/SBFspot", "-v2", "-nocsv"],
               stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
    out, err = proc.communicate()

    ret = {
        "uac1": 0, "uac2": 0, "uac3": 0, "udc1": 0, "udc2": 0,
        "iac1": 0, "iac2": 0, "iac3": 0, "idc1": 0, "idc2": 0,
        "pac1": 0, "pac2": 0, "pac3": 0, "pdc1": 0, "pdc2": 0,
        "pac": 0
    }
    ipaddr = "unknown"

    wantlines = ("EToday", "ETotal", "Feed-In Time", "String", "Phase", "Total Pac")
    for line in out.split("\n"):
        line = line.strip()

        if line.startswith("Inverter IP address:"):
            ipaddr = line.split(":")[1].strip()
            continue

        for wantline in wantlines:
            if line.startswith(wantline):
                break
        else:
            continue

        values = re.findall(r'(?P<field>\w+)\s*:\s+(?P<value>\d+\.\d+)(?P<unit>\w*)', line)

        phase = re.findall(r'(String|Phase) (?P<phase>\d+)', line)
        if phase:
            phase = phase[0][1]
        else:
            phase = ''

        for field, valstr, unit in values:
            if unit.startswith("k"):
                mult = 1000
            else:
                mult = 1

            ret[field.lower() + phase] = float(valstr) * mult

    if not ret:
        return Response("\n", mimetype="text/plain")

    counters = ["etotal", "etoday", "time"]

    return Response(''.join([
        ('# TYPE inverter_%s %s\n'         % (key, "counter" if key in counters else "gauge")) +
        ('inverter_%s{inverter="%s"} %f\n' % (key, ipaddr, ret[key]))
        for key in ret
    ]), mimetype="text/plain")

app.secret_key = str(uuid4())
app.debug = True

app.run(host="0.0.0.0", port=9500)
