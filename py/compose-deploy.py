#!/usr/bin/env python3
"""
compose-deploy – deployt eine docker-compose-Config in ein gemeinsames Netz mit
festen IPs in 10er-Blöcken.

Aufruf:
    DEPLOY_NETWORK=srv-net ./compose-deploy.py docker-compose.yml
    DEPLOY_NETWORK=srv-net ./compose-deploy.py -p myapp          # Config per Paste (stdin, Ende mit Strg-D)
    DEPLOY_NETWORK=srv-net ./compose-deploy.py -p myapp - < x.yml

Umgebungsvariablen:
    DEPLOY_NETWORK      (Pflicht) Name des Docker-Netzes (existiert bereits, z. B. macvlan/bridge /24)
    DEPLOY_HOSTNAME     Präfix für Container-Hostnamen (Default: $HOSTNAME, sonst Hostname des Systems)
    DEPLOY_BLOCK_SIZE   Blockgröße (Default: 10)
    DEPLOY_STATE_DIR    Ablage der generierten Compose-Files (Default: ~/.local/state/compose-deploy)

Was passiert:
  * networks/network_mode/ports aus dem Compose-File werden verworfen
  * jeder Service kommt ins DEPLOY_NETWORK mit fester IP:
      - existiert der Container schon (gleiches Compose-Projekt+Service oder gleicher
        container_name), wird seine IP wiederverwendet
      - neue Services bekommen freie IPs im Block des Projekts, sonst einen komplett
        freien Block (bei >10 Services zusammenhängende freie Blöcke)
      - Block 0 (.0–.9, Gateway etc.) wird nie vergeben
  * hostname = <DEPLOY_HOSTNAME>-<service>
  * "<IP:service>" in environment wird durch die IP des Services ersetzt
  * logging: max-size=10m, max-file=3 (json-file bzw. local)
  * Zusammenfassung + `docker compose config`, nach Bestätigung `up -d --force-recreate`
"""
import argparse
import collections
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt: apt install python3-yaml  (oder: pip install pyyaml)")

BLOCK = int(os.environ.get("DEPLOY_BLOCK_SIZE", "10"))
PLACEHOLDER = re.compile(r"<IP:([A-Za-z0-9_.-]+)>")
LOG_OPTS = {"max-size": "10m", "max-file": "3"}


def die(msg):
    print(f"FEHLER: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f"WARNUNG: {msg}", file=sys.stderr)


def docker(*args, check=True):
    r = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"docker {' '.join(args)}\n{r.stderr.strip()}")
    return r


# --------------------------------------------------------------------------- Docker-Zustand

def inspect_network(net):
    r = docker("network", "inspect", net, check=False)
    if r.returncode != 0:
        die(f"Netzwerk '{net}' nicht gefunden")
    info = json.loads(r.stdout)[0]
    cfgs = [c for c in (info.get("IPAM") or {}).get("Config") or []
            if ":" not in c.get("Subnet", "")]
    if not cfgs:
        die(f"Netzwerk '{net}' hat kein IPv4-Subnetz in der IPAM-Config")
    c = cfgs[0]
    subnet = ipaddress.ip_network(c["Subnet"])
    reserved = set()
    if c.get("Gateway"):
        reserved.add(ipaddress.ip_address(c["Gateway"]))
    for v in (c.get("AuxiliaryAddresses") or {}).values():
        reserved.add(ipaddress.ip_address(v))
    return info["Name"], subnet, reserved


def list_containers(net):
    """Alle Container (auch gestoppte) inkl. ihrer IP im Netz `net`."""
    ids = docker("ps", "-aq", "--no-trunc").stdout.split()
    out = []
    for i in range(0, len(ids), 100):
        for c in json.loads(docker("inspect", *ids[i:i + 100]).stdout):
            n = ((c.get("NetworkSettings") or {}).get("Networks") or {}).get(net)
            ip = None
            if n:
                ip = (n.get("IPAMConfig") or {}).get("IPv4Address") or n.get("IPAddress") or None
            labels = (c.get("Config") or {}).get("Labels") or {}
            out.append({
                "id": c["Id"][:12],
                "name": c["Name"].lstrip("/"),
                "ip": ipaddress.ip_address(ip) if ip else None,
                "project": labels.get("com.docker.compose.project"),
                "service": labels.get("com.docker.compose.service"),
                "state": (c.get("State") or {}).get("Status", "?"),
            })
    return out


# --------------------------------------------------------------------------- Eingabe

def load_compose(src):
    if src in (None, "-"):
        if sys.stdin.isatty():
            print("Compose-Config einfügen, abschließen mit Strg-D:", file=sys.stderr)
        text, base = sys.stdin.read(), None
    else:
        with open(src) as f:
            text = f.read()
        base = os.path.dirname(os.path.abspath(src))
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("services"), dict) or not data["services"]:
        die("Keine 'services' in der Compose-Config gefunden")
    return data, base


