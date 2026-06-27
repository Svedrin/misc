#!/usr/bin/env python3
"""Docker TUI — containers, volumes and images."""

import os
import re
import shutil
import subprocess
from typing import Any

import docker
import docker.errors
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

# ─── helpers ──────────────────────────────────────────────────────────────────

RESTART_POLICIES = ["no", "always", "unless-stopped", "on-failure"]


def _docker_client() -> docker.DockerClient:
    return docker.from_env()


def _container_ips(container) -> str:
    nets = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    ips = [f"{name}:{cfg['IPAddress']}" for name, cfg in nets.items() if cfg.get("IPAddress")]
    return ", ".join(ips) if ips else "—"


def _status_style(status: str) -> str:
    s = status.lower()
    if s == "running":
        return "bold green"
    if s in ("exited", "dead"):
        return "bold red"
    if s in ("paused", "restarting"):
        return "bold yellow"
    return "dim"


def _short_image(image: str) -> str:
    return re.sub(r"@sha256:[0-9a-f]+$", "", image)


def _fmt_size(b: int) -> str:
    for unit, div in [("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)]:
        if b >= div:
            return f"{b / div:.1f} {unit}"
    return f"{b} B"


def _container_snapshot(c) -> dict[str, Any]:
    attrs = c.attrs
    cfg   = attrs.get("Config", {})
    hcfg  = attrs.get("HostConfig", {})
    nets  = attrs.get("NetworkSettings", {}).get("Networks", {})

    env_list = cfg.get("Env") or []
    env = {k: v for k, v in (e.split("=", 1) for e in env_list if "=" in e)}

    ports = {}
    for cport, bindings in (hcfg.get("PortBindings") or {}).items():
        if bindings:
            ports[cport] = [
                {"HostIp": b.get("HostIp", ""), "HostPort": b.get("HostPort", "")}
                for b in bindings
            ]
        else:
            ports[cport] = None

    return {
        "name":          c.name,
        "image":         cfg.get("Image", ""),
        "env":           env,
        "networks":      list(nets.keys()),
        "ports":         ports,
        "restart_policy": hcfg.get("RestartPolicy", {}).get("Name", "no"),
        "volumes":       hcfg.get("Binds") or [],
        "labels":        cfg.get("Labels") or {},
        "command":       cfg.get("Cmd") or [],
        "entrypoint":    cfg.get("Entrypoint") or [],
        "hostname":      cfg.get("Hostname", ""),
        "privileged":    hcfg.get("Privileged", False),
        "network_mode":  hcfg.get("NetworkMode", ""),
        "cap_add":       hcfg.get("CapAdd") or [],
        "cap_drop":      hcfg.get("CapDrop") or [],
        "extra_hosts":   hcfg.get("ExtraHosts") or [],
        "dns":           hcfg.get("Dns") or [],
    }


def _redeploy(snap: dict[str, Any]) -> None:
    client = _docker_client()

    try:
        old = client.containers.get(snap["name"])
        was_running = old.status == "running"
        old.stop(timeout=10)
        old.remove()
    except docker.errors.NotFound:
        was_running = True

    env_list = [f"{k}={v}" for k, v in snap["env"].items()]

    kwargs: dict[str, Any] = {
        "image":          snap["image"],
        "name":           snap["name"],
        "environment":    env_list,
        "restart_policy": {"Name": snap["restart_policy"]},
        "volumes":        snap["volumes"],
        "labels":         snap["labels"],
        "privileged":     snap["privileged"],
        "cap_add":        snap["cap_add"] or None,
        "cap_drop":       snap["cap_drop"] or None,
        "extra_hosts":    snap["extra_hosts"] or None,
        "dns":            snap["dns"] or None,
        "detach":         True,
    }

    if snap["hostname"]:    kwargs["hostname"]   = snap["hostname"]
    if snap["command"]:     kwargs["command"]    = snap["command"]
    if snap["entrypoint"]:  kwargs["entrypoint"] = snap["entrypoint"]
    if snap["ports"]:       kwargs["ports"]      = snap["ports"]

    extra_nets: list[str] = []
    if snap["networks"]:
        nm = snap.get("network_mode", "")
        if nm and nm not in snap["networks"] and not nm.startswith(("bridge", "host", "none")):
            kwargs["network"] = nm
        else:
            kwargs["network"] = snap["networks"][0]
            extra_nets = snap["networks"][1:]
    elif snap.get("network_mode"):
        kwargs["network_mode"] = snap["network_mode"]

    container = client.containers.run(**kwargs)

    for net_name in extra_nets:
        try:
            client.networks.get(net_name).connect(container)
        except docker.errors.NotFound:
            pass

    if not was_running:
        container.stop(timeout=10)


# ─── dynamic row widgets ───────────────────────────────────────────────────────

class EnvVarRow(Horizontal):
    def __init__(self, key: str = "", value: str = "") -> None:
        super().__init__(classes="dyn-row")
        self._k, self._v = key, value

    def compose(self) -> ComposeResult:
        yield Input(value=self._k, placeholder="KEY",   classes="env-key")
        yield Input(value=self._v, placeholder="VALUE", classes="env-val")
        yield Button("✕", classes="row-rm", variant="error")

    @on(Button.Pressed, ".row-rm")
    def _rm(self) -> None:
        self.remove()


class VolumeRow(Horizontal):
    def __init__(self, binding: str = "") -> None:
        super().__init__(classes="dyn-row")
        self._b = binding

    def compose(self) -> ComposeResult:
        yield Input(value=self._b, placeholder="/host/path:/container/path[:ro]", classes="vol-input")
        yield Button("✕", classes="row-rm", variant="error")

    @on(Button.Pressed, ".row-rm")
    def _rm(self) -> None:
        self.remove()


class NetworkRow(Horizontal):
    def __init__(self, network: str = "") -> None:
        super().__init__(classes="dyn-row")
        self._n = network

    def compose(self) -> ComposeResult:
        yield Input(value=self._n, placeholder="network-name", classes="net-input")
        yield Button("✕", classes="row-rm", variant="error")

    @on(Button.Pressed, ".row-rm")
    def _rm(self) -> None:
        self.remove()


class PortRow(Horizontal):
    def __init__(self, container_port: str = "", host_port: str = "") -> None:
        super().__init__(classes="dyn-row")
        self._cp, self._hp = container_port, host_port

    def compose(self) -> ComposeResult:
        yield Input(value=self._cp, placeholder="80/tcp",                    classes="port-cport")
        yield Label("→",                                                       classes="port-arrow")
        yield Input(value=self._hp, placeholder="8080  (blank = expose only)", classes="port-hport")
        yield Button("✕", classes="row-rm", variant="error")

    @on(Button.Pressed, ".row-rm")
    def _rm(self) -> None:
        self.remove()


# ─── wizard screen ─────────────────────────────────────────────────────────────

class WizardScreen(ModalScreen[dict | None]):
    BINDINGS = [
        Binding("ctrl+s",    "deploy",       "Deploy"),
        Binding("escape",    "cancel",        "Cancel"),
        Binding("ctrl+right","next_tab",      "Next tab",    show=False),
        Binding("ctrl+left", "prev_tab",      "Prev tab",    show=False),
        Binding("ctrl+v",    "pick_volume",   "Pick volume", show=False),
    ]

    def __init__(self, snap: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._snap = snap

    def compose(self) -> ComposeResult:
        snap      = self._snap or {}
        is_new    = self._snap is None
        title     = "New Container" if is_new else f"Edit — {snap.get('name', '')}"
        btn_label = "Deploy" if is_new else "Redeploy"

        rp = snap.get("restart_policy", "no")
        if rp not in RESTART_POLICIES:
            rp = "no"

        with Vertical(id="wizard-outer"):
            yield Label(title, id="wizard-title")
            with TabbedContent(id="wizard-tabs"):
                with TabPane("Basic", id="tab-basic"):
                    with ScrollableContainer():
                        yield Label("Name" + ("" if is_new else "  (fixed)"), classes="field-lbl")
                        yield Input(value=snap.get("name", ""), placeholder="my-container",
                                    id="inp-name", disabled=not is_new)
                        yield Label("Image", classes="field-lbl")
                        yield Input(value=snap.get("image", ""), placeholder="nginx:latest", id="inp-image")
                        yield Label("Restart policy", classes="field-lbl")
                        yield Select(options=[(p, p) for p in RESTART_POLICIES], value=rp, id="sel-restart")
                        yield Label("Hostname (optional)", classes="field-lbl")
                        yield Input(value=snap.get("hostname", ""), placeholder="", id="inp-hostname")

                with TabPane("Environment", id="tab-env"):
                    with ScrollableContainer(id="env-list"):
                        for k, v in sorted(snap.get("env", {}).items()):
                            yield EnvVarRow(k, v)
                    yield Button("+ Add variable", id="btn-add-env", variant="success")

                with TabPane("Volumes", id="tab-vol"):
                    with ScrollableContainer(id="vol-list"):
                        for vol in snap.get("volumes", []):
                            yield VolumeRow(vol)
                    with Horizontal(id="vol-buttons"):
                        yield Button("+ Add path", id="btn-add-vol", variant="success")
                        yield Button("Pick Docker volume… [Ctrl+V]", id="btn-pick-vol", variant="default")

                with TabPane("Networks", id="tab-net"):
                    with ScrollableContainer(id="net-list"):
                        for net in snap.get("networks", []):
                            yield NetworkRow(net)
                    yield Button("+ Add network", id="btn-add-net", variant="success")

                with TabPane("Ports", id="tab-ports"):
                    with ScrollableContainer(id="port-list"):
                        for cport, bindings in snap.get("ports", {}).items():
                            if bindings:
                                for b in bindings:
                                    yield PortRow(cport, b.get("HostPort", ""))
                            else:
                                yield PortRow(cport, "")
                    yield Button("+ Add port", id="btn-add-port", variant="success")

                with TabPane("Advanced", id="tab-adv"):
                    with ScrollableContainer():
                        yield Checkbox("Privileged", value=snap.get("privileged", False), id="chk-privileged")
                        yield Label("cap_add  (comma-separated)", classes="field-lbl")
                        yield Input(value=", ".join(snap.get("cap_add", [])),
                                    placeholder="SYS_ADMIN, NET_ADMIN", id="inp-cap-add")
                        yield Label("cap_drop  (comma-separated)", classes="field-lbl")
                        yield Input(value=", ".join(snap.get("cap_drop", [])),
                                    placeholder="ALL", id="inp-cap-drop")
                        yield Label("Extra hosts  (host:ip, comma-separated)", classes="field-lbl")
                        yield Input(value=", ".join(snap.get("extra_hosts", [])),
                                    placeholder="myhost:192.168.1.10", id="inp-extra-hosts")
                        yield Label("DNS servers  (comma-separated)", classes="field-lbl")
                        yield Input(value=", ".join(snap.get("dns", [])),
                                    placeholder="8.8.8.8, 8.8.4.4", id="inp-dns")

            with Horizontal(id="wizard-buttons"):
                yield Button(f"{btn_label}  [Ctrl+S]", id="btn-deploy", variant="primary")
                yield Button("Cancel  [Esc]",          id="btn-cancel", variant="default")

    # ── row buttons ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-add-env")
    def _add_env(self) -> None:
        lst = self.query_one("#env-list")
        lst.mount(EnvVarRow())
        lst.scroll_end(animate=False)

    @on(Button.Pressed, "#btn-add-vol")
    def _add_vol(self) -> None:
        lst = self.query_one("#vol-list")
        lst.mount(VolumeRow())
        lst.scroll_end(animate=False)

    @on(Button.Pressed, "#btn-pick-vol")
    def _btn_pick_vol(self) -> None:
        self.action_pick_volume()

    @on(Button.Pressed, "#btn-add-net")
    def _add_net(self) -> None:
        lst = self.query_one("#net-list")
        lst.mount(NetworkRow())
        lst.scroll_end(animate=False)

    @on(Button.Pressed, "#btn-add-port")
    def _add_port(self) -> None:
        lst = self.query_one("#port-list")
        lst.mount(PortRow())
        lst.scroll_end(animate=False)

    # ── tab / volume-picker navigation ───────────────────────────────────────

    def action_next_tab(self) -> None:
        self.query_one(TabbedContent).query_one("Tabs").action_next_tab()

    def action_prev_tab(self) -> None:
        self.query_one(TabbedContent).query_one("Tabs").action_previous_tab()

    def action_pick_volume(self) -> None:
        try:
            client = _docker_client()
            names = sorted(v.name for v in client.volumes.list())
        except Exception as exc:
            self.notify(f"Could not list volumes: {exc}", severity="error")
            return
        if not names:
            self.notify("No Docker volumes found.", timeout=3)
            return
        self.app.push_screen(VolumePickerScreen(names), self._after_vpick)

    def _after_vpick(self, vol_name: str | None) -> None:
        if not vol_name:
            return
        lst = self.query_one("#vol-list")
        row = VolumeRow(binding=f"{vol_name}:")
        lst.mount(row)
        lst.scroll_end(animate=False)
        self.call_after_refresh(lambda: row.query_one(".vol-input", Input).focus())

    # ── deploy / cancel ──────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-deploy")
    def _on_deploy(self) -> None:
        self.action_deploy()

    @on(Button.Pressed, "#btn-cancel")
    def _on_cancel(self) -> None:
        self.action_cancel()

    def action_deploy(self) -> None:
        snap = self._collect()
        if snap is not None:
            self.dismiss(snap)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _collect(self) -> dict[str, Any] | None:
        name = self.query_one("#inp-name", Input).value.strip()
        if not name:
            self.notify("Container name is required.", severity="error")
            return None
        image = self.query_one("#inp-image", Input).value.strip()
        if not image:
            self.notify("Image is required.", severity="error")
            return None

        sel     = self.query_one("#sel-restart", Select)
        restart = str(sel.value) if sel.value != Select.BLANK else "no"
        hostname = self.query_one("#inp-hostname", Input).value.strip() or name

        env: dict[str, str] = {}
        for row in self.query(EnvVarRow):
            k = row.query_one(".env-key", Input).value.strip()
            v = row.query_one(".env-val", Input).value
            if k:
                env[k] = v

        volumes = [
            row.query_one(".vol-input", Input).value.strip()
            for row in self.query(VolumeRow)
            if row.query_one(".vol-input", Input).value.strip()
        ]

        networks = [
            row.query_one(".net-input", Input).value.strip()
            for row in self.query(NetworkRow)
            if row.query_one(".net-input", Input).value.strip()
        ]

        ports: dict[str, Any] = {}
        for row in self.query(PortRow):
            cp = row.query_one(".port-cport", Input).value.strip()
            hp = row.query_one(".port-hport", Input).value.strip()
            if cp:
                ports[cp] = [{"HostIp": "", "HostPort": hp}] if hp else None

        def _csv(wid: str) -> list[str]:
            v = self.query_one(wid, Input).value.strip()
            return [x.strip() for x in v.split(",") if x.strip()]

        base = self._snap or {}
        return {
            "name":           name,
            "image":          image,
            "env":            env,
            "networks":       networks,
            "ports":          ports,
            "restart_policy": restart,
            "volumes":        volumes,
            "labels":         base.get("labels", {}),
            "command":        base.get("command", []),
            "entrypoint":     base.get("entrypoint", []),
            "hostname":       hostname,
            "privileged":     self.query_one("#chk-privileged", Checkbox).value,
            "network_mode":   base.get("network_mode", ""),
            "cap_add":        _csv("#inp-cap-add"),
            "cap_drop":       _csv("#inp-cap-drop"),
            "extra_hosts":    _csv("#inp-extra-hosts"),
            "dns":            _csv("#inp-dns"),
        }


# ─── volume picker (wizard helper) ────────────────────────────────────────────

class VolumePickerScreen(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, volumes: list[str]) -> None:
        super().__init__()
        self._volumes = volumes

    def compose(self) -> ComposeResult:
        with Vertical(id="vpick-outer"):
            yield Label("Select a Docker volume  [dim](Enter to pick, Esc to cancel)[/]", id="vpick-title")
            yield ListView(*[ListItem(Label(v), name=v) for v in self._volumes], id="vpick-list")

    @on(ListView.Selected)
    def _selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.name)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ─── new-volume screen ─────────────────────────────────────────────────────────

class NewVolumeScreen(ModalScreen[dict | None]):
    BINDINGS = [
        Binding("ctrl+s", "create", "Create"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="newvol-outer"):
            yield Label("New Volume", id="newvol-title")
            yield Label("Name", classes="field-lbl")
            yield Input(placeholder="my-volume", id="inp-volname")
            yield Label("Driver", classes="field-lbl")
            yield Input(value="local", id="inp-voldriver")
            with Horizontal(id="newvol-buttons"):
                yield Button("Create  [Ctrl+S]", id="btn-create", variant="primary")
                yield Button("Cancel  [Esc]",    id="btn-cancel", variant="default")

    @on(Button.Pressed, "#btn-create")
    def _create(self) -> None:
        self.action_create()

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self) -> None:
        self.dismiss(None)

    def action_create(self) -> None:
        name = self.query_one("#inp-volname", Input).value.strip()
        if not name:
            self.notify("Volume name is required.", severity="error")
            return
        driver = self.query_one("#inp-voldriver", Input).value.strip() or "local"
        self.dismiss({"name": name, "driver": driver})

    def action_cancel(self) -> None:
        self.dismiss(None)


# ─── pull-image screen ─────────────────────────────────────────────────────────

class PullImageScreen(ModalScreen[str | None]):
    BINDINGS = [
        Binding("ctrl+s", "pull",   "Pull"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="pullimg-outer"):
            yield Label("Pull Image", id="pullimg-title")
            yield Label("Image reference", classes="field-lbl")
            yield Input(placeholder="nginx:latest", id="inp-imgref")
            with Horizontal(id="pullimg-buttons"):
                yield Button("Pull  [Ctrl+S]", id="btn-pull",   variant="primary")
                yield Button("Cancel  [Esc]",  id="btn-cancel", variant="default")

    @on(Button.Pressed, "#btn-pull")
    def _pull(self) -> None:
        self.action_pull()

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self) -> None:
        self.dismiss(None)

    def action_pull(self) -> None:
        ref = self.query_one("#inp-imgref", Input).value.strip()
        if not ref:
            self.notify("Image reference is required.", severity="error")
            return
        self.dismiss(ref)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ─── detail screen ────────────────────────────────────────────────────────────

class DetailScreen(ModalScreen):
    BINDINGS = [
        Binding("escape,q", "dismiss", "Back"),
        Binding("e",        "edit",    "Edit & Redeploy"),
    ]

    def __init__(self, container_id: str) -> None:
        super().__init__()
        self._cid = container_id

    def compose(self) -> ComposeResult:
        client = _docker_client()
        try:
            c = client.containers.get(self._cid)
        except docker.errors.NotFound:
            with Vertical(id="detail-outer"):
                yield Label("Container not found.")
                yield Button("Back", id="btn-back")
            return

        snap = _container_snapshot(c)
        lines = [
            f"[bold]Name:[/bold]       {c.name}",
            f"[bold]ID:[/bold]         {c.short_id}",
            f"[bold]Status:[/bold]     [{_status_style(c.status)}]{c.status}[/]",
            f"[bold]Image:[/bold]      {_short_image(snap['image'])}",
            f"[bold]Networks:[/bold]   {', '.join(snap['networks']) or '—'}",
            f"[bold]IPs:[/bold]        {_container_ips(c)}",
            f"[bold]Restart:[/bold]    {snap['restart_policy']}",
            "",
            "[bold]Environment:[/bold]",
        ]
        for k, v in sorted(snap["env"].items()):
            lines.append(f"  {k}={v}")
        lines += ["", "[bold]Volumes:[/bold]"]
        for v in snap["volumes"]:
            lines.append(f"  {v}")
        lines += ["", "[bold]Ports:[/bold]"]
        for cport, bindings in snap["ports"].items():
            if bindings:
                for b in bindings:
                    lines.append(f"  {b.get('HostPort', '')}→{cport}")
            else:
                lines.append(f"  {cport} (exposed)")

        with Vertical(id="detail-outer"):
            yield Label(f"Container detail — [bold]{c.name}[/bold]", id="detail-title")
            with ScrollableContainer(id="detail-scroll"):
                yield Static("\n".join(lines), id="detail-body", markup=True)
            with Horizontal(id="detail-buttons"):
                yield Button("Edit & Redeploy  [E]", id="btn-edit", variant="primary")
                yield Button("Back  [Esc]",          id="btn-back", variant="default")

    @on(Button.Pressed, "#btn-back")
    def _back(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#btn-edit")
    def _edit(self) -> None:
        self.action_edit()

    def action_edit(self) -> None:
        client = _docker_client()
        try:
            c = client.containers.get(self._cid)
        except docker.errors.NotFound:
            self.notify("Container vanished.", severity="error")
            return
        self.app.push_screen(WizardScreen(snap=_container_snapshot(c)), self._after_wizard)

    def _after_wizard(self, snap: dict | None) -> None:
        if snap is None:
            return
        self.dismiss()
        self.app.query_one(MainScreen).do_redeploy(snap)


# ─── confirm screen ───────────────────────────────────────────────────────────

class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y",        "yes", "Yes"),
        Binding("n,escape", "no",  "No"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-outer"):
            yield Label(self._message, id="confirm-msg", markup=True)
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes  [Y]",    id="btn-yes", variant="error")
                yield Button("No  [N/Esc]", id="btn-no",  variant="default")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def _no(self) -> None:
        self.dismiss(False)


# ─── main screen ──────────────────────────────────────────────────────────────

class MainScreen(Screen):
    BINDINGS = [
        Binding("r",          "refresh",        "Refresh"),
        Binding("ctrl+right", "next_pane",       "Next pane",        show=False),
        Binding("ctrl+left",  "prev_pane",       "Prev pane",        show=False),
        # containers
        Binding("n",  "new_item",         "New"),
        Binding("e",  "edit_selected",    "Edit & Redeploy"),
        Binding("u",  "start_selected",   "Start"),
        Binding("s",  "stop_selected",    "Stop"),
        Binding("x",  "restart_selected", "Restart"),
        Binding("h",  "toggle_stopped",   "Show/Hide stopped"),
        # volumes
        Binding("b",  "browse_volume",    "Browse (ncdu)"),
        # images
        Binding("p",  "pull_image",       "Pull"),
        # universal
        Binding("d",  "delete_selected",  "Delete"),
        Binding("q",  "app.quit",         "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._show_stopped  = True
        self._containers:   list[dict] = []
        self._volumes:      list[dict] = []
        self._images:       list[dict] = []
        self._first_load    = True

    # ── layout ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="main-tabs"):
            with TabPane("Containers", id="tab-containers"):
                yield DataTable(id="ctable", cursor_type="row", zebra_stripes=True)
            with TabPane("Volumes", id="tab-volumes"):
                yield DataTable(id="vtable", cursor_type="row", zebra_stripes=True)
            with TabPane("Images", id="tab-images"):
                yield DataTable(id="itable", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        for col in ("Name", "Status", "Image", "Networks / IPs"):
            self.query_one("#ctable", DataTable).add_column(col, key=col)
        for col in ("Name", "Driver", "Mountpoint"):
            self.query_one("#vtable", DataTable).add_column(col, key=col)
        for col in ("Repository:Tag", "ID", "Size", "Created"):
            self.query_one("#itable", DataTable).add_column(col, key=col)
        self.action_refresh()
        self.set_interval(5, self.action_refresh)

    # ── tab / pane helpers ────────────────────────────────────────────────────

    def _active_tab(self) -> str:
        try:
            return str(self.query_one("#main-tabs", TabbedContent).active)
        except Exception:
            return "tab-containers"

    def action_next_pane(self) -> None:
        self.query_one("#main-tabs", TabbedContent).query_one("Tabs").action_next_tab()

    def action_prev_pane(self) -> None:
        self.query_one("#main-tabs", TabbedContent).query_one("Tabs").action_previous_tab()

    @on(TabbedContent.TabActivated)
    def _tab_switched(self, _: TabbedContent.TabActivated) -> None:
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        tab = self._active_tab()
        containers_only = {"edit_selected", "start_selected", "stop_selected",
                           "restart_selected", "toggle_stopped"}
        volumes_only    = {"browse_volume"}
        images_only     = {"pull_image"}
        if action == "new_item"        and tab == "tab-images":     return False
        if action in containers_only   and tab != "tab-containers": return False
        if action in volumes_only      and tab != "tab-volumes":    return False
        if action in images_only       and tab != "tab-images":     return False
        return True

    # ── refresh ───────────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._load_containers()
        self._load_volumes()
        self._load_images()

    # ── row-selected dispatch ─────────────────────────────────────────────────

    @on(DataTable.RowSelected)
    def _row_selected(self, _: DataTable.RowSelected) -> None:
        tab = self._active_tab()
        if tab == "tab-containers":
            self.action_open_detail()
        elif tab == "tab-volumes":
            self.action_browse_volume()

    # ── containers ────────────────────────────────────────────────────────────

    def action_new_item(self) -> None:
        tab = self._active_tab()
        if tab == "tab-containers":
            self.app.push_screen(WizardScreen(snap=None), self._after_new_container)
        elif tab == "tab-volumes":
            self.app.push_screen(NewVolumeScreen(), self._after_new_volume)

    def _after_new_container(self, snap: dict | None) -> None:
        if snap is None:
            return
        self.notify(f"Deploying {snap['name']}…", timeout=30)
        self._run_redeploy(snap)

    def action_open_detail(self) -> None:
        row = self._selected_container()
        if row:
            self.app.push_screen(DetailScreen(row["id"]))

    def action_edit_selected(self) -> None:
        row = self._selected_container()
        if not row:
            return
        client = _docker_client()
        try:
            c = client.containers.get(row["id"])
        except docker.errors.NotFound:
            self.notify("Container not found.", severity="error")
            return
        self.app.push_screen(WizardScreen(snap=_container_snapshot(c)), self._after_edit)

    def _after_edit(self, snap: dict | None) -> None:
        if snap is not None:
            self.do_redeploy(snap)

    def action_start_selected(self) -> None:
        row = self._selected_container()
        if not row:
            return
        if row["status"] == "running":
            self.notify("Already running.", timeout=2)
            return
        self._container_action(row["id"], row["name"], "start")

    def action_stop_selected(self) -> None:
        row = self._selected_container()
        if not row:
            return
        if row["status"] != "running":
            self.notify("Not running.", timeout=2)
            return
        self._container_action(row["id"], row["name"], "stop")

    def action_restart_selected(self) -> None:
        row = self._selected_container()
        if row:
            self._container_action(row["id"], row["name"], "restart")

    def action_toggle_stopped(self) -> None:
        self._show_stopped = not self._show_stopped
        self._render_containers()

    def action_delete_selected(self) -> None:
        tab = self._active_tab()
        if tab == "tab-containers":
            row = self._selected_container()
            if not row:
                return
            msg = (f"Delete [bold]{row['name']}[/bold]?\n\n"
                   "This will [red]permanently remove[/red] the container.\n"
                   "Volumes and images are left intact.")
            self.app.push_screen(ConfirmScreen(msg), lambda ok: self._exec_delete_container(ok, row))
        elif tab == "tab-volumes":
            row = self._selected_volume()
            if not row:
                return
            msg = (f"Delete volume [bold]{row['name']}[/bold]?\n\n"
                   "This will [red]permanently remove[/red] the volume and [red]all its data[/red].")
            self.app.push_screen(ConfirmScreen(msg), lambda ok: self._exec_delete_volume(ok, row))
        elif tab == "tab-images":
            row = self._selected_image()
            if not row:
                return
            msg = (f"Delete image [bold]{row['tag']}[/bold]?\n\n"
                   "This will [red]remove the image[/red] from the local store.")
            self.app.push_screen(ConfirmScreen(msg), lambda ok: self._exec_delete_image(ok, row))

    def _exec_delete_container(self, ok: bool, row: dict) -> None:
        if ok:
            self._container_action(row["id"], row["name"], "delete")

    @work(thread=True)
    def _container_action(self, cid: str, name: str, action: str) -> None:
        try:
            client = _docker_client()
            c = client.containers.get(cid)
            if action == "start":   c.start()
            elif action == "stop":  c.stop(timeout=10)
            elif action == "restart": c.restart(timeout=10)
            elif action == "delete":  c.remove(force=True)
            self.app.call_from_thread(self.notify, f"{action.capitalize()}ed {name}", timeout=3)
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"{action} failed: {exc}", severity="error", timeout=8)
        finally:
            self.app.call_from_thread(self._load_containers)

    def _selected_container(self) -> dict | None:
        table = self.query_one("#ctable", DataTable)
        idx = table.cursor_row
        if idx is None or not self._containers:
            return None
        visible = [c for c in self._containers if self._show_stopped or c["status"] == "running"]
        return visible[idx] if idx < len(visible) else None

    @work(thread=True)
    def _load_containers(self) -> None:
        try:
            client = _docker_client()
            rows = []
            for c in client.containers.list(all=True):
                rows.append({
                    "id":       c.id,
                    "name":     c.name,
                    "status":   c.status,
                    "image":    _short_image(c.attrs.get("Config", {}).get("Image", "")),
                    "ips":      _container_ips(c),
                    "networks": ", ".join(
                        c.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()
                    ) or "—",
                })
            self._containers = sorted(rows, key=lambda r: (r["status"] != "running", r["name"]))
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Docker error: {exc}", severity="error", timeout=8)
            return
        self.app.call_from_thread(self._render_containers)

    def _render_containers(self) -> None:
        table = self.query_one("#ctable", DataTable)
        table.clear()
        visible = [c for c in self._containers if self._show_stopped or c["status"] == "running"]
        for row in visible:
            style = _status_style(row["status"])
            table.add_row(
                f"[{style}]{row['name']}[/]",
                f"[{style}]{row['status']}[/]",
                row["image"],
                f"{row['networks']}  {row['ips']}",
            )
        if self._first_load:
            self.notify(f"Loaded {len(visible)} containers", timeout=2)
            self._first_load = False

    def do_redeploy(self, snap: dict[str, Any]) -> None:
        msg = (f"Redeploy [bold]{snap['name']}[/bold]?\n\n"
               "This will [red]stop and remove[/red] the existing container, then recreate it.")
        self.app.push_screen(ConfirmScreen(msg), lambda ok: self._exec_redeploy(ok, snap))

    def _exec_redeploy(self, ok: bool, snap: dict[str, Any]) -> None:
        if not ok:
            return
        self.notify(f"Redeploying {snap['name']}…", timeout=30)
        self._run_redeploy(snap)

    @work(thread=True)
    def _run_redeploy(self, snap: dict[str, Any]) -> None:
        try:
            _redeploy(snap)
            self.app.call_from_thread(self.notify, f"Done: {snap['name']}", timeout=4)
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Failed: {exc}", severity="error", timeout=10)
        finally:
            self.app.call_from_thread(self._load_containers)

    # ── volumes ───────────────────────────────────────────────────────────────

    def _after_new_volume(self, result: dict | None) -> None:
        if result is None:
            return
        self._create_volume(result["name"], result["driver"])

    @work(thread=True)
    def _create_volume(self, name: str, driver: str) -> None:
        try:
            _docker_client().volumes.create(name=name, driver=driver)
            self.app.call_from_thread(self.notify, f"Created volume {name}", timeout=3)
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Create failed: {exc}", severity="error", timeout=8)
        finally:
            self.app.call_from_thread(self._load_volumes)

    def action_browse_volume(self) -> None:
        row = self._selected_volume()
        if not row:
            return
        mp = row.get("mountpoint", "")
        if not mp:
            self.notify("No mountpoint available.", severity="error")
            return
        if not shutil.which("ncdu"):
            self.notify("ncdu is not installed — please install it first.", severity="error")
            return
        cmd = ["ncdu", mp] if os.geteuid() == 0 else ["sudo", "ncdu", mp]
        with self.app.suspend():
            subprocess.run(cmd)

    def _exec_delete_volume(self, ok: bool, row: dict) -> None:
        if ok:
            self._delete_volume(row["name"])

    @work(thread=True)
    def _delete_volume(self, name: str) -> None:
        try:
            vol = _docker_client().volumes.get(name)
            vol.remove(force=True)
            self.app.call_from_thread(self.notify, f"Deleted volume {name}", timeout=3)
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Delete failed: {exc}", severity="error", timeout=8)
        finally:
            self.app.call_from_thread(self._load_volumes)

    def _selected_volume(self) -> dict | None:
        table = self.query_one("#vtable", DataTable)
        idx = table.cursor_row
        if idx is None or not self._volumes or idx >= len(self._volumes):
            return None
        return self._volumes[idx]

    @work(thread=True)
    def _load_volumes(self) -> None:
        try:
            client = _docker_client()
            rows = []
            for v in client.volumes.list():
                rows.append({
                    "name":       v.name,
                    "driver":     v.attrs.get("Driver", "local"),
                    "mountpoint": v.attrs.get("Mountpoint", ""),
                })
            self._volumes = sorted(rows, key=lambda r: r["name"])
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Docker error: {exc}", severity="error", timeout=8)
            return
        self.app.call_from_thread(self._render_volumes)

    def _render_volumes(self) -> None:
        table = self.query_one("#vtable", DataTable)
        table.clear()
        for row in self._volumes:
            table.add_row(row["name"], row["driver"], row["mountpoint"])

    # ── images ────────────────────────────────────────────────────────────────

    def action_pull_image(self) -> None:
        self.app.push_screen(PullImageScreen(), self._after_pull)

    def _after_pull(self, ref: str | None) -> None:
        if not ref:
            return
        self.notify(f"Pulling {ref}…", timeout=60)
        self._pull_image(ref)

    @work(thread=True)
    def _pull_image(self, ref: str) -> None:
        try:
            _docker_client().images.pull(ref)
            self.app.call_from_thread(self.notify, f"Pulled {ref}", timeout=4)
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Pull failed: {exc}", severity="error", timeout=10)
        finally:
            self.app.call_from_thread(self._load_images)

    def _exec_delete_image(self, ok: bool, row: dict) -> None:
        if ok:
            self._delete_image(row["full_id"], row["tag"])

    @work(thread=True)
    def _delete_image(self, image_id: str, tag: str) -> None:
        try:
            _docker_client().images.remove(image_id, force=False)
            self.app.call_from_thread(self.notify, f"Deleted {tag}", timeout=3)
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Delete failed: {exc}", severity="error", timeout=8)
        finally:
            self.app.call_from_thread(self._load_images)

    def _selected_image(self) -> dict | None:
        table = self.query_one("#itable", DataTable)
        idx = table.cursor_row
        if idx is None or not self._images or idx >= len(self._images):
            return None
        return self._images[idx]

    @work(thread=True)
    def _load_images(self) -> None:
        try:
            client = _docker_client()
            rows = []
            for img in client.images.list():
                tags    = img.tags or ["<none>:<none>"]
                size    = _fmt_size(img.attrs.get("Size", 0))
                created = img.attrs.get("Created", "")[:10]
                short   = img.id.split(":")[-1][:12]
                for tag in tags:
                    rows.append({
                        "tag":     tag,
                        "id":      short,
                        "size":    size,
                        "created": created,
                        "full_id": img.id,
                    })
            self._images = sorted(rows, key=lambda r: r["tag"])
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f"Docker error: {exc}", severity="error", timeout=8)
            return
        self.app.call_from_thread(self._render_images)

    def _render_images(self) -> None:
        table = self.query_one("#itable", DataTable)
        table.clear()
        for row in self._images:
            table.add_row(row["tag"], row["id"], row["size"], row["created"])


# ─── app / css ────────────────────────────────────────────────────────────────

CSS = """
/* ── main layout ── */
#main-tabs                    { height: 1fr; }
#main-tabs ContentSwitcher    { height: 1fr; }
#main-tabs TabPane            { height: 100%; padding: 0; }
#ctable, #vtable, #itable     { height: 100%; }

/* ── modal alignment ── */
WizardScreen, DetailScreen, ConfirmScreen,
NewVolumeScreen, PullImageScreen { align: center middle; }

/* ── wizard ── */
#wizard-outer  { width: 95%; max-width: 150; height: 90%;
                 background: $surface; border: round $primary; padding: 1 2; }
#wizard-title  { text-style: bold; margin-bottom: 1; }
#wizard-tabs   { height: 1fr; }
.field-lbl     { margin-top: 1; color: $text-muted; }

#env-list, #vol-list, #net-list, #port-list { height: 1fr; }

.dyn-row        { height: auto; margin-bottom: 1; align: left middle; }
.dyn-row .row-rm { width: 5; min-width: 5; margin-left: 1; }

EnvVarRow .env-key  { width: 1fr; margin-right: 1; }
EnvVarRow .env-val  { width: 2fr; }
VolumeRow  .vol-input { width: 1fr; }
NetworkRow .net-input { width: 1fr; }
PortRow .port-cport  { width: 12; }
PortRow .port-arrow  { width: 3; text-align: center; }
PortRow .port-hport  { width: 1fr; }

#wizard-buttons { height: auto; margin-top: 1; align: right middle; }
#wizard-buttons Button { margin-left: 2; }
#vol-buttons    { height: auto; margin-top: 1; }
#vol-buttons Button { margin-right: 2; }

/* ── volume picker (wizard) ── */
VolumePickerScreen { align: center middle; }
#vpick-outer { width: 60; height: 70%; background: $surface;
               border: round $primary; padding: 1 2; }
#vpick-title { margin-bottom: 1; }
#vpick-list  { height: 1fr; }

/* ── new volume ── */
#newvol-outer  { width: 60; height: auto; background: $surface;
                 border: round $primary; padding: 1 2; }
#newvol-title  { text-style: bold; margin-bottom: 1; }
#newvol-buttons { height: auto; margin-top: 1; align: right middle; }
#newvol-buttons Button { margin-left: 2; }

/* ── pull image ── */
#pullimg-outer  { width: 70; height: auto; background: $surface;
                  border: round $primary; padding: 1 2; }
#pullimg-title  { text-style: bold; margin-bottom: 1; }
#pullimg-buttons { height: auto; margin-top: 1; align: right middle; }
#pullimg-buttons Button { margin-left: 2; }

/* ── detail ── */
#detail-outer  { width: 80%; max-width: 110; height: 80%;
                 background: $surface; border: round $primary; padding: 1 2; }
#detail-title  { text-style: bold; margin-bottom: 1; }
#detail-scroll { height: 1fr; }
#detail-body   { height: auto; }
#detail-buttons { height: auto; margin-top: 1; align: right middle; }
#detail-buttons Button { margin-left: 2; }

/* ── confirm ── */
#confirm-outer   { width: 62; height: auto; background: $surface;
                   border: round $warning; padding: 2 3; }
#confirm-msg     { margin-bottom: 2; }
#confirm-buttons { height: auto; align: right middle; }
#confirm-buttons Button { margin-left: 2; }
"""


class DockTUI(App):
    TITLE = "DockTUI"
    CSS = CSS

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


if __name__ == "__main__":
    DockTUI().run()
