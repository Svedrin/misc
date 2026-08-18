#!/usr/bin/env python3
"""
docker-run-reconstruct.py

Liest die internen Docker-Container-Configs (config.v2.json + hostconfig.json)
aus einem Docker-Datenverzeichnis (Standard: /var/lib/docker, per --root
änderbar, z.B. für ein gemountetes Backup) und generiert daraus passende
"docker run"-Kommandos, mit denen sich die Container neu starten lassen.

WICHTIG:
- Das Ergebnis ist eine Rekonstruktion, keine 1:1-Garantie. Manche Dinge
  (z.B. Secrets, Build-Kontext, manche Netzwerk-Spezialfälle, Swarm-Configs)
  lassen sich aus den Configs nicht vollständig ableiten.
- Es werden nur die Dateien gelesen, es wird nichts gestartet oder verändert.

Nutzung:
    ./docker-run-reconstruct.py
    ./docker-run-reconstruct.py --root /pfad/zum/backup/var/lib/docker
    ./docker-run-reconstruct.py --root /backup/docker --id 3f2a1b...
    ./docker-run-reconstruct.py --root /backup/docker --only-running
    ./docker-run-reconstruct.py --root /backup/docker --out commands.sh
"""

import argparse
import json
import os
import shlex
import sys


def q(value):
    """Shell-quote einen Wert."""
    return shlex.quote(str(value))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_containers(containers_dir, wanted_id=None):
    result = []
    if not os.path.isdir(containers_dir):
        print(f"FEHLER: Verzeichnis nicht gefunden: {containers_dir}", file=sys.stderr)
        return result

    for entry in sorted(os.listdir(containers_dir)):
        if wanted_id and not entry.startswith(wanted_id):
            continue
        cdir = os.path.join(containers_dir, entry)
        cfg_path = os.path.join(cdir, "config.v2.json")
        hcfg_path = os.path.join(cdir, "hostconfig.json")
        if os.path.isfile(cfg_path) and os.path.isfile(hcfg_path):
            result.append((entry, cfg_path, hcfg_path))
    return result


def parse_port_bindings(exposed_ports, port_bindings):
    """
    exposed_ports: dict wie {"80/tcp": {}}
    port_bindings: dict wie {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}
    -> Liste von -p Argumenten als Strings
    """
    ports = []
    port_bindings = port_bindings or {}

    for container_port, bindings in port_bindings.items():
        if not bindings:
            continue
        for b in bindings:
            host_ip = b.get("HostIp") or ""
            host_port = b.get("HostPort") or ""
            proto = ""
            cport = container_port
            if "/" in container_port:
                cport, proto = container_port.split("/", 1)
            spec = cport
            if host_port:
                if host_ip:
                    spec = f"{host_ip}:{host_port}:{cport}"
                else:
                    spec = f"{host_port}:{cport}"
            if proto and proto != "tcp":
                spec = f"{spec}/{proto}"
            ports.append(spec)

    # Ports, die exponiert aber nicht gebunden sind (nur --expose relevant,
    # meist reicht das implizit über EXPOSE im Image, daher hier ignoriert)
    return ports


def parse_mounts(config, hostconfig):
    """
    Bevorzugt hostconfig["Mounts"] (neueres Docker), fällt sonst auf
    config["MountPoints"] bzw. hostconfig["Binds"] zurück.
    """
    mounts = []

    hc_mounts = hostconfig.get("Mounts") or []
    if hc_mounts:
        for m in hc_mounts:
            mtype = m.get("Type", "volume")
            source = m.get("Source", "")
            target = m.get("Target", "")
            ro = m.get("ReadOnly", False)
            if mtype == "bind":
                spec = f"type=bind,source={source},target={target}"
            elif mtype == "tmpfs":
                spec = f"type=tmpfs,target={target}"
            else:
                spec = f"type=volume,source={source},target={target}" if source else f"type=volume,target={target}"
            if ro:
                spec += ",readonly"
            mounts.append(("--mount", spec))
        return mounts

    # Fallback: Binds aus hostconfig (klassische -v Syntax)
    binds = hostconfig.get("Binds") or []
    for b in binds:
        mounts.append(("-v", b))

    # Fallback: benannte Volumes aus config["MountPoints"], die nicht
    # schon über Binds abgedeckt sind
    mount_points = config.get("MountPoints") or {}
    bind_targets = {b.split(":")[1] for b in binds if ":" in b}
    for dest, mp in mount_points.items():
        if dest in bind_targets:
            continue
        name = mp.get("Name")
        if name:
            spec = f"{name}:{dest}"
            if mp.get("RW") is False:
                spec += ":ro"
            mounts.append(("-v", spec))

    return mounts