def normalize_project(name):
    name = re.sub(r"[^a-z0-9_-]", "", name.lower())
    name = re.sub(r"^[^a-z0-9]+", "", name)
    if not name:
        die("Ungültiger Projektname")
    return name


# --------------------------------------------------------------------------- IP-Vergabe

def allocate(services, existing_ip, subnet, reserved, used):
    off = int(subnet.network_address)

    def block_of(ip):
        return (int(ip) - off) // BLOCK

    by_block = collections.OrderedDict()
    for ip in subnet.hosts():
        if ip in reserved or block_of(ip) < 1:
            continue
        by_block.setdefault(block_of(ip), []).append(ip)

    assigned = dict(existing_ip)
    taken = set(used) | set(assigned.values())
    todo = [s for s in services if s not in assigned]
    if not todo:
        return assigned

    # 1) freie IPs in den Blöcken, die das Projekt schon belegt (meistgenutzter zuerst)
    pref = [b for b, _ in collections.Counter(block_of(ip) for ip in assigned.values()).most_common()]
    pool = [ip for b in pref for ip in by_block.get(b, []) if ip not in taken]

    # 2) sonst zusammenhängende, komplett freie Blöcke mit genug Kapazität
    rest = len(todo) - len(pool)
    if rest > 0:
        fully_free = [b for b, ips in by_block.items() if not any(ip in taken for ip in ips)]
        chosen = None
        for i in range(len(fully_free)):
            run, cap = [], 0
            for b in fully_free[i:]:
                if run and b != run[-1] + 1:
                    break
                run.append(b)
                cap += len(by_block[b])
                if cap >= rest:
                    chosen = run
                    break
            if chosen:
                break
        if chosen:
            if pref:
                warn(f"Projekt-Block {pref} reicht nicht – weiche zusätzlich auf Block {chosen} aus")
            pool += [ip for b in chosen for ip in by_block[b]]
        else:
            warn("Kein ausreichend großer freier Block – vergebe beliebige freie IPs")
            pool += [ip for ips in by_block.values() for ip in ips if ip not in taken and ip not in pool]

    if len(pool) < len(todo):
        die(f"Nicht genug freie IPs im Netz {subnet}")
    for svc, ip in zip(todo, pool):
        assigned[svc] = ip
    return assigned


# --------------------------------------------------------------------------- Transformation

def transform(data, net, ips, host_prefix):
    def sub(value, svc):
        def repl(m):
            target = m.group(1)
            if target not in ips:
                die(f"Service '{svc}': <IP:{target}> – Service '{target}' gibt es nicht")
            return str(ips[target])
        return PLACEHOLDER.sub(repl, value) if isinstance(value, str) else value

    data.pop("version", None)
    data["networks"] = {net: {"external": True, "name": net}}

    for svc, cfg in data["services"].items():
        cfg = cfg if isinstance(cfg, dict) else {}
        data["services"][svc] = cfg

        replicas = (cfg.get("deploy") or {}).get("replicas")
        if (replicas not in (None, 1)) or (cfg.get("scale") not in (None, 1)):
            die(f"Service '{svc}': replicas/scale > 1 geht nicht mit fester IP")

        for key in ("ports", "networks", "network_mode"):
            cfg.pop(key, None)

        cfg["hostname"] = f"{host_prefix}-{svc}"
        cfg["networks"] = {net: {"ipv4_address": str(ips[svc])}}

        env = cfg.get("environment")
        if isinstance(env, dict):
            cfg["environment"] = {k: sub(v, svc) for k, v in env.items()}
        elif isinstance(env, list):
            cfg["environment"] = [sub(e, svc) for e in env]

        log = cfg.get("logging") or {}
        driver = log.get("driver", "json-file")
        if driver in ("json-file", "local"):
            opts = {k: str(v) for k, v in (log.get("options") or {}).items()}
            opts.update(LOG_OPTS)
            cfg["logging"] = {"driver": driver, "options": opts}
        else:
            warn(f"Service '{svc}': Logging-Driver '{driver}' kennt max-size/max-file nicht – unverändert")

        left = PLACEHOLDER.findall(yaml.safe_dump(cfg))
        if left:
            warn(f"Service '{svc}': <IP:...> außerhalb von environment wird nicht ersetzt: {sorted(set(left))}")
    return data


# --------------------------------------------------------------------------- Main

