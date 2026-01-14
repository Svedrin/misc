#!/usr/bin/env python3
"""
udp_over_zmq.py

Two modes:

1) Server:
   - Binds a ZeroMQ socket and receives messages (each message is one UDP payload).
   - Forwards each payload via UDP to a fixed destination (host:port) given on CLI.

2) Client:
   - Connects to the server's ZeroMQ socket.
   - Listens on a local UDP socket (host:port) and forwards each received UDP payload
     as a ZeroMQ message to the server.

Queueing / caching policy (memory only, intentionally):
- Very generous in-memory buffering on both sides (high water marks set to 0 -> "no limit").
- OS socket buffers enlarged where possible.

At-most-once delivery intent:
- No application-level ACKs / retries are implemented.
- ZMQ_IMMEDIATE=1: if not connected, sends fail / drop instead of queueing for a future connection.
- LINGER=0 on close: do not try to flush buffered messages on shutdown.
- With these settings, delivery is best-effort / at-most-once from the application's perspective.

Requirements:
    pip install pyzmq
"""

import argparse
import signal
import socket
import sys
import time
from typing import Optional, Tuple

import zmq


def parse_hostport(value: str) -> Tuple[str, int]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("Expected HOST:PORT")
    host, port_s = value.rsplit(":", 1)
    host = host.strip() or "0.0.0.0"
    try:
        port = int(port_s)
    except ValueError as e:
        raise argparse.ArgumentTypeError("PORT must be an integer") from e
    if not (0 <= port <= 65535):
        raise argparse.ArgumentTypeError("PORT out of range")
    return host, port


def tune_zmq_socket(
    zsock: zmq.Socket,
    *,
    hwm: int = 0,
    immediate: bool = True,
    linger_ms: int = 0,
    sndbuf: int = 8 * 1024 * 1024,
    rcvbuf: int = 8 * 1024 * 1024,
    backlog: int = 10_000,
    sndtimeo_ms: int = 0,
    rcvtimeo_ms: int = 1000,
) -> None:
    """
    hwm=0 means "no limit" in libzmq (be mindful of RAM usage).
    immediate=True drops messages when not connected (supports at-most-once semantics).
    linger_ms=0 drops pending messages on close (do not block on shutdown).
    """
    # Queue capacity (in messages). 0 == "no limit"
    zsock.setsockopt(zmq.SNDHWM, hwm)
    zsock.setsockopt(zmq.RCVHWM, hwm)

    # At-most-once leaning behavior
    zsock.setsockopt(zmq.IMMEDIATE, 1 if immediate else 0)
    zsock.setsockopt(zmq.LINGER, linger_ms)

    # OS buffer sizes (bytes) - best effort; may be capped by OS limits
    zsock.setsockopt(zmq.SNDBUF, sndbuf)
    zsock.setsockopt(zmq.RCVBUF, rcvbuf)

    # Pending connection backlog
    try:
        zsock.setsockopt(zmq.BACKLOG, backlog)
    except AttributeError:
        # Older pyzmq/libzmq may not expose BACKLOG
        pass

    # Timeouts: 0 means "block forever". We keep recv with timeout to allow clean shutdown.
    zsock.setsockopt(zmq.SNDTIMEO, sndtimeo_ms)
    zsock.setsockopt(zmq.RCVTIMEO, rcvtimeo_ms)


def make_udp_socket(
    bind: Optional[Tuple[str, int]] = None,
    *,
    rcvbuf: int = 8 * 1024 * 1024,
    sndbuf: int = 8 * 1024 * 1024,
) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Best-effort buffer tuning; OS may clamp values.
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
    except OSError:
        pass
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sndbuf)
    except OSError:
        pass

    if bind is not None:
        s.bind(bind)
    return s


class StopFlag:
    def __init__(self) -> None:
        self._stop = False

    def set(self, *_args) -> None:
        self._stop = True

    @property
    def stop(self) -> bool:
        return self._stop


