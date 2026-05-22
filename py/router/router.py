# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import ipaddress
import json
import subprocess
from datetime import datetime

from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = "some super random stuff here"


# Protocol → (abbreviation, Bootstrap colour name)
PROTOCOL_STYLES = {
    "connected": ("C",  "success"),
    "kernel":    ("K",  "secondary"),
    "static":    ("S",  "warning"),
    "ospf":      ("O",  "primary"),
    "ospf6":     ("O6", "primary"),
    "bgp":       ("B",  "info"),
    "isis":      ("I",  "secondary"),
    "rip":       ("R",  "danger"),
    "eigrp":     ("E",  "warning"),
    "babel":     ("A",  "secondary"),
    "sharp":     ("D",  "secondary"),
    "pbr":       ("F",  "secondary"),
    "nhrp":      ("N",  "secondary"),
}

OSPF_STATE_COLOUR = {
    "Full":     "success",
    "2-Way":    "info",
    "Exchange": "warning",
    "ExStart":  "warning",
    "Loading":  "warning",
    "Init":     "danger",
    "Down":     "danger",
    "Attempt":  "danger",
}


def vtysh(command):
    """Run a single vtysh command.  Returns (stdout_str, error_str_or_None)."""
    try:
        proc = subprocess.run(
            ["vtysh", "-c", command],
            capture_output=True,
            timeout=10,
        )
        out = proc.stdout.decode("utf-8", errors="replace").strip()
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        return out, (err if proc.returncode != 0 else None)
    except FileNotFoundError:
        return "", "vtysh not found – is FRR installed?"
    except subprocess.TimeoutExpired:
        return "", "Command timed out after 10 s"
    except Exception as exc:
        return "", str(exc)


def fmt_nexthop(nh):
    ip    = nh.get("ip", "")
    iface = nh.get("interfaceName", "")
    if ip and iface:
        return "{} via {}".format(ip, iface)
    if ip:
        return ip
    if iface:
        return iface
    return "–"


def _build_neighbor(router_id, nbr, vrf="default"):
    """Turn a single neighbor JSON object into our display dict."""
    state_full = nbr.get("state", "")
    parts  = state_full.split("/", 1)
    state  = parts[0]
    role   = parts[1] if len(parts) > 1 else ""
    iface_raw = nbr.get("ifaceName", "")
    iface = iface_raw.split(":")[0] if ":" in iface_raw else iface_raw
    return {
        "vrf":       "" if vrf == "default" else vrf,
        "router_id": router_id,
        "priority":  nbr.get("priority", ""),
        "state":     state,
        "role":      role,
        "colour":    OSPF_STATE_COLOUR.get(state, "secondary"),
        "address":   nbr.get("address", ""),
        "interface": iface,
        "duration":  nbr.get("stateDuration", ""),
    }


def _walk_neighbors_dict(nbrs_dict, vrf="default"):
    """Yield neighbor rows from a {router_id: [nbr, …]} dict."""
    for router_id, entry in nbrs_dict.items():
        nbr_list = entry if isinstance(entry, list) else [entry]
        for nbr in nbr_list:
            if isinstance(nbr, dict):
                yield _build_neighbor(router_id, nbr, vrf)


def _walk_neighbors_list(nbrs_list, vrf="default"):
    """Yield neighbor rows from a [{routerId/neighborId: …}] list."""
    for nbr in nbrs_list:
        if not isinstance(nbr, dict):
            continue
        rid = (nbr.get("routerId") or nbr.get("neighborId")
               or nbr.get("neighborAddress") or "?")
        yield _build_neighbor(rid, nbr, vrf)


