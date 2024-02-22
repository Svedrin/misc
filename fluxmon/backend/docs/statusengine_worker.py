import gearman
import json
import re
import traceback

from uuid import uuid4

gm_worker = gearman.GearmanWorker(['localhost:4730'])

def task(wrk, job):
    try:
        jobdata = json.loads(job.data)

        timestamp = jobdata["timestamp"]

        # Fix for braindead check plugins that format the perfdata with their locale.
        # this is ugly as hell, but PNP does it the same way.
        perfdata = jobdata["servicecheck"]["perf_data"].replace(",", ".")
        data = {}
        for definition in perfdata.split(" "):
            if '=' not in definition:
                continue
            key, values = definition.split("=", 1)
            data[key] = dict(zip(
                ["curr", "warn", "crit", "min", "max"],
                [v for v in values.split(";") if v]))
            m = re.match( '^(?P<value>\d*(?:\.\d+)?)(?P<unit>[^\d]*)$', data[key]["curr"] )
            if m:
                data[key]["curr"] = float(m.group("value"))
                data[key]["unit"] = m.group("unit")
            for perfkey in data[key]:
                if perfkey != "unit":
                    data[key][perfkey] = float(data[key][perfkey])

        checkresult = {
            "timestamp": timestamp,
            "uuid": str(uuid4()),
            "check": jobdata["servicecheck"]["service_description"],
            "data": dict([ (key, data[key]["curr"]) for key in data ]),
            "max":  None,
            "errmessage": None
        }

        print json.dumps(checkresult, indent=4)
    except Exception:
        traceback.print_exc()
    return ""

gm_worker.set_client_id("tehpython")
gm_worker.register_task('statusngin_servicechecks', task)

gm_worker.work()