def run_server(args: argparse.Namespace) -> int:
    ctx = zmq.Context.instance()
    stop = StopFlag()

    def _handle_signal(signum, frame):
        stop.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # ZMQ side: PULL receives one message per UDP payload
    zsock = ctx.socket(zmq.PULL)
    tune_zmq_socket(
        zsock,
        hwm=args.zmq_hwm,
        immediate=True,
        linger_ms=0,
        sndbuf=args.zmq_sndbuf,
        rcvbuf=args.zmq_rcvbuf,
        backlog=args.zmq_backlog,
        sndtimeo_ms=0,
        rcvtimeo_ms=1000,
    )

    if args.bind.startswith(("tcp://", "ipc://", "inproc://")):
        endpoint = args.bind
    else:
        endpoint = f"tcp://{args.bind}"
    zsock.bind(endpoint)

    # UDP side: forward to fixed destination
    udp = make_udp_socket(bind=None, rcvbuf=args.udp_rcvbuf, sndbuf=args.udp_sndbuf)
    dest_host, dest_port = parse_hostport(args.dest)

    print(f"[server] ZMQ bind: {endpoint}")
    print(f"[server] UDP forward destination: {dest_host}:{dest_port}")
    print("[server] running... (Ctrl-C to stop)")

    forwarded = 0
    dropped = 0

    while not stop.stop:
        try:
            msg = zsock.recv()  # bytes
        except zmq.Again:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[server] ZMQ recv error: {e}", file=sys.stderr)
            continue

        if not msg:
            continue

        try:
            udp.sendto(msg, (dest_host, dest_port))
            forwarded += 1
        except Exception as e:
            # UDP send failure (rare). We drop to preserve at-most-once behavior.
            dropped += 1
            if args.verbose:
                print(f"[server] UDP sendto error (drop): {e}", file=sys.stderr)

        if args.stats_interval > 0 and (forwarded + dropped) % args.stats_interval == 0:
            print(f"[server] forwarded={forwarded} dropped={dropped}")

    print(f"[server] stopping. forwarded={forwarded} dropped={dropped}")
    try:
        zsock.close(0)
    except Exception:
        pass
    try:
        udp.close()
    except Exception:
        pass
    return 0