def ask(prompt):
    try:
        with open("/dev/tty") as tty:  # stdin ist evtl. schon durch den Paste verbraucht
            print(prompt, end="", flush=True, file=sys.stderr)
            return tty.readline().strip().lower()
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser(description="Compose-Stack mit festen IPs ins DEPLOY_NETWORK deployen")
    ap.add_argument("file", nargs="?", help="Compose-File (leer oder '-' = stdin/Paste)")
    ap.add_argument("-p", "--project", help="Compose-Projektname (Default: 'name:' im File, sonst Ordnername)")
    ap.add_argument("--project-dir", help="Basisverzeichnis für relative Pfade/.env (Default: Ordner des Files bzw. cwd)")
    ap.add_argument("-y", "--yes", action="store_true", help="ohne Rückfrage deployen")
    ap.add_argument("-n", "--dry-run", action="store_true", help="nur anzeigen, nicht deployen")
    ap.add_argument("--pull", action="store_true", help="Images vorher neu ziehen (--pull always)")
    args = ap.parse_args()

    net_name = os.environ.get("DEPLOY_NETWORK") or die("DEPLOY_NETWORK ist nicht gesetzt")
    host_prefix = (os.environ.get("DEPLOY_HOSTNAME") or os.environ.get("HOSTNAME")
                   or socket.gethostname()).split(".")[0]

    data, base = load_compose(args.file)
    project_dir = os.path.abspath(args.project_dir or base or os.getcwd())
    project = args.project or data.get("name") or os.environ.get("COMPOSE_PROJECT_NAME") \
        or (os.path.basename(base) if base else None)
    if not project:
        die("Bei Paste/stdin bitte Projektnamen mit -p angeben (oder 'name:' in die Config)")
    project = normalize_project(project)
    data["name"] = project

    net, subnet, reserved = inspect_network(net_name)
    containers = list_containers(net)
    services = list(data["services"])

    # bestehende Container je Service finden
    existing_ip, status, to_remove = {}, {}, []
    for svc in services:
        cname = (data["services"][svc] or {}).get("container_name")
        matches = [c for c in containers if c["project"] == project and c["service"] == svc]
        if cname:
            for c in containers:
                if c["name"] == cname and c not in matches:
                    matches.append(c)
                    to_remove.append(c)  # gleicher Name, aber nicht von diesem Compose-Projekt
        if matches:
            with_ip = [c for c in matches if c["ip"] and c["ip"] in subnet]
            if with_ip:
                existing_ip[svc] = with_ip[0]["ip"]
            m = matches[0]
            status[svc] = f"ersetzt ({m['name']}, {m['state']})"
        else:
            status[svc] = "neu"

    used = {c["ip"] for c in containers if c["ip"]} | reserved
    ips = allocate(services, existing_ip, subnet, reserved, used)
    data = transform(data, net, ips, host_prefix)

    state_dir = os.environ.get("DEPLOY_STATE_DIR") or os.path.expanduser("~/.local/state/compose-deploy")
    os.makedirs(os.path.join(state_dir, project), exist_ok=True)
    out_file = os.path.join(state_dir, project, "docker-compose.yml")
    with open(out_file, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    compose = ["docker", "compose", "-f", out_file, "--project-directory", project_dir, "-p", project]

    # ---- Zusammenfassung
    print(f"\n=== Projekt '{project}' → Netz '{net}' ({subnet}) ===\n")
    w = max(len(s) for s in services + ["SERVICE"]) + 2
    hw = max([len(data["services"][s]["hostname"]) for s in services] + [len("HOSTNAME")]) + 2
    print(f"{'SERVICE':<{w}}{'IP':<17}{'HOSTNAME':<{hw}}STATUS")
    for svc in services:
        print(f"{svc:<{w}}{str(ips[svc]):<17}{data['services'][svc]['hostname']:<{hw}}{status[svc]}")
    if to_remove:
        print("\nDiese Container (gleicher Name, nicht von Compose verwaltet) werden vorher entfernt:")
        for c in to_remove:
            print(f"  - {c['name']} ({c['id']}, {c['state']})")

    print(f"\n--- docker compose config ({out_file}) ---")
    r = subprocess.run(compose + ["config"], capture_output=True, text=True)
    if r.returncode != 0:
        print(yaml.safe_dump(data, sort_keys=False))
        die(f"docker compose config schlägt fehl:\n{r.stderr.strip()}")
    print(r.stdout)
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)

    if args.dry_run:
        print("Dry-Run – nichts deployed.")
        return
    if not args.yes and ask("So deployen? [j/N] ") not in ("j", "ja", "y", "yes"):
        print("Abgebrochen.")
        return

    # ---- Deploy
    for c in to_remove:
        print(f"Entferne {c['name']} …")
        docker("rm", "-f", c["id"])
    up = compose + ["up", "-d", "--force-recreate"]
    if args.pull:
        up += ["--pull", "always"]
    sys.exit(subprocess.run(up).returncode)


if __name__ == "__main__":
    main()