def build_run_command(container_id, config, hostconfig):
    parts = ["docker", "run", "-d"]

    name = (config.get("Name") or "").lstrip("/")
    if name:
        parts += ["--name", q(name)]

    cfg = config.get("Config", {}) or {}

    # Hostname nur setzen, wenn er nicht der Standard (= gekürzte Container-ID) ist
    hostname = cfg.get("Hostname")
    if hostname and not container_id.startswith(hostname):
        parts += ["--hostname", q(hostname)]

    # Restart-Policy
    restart = hostconfig.get("RestartPolicy", {}) or {}
    rp_name = restart.get("Name")
    if rp_name and rp_name != "no":
        if rp_name == "on-failure" and restart.get("MaximumRetryCount"):
            parts += ["--restart", q(f"on-failure:{restart['MaximumRetryCount']}")]
        else:
            parts += ["--restart", q(rp_name)]

    if hostconfig.get("AutoRemove"):
        parts.append("--rm")

    if hostconfig.get("Privileged"):
        parts.append("--privileged")

    if cfg.get("Tty"):
        parts.append("-t")
    if cfg.get("OpenStdin") or cfg.get("StdinOnce"):
        parts.append("-i")

    if cfg.get("User"):
        parts += ["--user", q(cfg["User"])]

    if cfg.get("WorkingDir"):
        parts += ["--workdir", q(cfg["WorkingDir"])]

    # Netzwerk
    network_mode = hostconfig.get("NetworkMode")
    if network_mode and network_mode not in ("default", "bridge"):
        parts += ["--network", q(network_mode)]

    # IP-Adresse, sofern statisch konfiguriert
    net_settings = config.get("NetworkSettings", {}) or {}
    networks = net_settings.get("Networks", {}) or {}
    for net_name, net_data in networks.items():
        ip = net_data.get("IPAMConfig", {}).get("IPv4Address") if net_data.get("IPAMConfig") else None
        if ip:
            parts += ["--ip", q(ip)]
        aliases = net_data.get("Aliases") or []
        # nur "echte" Aliases (nicht die zufällige Container-ID) übernehmen
        real_aliases = [a for a in aliases if not container_id.startswith(a)]
        for alias in real_aliases:
            parts += ["--network-alias", q(alias)]
        break  # nur das erste konfigurierte Netzwerk berücksichtigen

    # Ports
    exposed_ports = cfg.get("ExposedPorts", {}) or {}
    port_bindings = hostconfig.get("PortBindings", {}) or {}
    for spec in parse_port_bindings(exposed_ports, port_bindings):
        parts += ["-p", q(spec)]

    if hostconfig.get("PublishAllPorts"):
        parts.append("-P")

    # Volumes / Mounts
    for flag, spec in parse_mounts(config, hostconfig):
        parts += [flag, q(spec)]

    # Environment-Variablen
    for env in cfg.get("Env") or []:
        parts += ["-e", q(env)]

    # Labels
    labels = cfg.get("Labels") or {}
    for k, v in labels.items():
        # Auto-generierte Compose/Swarm-Labels sind meist Rauschen,
        # werden hier trotzdem übernommen, damit nichts verloren geht
        parts += ["--label", q(f"{k}={v}")]

    # DNS
    for dns in hostconfig.get("Dns") or []:
        parts += ["--dns", q(dns)]
    for search in hostconfig.get("DnsSearch") or []:
        parts += ["--dns-search", q(search)]

    # Extra hosts
    for host in hostconfig.get("ExtraHosts") or []:
        parts += ["--add-host", q(host)]

    # Capabilities
    for cap in hostconfig.get("CapAdd") or []:
        parts += ["--cap-add", q(cap)]
    for cap in hostconfig.get("CapDrop") or []:
        parts += ["--cap-drop", q(cap)]

    # Devices
    for dev in hostconfig.get("Devices") or []:
        path_on_host = dev.get("PathOnHost")
        path_in_container = dev.get("PathInContainer")
        perms = dev.get("CgroupPermissions", "")
        if path_on_host and path_in_container:
            spec = f"{path_on_host}:{path_in_container}"
            if perms and perms != "rwm":
                spec += f":{perms}"
            parts += ["--device", q(spec)]

    # Links (klassisch, meist nur bei alten Containern relevant)
    for link in hostconfig.get("Links") or []:
        parts += ["--link", q(link)]

    # Ressourcenlimits
    if hostconfig.get("Memory"):
        parts += ["--memory", q(hostconfig["Memory"])]
    if hostconfig.get("MemorySwap") and hostconfig["MemorySwap"] not in (0, -1):
        parts += ["--memory-swap", q(hostconfig["MemorySwap"])]
    if hostconfig.get("NanoCpus"):
        cpus = hostconfig["NanoCpus"] / 1e9
        parts += ["--cpus", q(cpus)]
    elif hostconfig.get("CpuShares"):
        parts += ["--cpu-shares", q(hostconfig["CpuShares"])]
    if hostconfig.get("CpusetCpus"):
        parts += ["--cpuset-cpus", q(hostconfig["CpusetCpus"])]

    # Ulimits
    for ulimit in hostconfig.get("Ulimits") or []:
        name_ = ulimit.get("Name")
        soft = ulimit.get("Soft")
        hard = ulimit.get("Hard")
        if name_:
            parts += ["--ulimit", q(f"{name_}={soft}:{hard}")]

    # Security-Opt
    for sec in hostconfig.get("SecurityOpt") or []:
        parts += ["--security-opt", q(sec)]

    # Entrypoint überschreiben, falls vom Image abweichend gesetzt
    entrypoint = cfg.get("Entrypoint")
    if entrypoint:
        parts += ["--entrypoint", q(entrypoint[0])]
        # Rest von Entrypoint kommt unten mit ins Cmd, da docker run
        # nur ein einzelnes --entrypoint-Executable erlaubt
        extra_entrypoint = entrypoint[1:]
    else:
        extra_entrypoint = []

    image = cfg.get("Image", "")
    parts.append(q(image))

    cmd = cfg.get("Cmd") or []
    full_cmd = extra_entrypoint + cmd
    for c in full_cmd:
        parts.append(q(c))

    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Generiert docker-run-Kommandos aus Docker-Container-Configs."
    )
    parser.add_argument(
        "--root",
        default="/var/lib/docker",
        help="Docker-Datenverzeichnis (Standard: /var/lib/docker). "
             "Für ein Backup z.B. /pfad/zu/backup/var/lib/docker angeben.",
    )
    parser.add_argument(
        "--id",
        default=None,
        help="Nur den Container verarbeiten, dessen ID mit diesem Wert beginnt.",
    )
    parser.add_argument(
        "--only-running",
        action="store_true",
        help="Nur Container ausgeben, die laut Config zuletzt liefen (Running=true).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Ausgabe zusätzlich in diese Datei schreiben (z.B. restart.sh).",
    )
    args = parser.parse_args()

    containers_dir = os.path.join(args.root, "containers")
    containers = find_containers(containers_dir, wanted_id=args.id)

    if not containers:
        print(f"Keine Container-Configs unter {containers_dir} gefunden.", file=sys.stderr)
        sys.exit(1)

    lines = ["#!/bin/sh", "# Automatisch generiert von docker-run-reconstruct.py", ""]

    count = 0
    for container_id, cfg_path, hcfg_path in containers:
        try:
            config = load_json(cfg_path)
            hostconfig = load_json(hcfg_path)
        except Exception as e:
            print(f"# WARNUNG: Konnte {container_id} nicht lesen: {e}", file=sys.stderr)
            continue

        state = config.get("State", {}) or {}
        if args.only_running and not state.get("Running"):
            continue

        name = (config.get("Name") or container_id).lstrip("/")
        cmd = build_run_command(container_id, config, hostconfig)

        lines.append(f"# Container: {name} ({container_id[:12]})")
        lines.append(cmd)
        lines.append("")
        count += 1

    output = "\n".join(lines)
    print(output)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        os.chmod(args.out, 0o755)
        print(f"\n# {count} Kommando(s) zusätzlich geschrieben nach: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