def run_client(args: argparse.Namespace) -> int:
    ctx = zmq.Context.instance()
    stop = StopFlag()

    def _handle_signal(signum, frame):
        stop.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # UDP side: listen locally
    listen_host, listen_port = parse_hostport(args.listen)
    udp = make_udp_socket(bind=(listen_host, listen_port), rcvbuf=args.udp_rcvbuf, sndbuf=args.udp_sndbuf)
    udp.settimeout(1.0)

    # ZMQ side: PUSH sends one message per UDP payload
    zsock = ctx.socket(zmq.PUSH)
    tune_zmq_socket(
        zsock,
        hwm=args.zmq_hwm,
        immediate=False,  # queue when disconnected
        linger_ms=0,      # drop buffered on close
        sndbuf=args.zmq_sndbuf,
        rcvbuf=args.zmq_rcvbuf,
        backlog=args.zmq_backlog,
        sndtimeo_ms=0,    # block on send if connected but peer is slow and HWM is finite
        rcvtimeo_ms=1000,
    )

    # Keep reconnect attempts from hammering CPU if server is down
    try:
        zsock.setsockopt(zmq.RECONNECT_IVL, args.zmq_reconnect_ivl_ms)
        zsock.setsockopt(zmq.RECONNECT_IVL_MAX, args.zmq_reconnect_ivl_max_ms)
    except Exception:
        pass

    if args.connect.startswith(("tcp://", "ipc://", "inproc://")):
        endpoint = args.connect
    else:
        endpoint = f"tcp://{args.connect}"
    zsock.connect(endpoint)

    print(f"[client] UDP listen: {listen_host}:{listen_port}")
    print(f"[client] ZMQ connect: {endpoint}")
    print("[client] running... (Ctrl-C to stop)")

    sent = 0
    dropped = 0

    while not stop.stop:
        try:
            data, _addr = udp.recvfrom(args.udp_max_datagram)
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[client] UDP recv error: {e}", file=sys.stderr)
            continue

        if not data:
            continue

        # At-most-once intent: if not connected, IMMEDIATE causes send to fail immediately
        try:
            zsock.send(data, flags=zmq.DONTWAIT if args.nonblocking_send else 0)
            sent += 1
        except zmq.Again:
            # Queue full or not connected => drop
            dropped += 1
            if args.verbose:
                print("[client] ZMQ send would block / not connected (drop)", file=sys.stderr)
        except Exception as e:
            dropped += 1
            if args.verbose:
                print(f"[client] ZMQ send error (drop): {e}", file=sys.stderr)

        if args.stats_interval > 0 and (sent + dropped) % args.stats_interval == 0:
            print(f"[client] sent={sent} dropped={dropped}")

    print(f"[client] stopping. sent={sent} dropped={dropped}")
    try:
        zsock.close(0)
    except Exception:
        pass
    try:
        udp.close()
    except Exception:
        pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Bridge UDP over ZeroMQ with large in-memory queues and at-most-once behavior."
    )
    sub = p.add_subparsers(dest="mode", required=True)

    # Common tuning defaults
    def add_tuning(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--zmq-hwm", type=int, default=0,
                        help="ZMQ high-water mark (messages). 0 means 'no limit' (RAM risk). Default: 0")
        sp.add_argument("--zmq-sndbuf", type=int, default=16 * 1024 * 1024,
                        help="ZMQ OS send buffer bytes. Default: 16 MiB")
        sp.add_argument("--zmq-rcvbuf", type=int, default=16 * 1024 * 1024,
                        help="ZMQ OS recv buffer bytes. Default: 16 MiB")
        sp.add_argument("--zmq-backlog", type=int, default=10000,
                        help="ZMQ backlog for pending connections (best effort). Default: 10000")
        sp.add_argument("--udp-sndbuf", type=int, default=8 * 1024 * 1024,
                        help="UDP OS send buffer bytes. Default: 8 MiB")
        sp.add_argument("--udp-rcvbuf", type=int, default=8 * 1024 * 1024,
                        help="UDP OS recv buffer bytes. Default: 8 MiB")
        sp.add_argument("--stats-interval", type=int, default=0,
                        help="Print stats every N packets (0 disables). Default: 0")
        sp.add_argument("--verbose", action="store_true", help="More logging on drops/errors.")

    sp_s = sub.add_parser("server", help="Run as server: ZMQ -> UDP")
    sp_s.add_argument("--bind", required=True,
                      help="ZMQ bind endpoint. Example: 0.0.0.0:5555 or tcp://0.0.0.0:5555")
    sp_s.add_argument("--dest", required=True, type=str,
                      help="UDP destination HOST:PORT (fixed). Example: 10.0.0.5:9999")
    add_tuning(sp_s)

    sp_c = sub.add_parser("client", help="Run as client: UDP -> ZMQ")
    sp_c.add_argument("--connect", required=True,
                      help="ZMQ connect endpoint. Example: server.example.com:5555 or tcp://server:5555")
    sp_c.add_argument("--listen", required=True,
                      help="Local UDP listen HOST:PORT. Example: 0.0.0.0:9999")
    sp_c.add_argument("--udp-max-datagram", type=int, default=65507,
                      help="Max UDP datagram size to read. Default: 65507")
    sp_c.add_argument("--nonblocking-send", action="store_true",
                      help="Use DONTWAIT for ZMQ send; drops immediately if would block.")
    sp_c.add_argument("--zmq-reconnect-ivl-ms", type=int, default=250,
                      help="ZMQ reconnect interval (ms). Default: 250")
    sp_c.add_argument("--zmq-reconnect-ivl-max-ms", type=int, default=5000,
                      help="ZMQ max reconnect interval (ms). Default: 5000")
    add_tuning(sp_c)

    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "server":
        return run_server(args)
    if args.mode == "client":
        return run_client(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