def parse_neighbors(raw):
    """Return (list_of_dicts, error_or_None).

    FRR has emitted a few different shapes over the years; handle them all:
      A) {"default": {"neighbors": {"RID": [{…}]}}}   ← VRF-keyed (FRR 7+)
      B) {"neighbors": {"RID": [{…}]}}                ← flat, dict-keyed
      C) {"neighbors": [{routerId:"RID", …}]}          ← flat, list-keyed
      D) [{"routerId": "RID", …}]                      ← bare array
    """
    if not raw:
        return [], None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [], "JSON decode error: {}".format(exc)

    neighbors = []

    # Format D – bare JSON array
    if isinstance(data, list):
        neighbors.extend(_walk_neighbors_list(data))
        return neighbors, None

    if not isinstance(data, dict):
        return [], "Unexpected JSON type: {}".format(type(data).__name__)

    # Format B / C – "neighbors" key at the top level (no VRF wrapper)
    if "neighbors" in data:
        nbrs = data["neighbors"]
        if isinstance(nbrs, dict):
            neighbors.extend(_walk_neighbors_dict(nbrs))
        elif isinstance(nbrs, list):
            neighbors.extend(_walk_neighbors_list(nbrs))
        return neighbors, None

    # Format A – VRF-keyed outer dict
    for vrf_name, vrf_data in data.items():
        if not isinstance(vrf_data, dict):
            continue
        nbrs = vrf_data.get("neighbors", {})
        if isinstance(nbrs, dict):
            neighbors.extend(_walk_neighbors_dict(nbrs, vrf=vrf_name))
        elif isinstance(nbrs, list):
            neighbors.extend(_walk_neighbors_list(nbrs, vrf=vrf_name))

    return neighbors, None


def parse_routes(raw):
    """Return (list_of_dicts, error_or_None)."""
    if not raw:
        return [], None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [], "JSON decode error: {}".format(exc)

    routes = []
    for prefix, route_list in data.items():
        for route in route_list:
            nexthops = route.get("nexthops", [])
            nh_strs  = [fmt_nexthop(nh) for nh in nexthops] if nexthops else ["directly connected"]

            proto = route.get("protocol", "?")
            abbr, colour = PROTOCOL_STYLES.get(proto, (proto[:3].upper(), "secondary"))

            routes.append({
                "prefix":   prefix,
                "protocol": proto,
                "abbr":     abbr,
                "colour":   colour,
                "selected": route.get("selected", False),
                "fib":      any(nh.get("fib") for nh in nexthops),
                "distance": route.get("distance", ""),
                "metric":   route.get("metric", ""),
                "nexthops": nh_strs,
                "uptime":   route.get("uptime", ""),
            })

    def sort_key(r):
        try:
            return (0, ipaddress.ip_network(r["prefix"], strict=False))
        except ValueError:
            return (1, r["prefix"])

    routes.sort(key=sort_key)
    return routes, None


@app.route("/")
def index():
    now = datetime.now().strftime("%H:%M:%S")

    # ── OSPF neighbors ────────────────────────────────────────────
    raw_nbr, vtysh_err = vtysh("show ip ospf neighbor json")
    if vtysh_err:
        neighbors, nbr_err = [], vtysh_err
    else:
        neighbors, nbr_err = parse_neighbors(raw_nbr)

    nbr_full    = sum(1 for n in neighbors if n["state"] == "Full")
    nbr_nonfull = len(neighbors) - nbr_full
    has_vrf     = any(n["vrf"] for n in neighbors)

    # ── Routes ────────────────────────────────────────────────────
    raw_rt, vtysh_err2 = vtysh("show ip route json")
    if vtysh_err2:
        routes, rt_err = [], vtysh_err2
    else:
        routes, rt_err = parse_routes(raw_rt)

    # Protocol summary for the card header badges
    proto_counts = {}
    for r in routes:
        key = (r["abbr"], r["colour"])
        proto_counts[key] = proto_counts.get(key, 0) + 1
    proto_summary = [
        {"abbr": k[0], "colour": k[1], "count": v}
        for k, v in sorted(proto_counts.items(), key=lambda x: -x[1])
    ]

    return render_template(
        "index.html",
        now=now,
        neighbors=neighbors,
        nbr_err=nbr_err,
        nbr_full=nbr_full,
        nbr_nonfull=nbr_nonfull,
        has_vrf=has_vrf,
        routes=routes,
        rt_err=rt_err,
        proto_summary=proto_summary,
        total_routes=len(routes),
    )


@app.route("/debug")
def debug():
    """Raw vtysh output — handy for diagnosing JSON shape issues."""
    from flask import Response
    cmds = [
        "show ip ospf neighbor json",
        "show ip ospf neighbor",
        "show ip route json",
    ]
    lines = []
    for cmd in cmds:
        out, err = vtysh(cmd)
        lines.append("=" * 60)
        lines.append("$ vtysh -c '{}'".format(cmd))
        lines.append("=" * 60)
        if err:
            lines.append("STDERR: " + err)
        lines.append(out or "(no output)")
        lines.append("")
    return Response("\n".join(lines), mimetype="text/plain")


application = app.wsgi_app


if __name__ == "__main__":
    app.debug = True
    app.run(host="::")
