"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Live Capture Engine (detect + prevent in real time)
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
A network interface -> packets -> flows -> CNN-LSTM -> prevention policy ->
Windows Firewall, while the traffic happens. app.py imports this module as
its capture engine and calls the four functions at the bottom:
list_interfaces(), start(interface), poll(after, limit), stop().

Three threads, so a burst of packets never waits for the model:

  capture  reads raw frames from Npcap (no scapy decoding: it is about 30x
           slower), parses the IP and TCP/UDP headers with
           model/flow_features.py and puts the packet on a bounded queue.
           A full queue drops the packet and counts it ("dropped"). Npcap's
           own kernel-side drops are not visible through scapy.
  flows    the only owner of the flow table: ends a flow at FIN or RST, and
           once a second ends flows that started more than 120 s ago - the
           same as flows_from_packets(..., end_on_rst=True,
           live_flow_timeout_s=120), which the saved captures were scored with.
  worker   once a second, if at least one flow has ended since the last
           prediction, predicts on the 10 most recently ended flows (one model
           window), chooses the prevention target (model/target_selection.py)
           and hands the result to the firewall engine
           (prevention_runtime.execute_for_result). Prevention therefore
           happens even when no dashboard is polling; poll() only reports.

A port scan's flows end at the victim's RST, so a scan is classified within
about a second. Only traffic to and from this machine is read (promiscuous
mode off). Only a private IPv4 address that is not this machine or the
gateway can become a target, and the firewall engine still blocks it only if
it is listed in IDS_PREVENTION_DEMO_TARGETS and execution is switched on.

Without a network (tests, rehearsal), start_replay(path, speed) plays a saved
Wireshark capture through the same engine at its recorded pace.
"""

import os
import queue
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent
MODEL_DIR = BACKEND_DIR.parent / "model"
for _p in (str(BACKEND_DIR), str(MODEL_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import flow_features as ff  # noqa: E402
from target_selection import select_target  # noqa: E402

SEQ_LEN = 10                    # flows per model window
TICK_S = 1.0                    # flow-timeout check and prediction interval (capture time)
FLOW_TIMEOUT_S = ff.ACTIVE_TIMEOUT_S
BPF_FILTER = "tcp or udp"       # IPv4 and IPv6; everything else never leaves the kernel
QUEUE_MAX = 100_000             # packets waiting for the flow thread
RESULTS_MAX = 2_000             # results kept for poll()
POLL_LIMIT_MAX = 50
IPV6_ENV = "IDS_LIVE_IPV6"      # "0" analyses IPv4 only
PREDICTION_ERROR = "last prediction failed"


def _env_ipv6():
    return os.environ.get(IPV6_ENV, "1").strip().lower() not in {"0", "false", "no", "off"}


def _utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


# ============================================================
# Packet sources
# ============================================================
# A source has read() -> (frame bytes, timestamp, linktype) or None when
# nothing arrived within ~0.1 s, clock() -> current capture time in seconds,
# speed (capture seconds per wall second) and close().


class NpcapSource:
    """Live frames from one interface through Npcap."""

    speed = 1.0

    def __init__(self, iface):
        from scapy.config import conf

        if sys.platform == "win32" and not conf.use_pcap:
            raise RuntimeError("Npcap was not found - install it from https://npcap.com and restart the backend")
        # 100 ms read timeout, so the capture thread sees stop() promptly.
        self._sock = conf.L2listen(iface=iface, promisc=False, filter=BPF_FILTER)
        fd = getattr(self._sock, "pcap_fd", None)
        self.linktype = fd.datalink() if fd is not None else ff.LINKTYPE_ETHERNET

    def read(self):
        _cls, data, ts = self._sock.recv_raw()
        if data is None:
            return None
        return data, float(ts) if ts is not None else time.time(), self.linktype

    @staticmethod
    def clock():
        return time.time()

    def close(self):
        self._sock.close()


class PcapReplaySource:
    """
    A saved .pcap/.pcapng played at its recorded pace (speed = 2.0 plays it
    twice as fast). Packet timestamps are kept as recorded, so flow features
    are exactly those of the capture; clock() runs in capture time.
    """

    def __init__(self, path, speed=1.0):
        from scapy.utils import RawPcapReader

        if speed <= 0:
            raise ValueError("speed must be positive")
        self.speed = float(speed)
        self._reader = RawPcapReader(str(path))
        self._frames = iter(self._reader)
        self._pending = None
        self._t0 = self._wall0 = None
        self.finished = False

    def _next_frame(self):
        for data, meta in self._frames:
            if hasattr(meta, "tsresol"):                       # pcapng
                return data, ((meta.tshigh << 32) + meta.tslow) / int(meta.tsresol), meta.linktype
            scale = 10 ** 9 if self._reader.nano else 10 ** 6
            return data, (meta.sec * scale + meta.usec) / scale, self._reader.linktype
        return None

    def clock(self):
        if self._t0 is None:
            return 0.0
        return self._t0 + (time.monotonic() - self._wall0) * self.speed

    def read(self):
        if self._pending is None and not self.finished:
            self._pending = self._next_frame()
            if self._pending is None:
                self.finished = True
            elif self._t0 is None:
                self._t0, self._wall0 = self._pending[1], time.monotonic()
        if self._pending is None:
            time.sleep(0.1)
            return None
        wait = (self._pending[1] - self.clock()) / self.speed
        if wait > 0:
            time.sleep(min(wait, 0.1))
            if wait > 0.1:
                return None
        frame, self._pending = self._pending, None
        return frame

    def close(self):
        self._reader.close()


# ============================================================
# Engine
# ============================================================


class LiveEngine:
    """
    service: the backend's model_service.service (predict_matrix, _build_result,
    loaded). execute(result, target_ip) -> execution dict or None:
    prevention_runtime.execute_for_result. Both default to the backend's own
    and are injectable so the engine can be tested without TensorFlow or a
    firewall.
    """

    def __init__(self, service=None, execute=None, tick_s=TICK_S, flow_timeout_s=FLOW_TIMEOUT_S,
                 ipv6=None, queue_max=QUEUE_MAX, results_max=RESULTS_MAX):
        self._service = service
        self._execute = execute
        self.tick_s = tick_s
        self.flow_timeout_s = flow_timeout_s
        self.ipv6 = _env_ipv6() if ipv6 is None else ipv6
        self.queue_max = queue_max
        self.results_max = results_max
        self._lock = threading.Lock()          # guards the state poll() reads
        self._control = threading.Lock()       # serialises start() / stop()
        self._threads = []
        self._source = None
        self._stop = threading.Event()
        self._reset(None, (), ())

    # ---------- state ----------

    def _reset(self, interface, local_ips, gateway_ips):
        self.interface = interface
        self.local_ips = sorted(set(local_ips))
        self.gateway_ips = sorted(set(gateway_ips))
        self._queue = queue.Queue(maxsize=self.queue_max)
        self._table = ff.FlowTable(active_timeout_s=self.flow_timeout_s, end_on_rst=True)
        self._next_tick = None
        self._recent = deque(maxlen=SEQ_LEN)  # (features, info) of the latest ended flows
        self._results = deque(maxlen=self.results_max)
        self._packets = self._parsed = self._dropped = 0
        self._flows = self._windows = 0
        self._predicted_at_flow = 0
        self._running = False
        self._error = None
        self._started_at = None

    def _deps(self):
        if self._service is None:
            from model_service import service
            self._service = service
        if self._execute is None:
            from prevention_runtime import execute_for_result
            self._execute = execute_for_result
        return self._service, self._execute

    # ---------- the three steps (each thread loops over one) ----------

    def _on_frame(self, data, ts, linktype):
        """Capture thread: parse one frame and queue it for the flow thread."""
        self._packets += 1
        p = ff.packet_from_bytes(data, linktype, ts)
        if p is None or (not self.ipv6 and ":" in p.src):
            return
        self._parsed += 1
        try:
            self._queue.put_nowait(p)
        except queue.Full:
            self._dropped += 1

    def _flow_step(self, clock, timeout=0.1):
        """Flow thread: one packet (if any) into the table, plus the timeout tick when due."""
        try:
            p = self._queue.get(timeout=timeout) if timeout else self._queue.get_nowait()
        except queue.Empty:
            p = None
        ended = self._table.add(p) if p is not None else []
        # While packets are still queued, time is the latest packet's own
        # timestamp, so a backlog cannot end flows its own packets would extend.
        now = p.ts if p is not None and not self._queue.empty() else clock()
        if self._next_tick is None:
            self._next_tick = now + self.tick_s
        if now >= self._next_tick:
            ended += self._table.tick(now)
            self._next_tick = now + self.tick_s
        if ended:
            rows = [(f.features(), f.info()) for f in ended]
            with self._lock:
                self._recent.extend(rows)
                self._flows += len(rows)
        return p is not None

    def _predict_step(self, now):
        """Worker thread: one prediction on the latest window, if a flow ended since the last one."""
        with self._lock:
            if self._flows == self._predicted_at_flow or len(self._recent) < SEQ_LEN:
                return None
            self._predicted_at_flow = self._flows
            window = list(self._recent)
        service, execute = self._deps()
        X = np.array([[row[c] for c in ff.FEATURE_COLS] for row, _ in window], dtype="float32")
        result = service._build_result(service.predict_matrix(X)[0])
        sources = [info["Source IP"] for _, info in window]
        target = select_target(sources, self.local_ips, self.gateway_ips)
        result["source_ip"] = target
        result["time"] = _utc(now)
        result["window_flows"] = [
            {"src": i["Source IP"], "sport": int(i["Source Port"]), "dst": i["Destination IP"],
             "dport": int(row["Destination Port"]), "proto": "TCP" if i["Protocol"] == ff.TCP else "UDP"}
            for row, i in window
        ]
        # The firewall call happens here, not in poll(): blocking must not
        # depend on a dashboard being open.
        outcome = execute(result, target)
        if outcome is not None:
            result["execution"] = outcome
        with self._lock:
            result["window"] = self._windows
            self._windows += 1
            self._results.append(result)
            if self._error and self._error.startswith(PREDICTION_ERROR):
                self._error = None          # predictions work again
        return result

    # ---------- threads ----------

    # Each run's threads get that run's own stop event, so a thread that is
    # slow to exit can never keep running into the next run.

    def _fail(self, stop, where, exc):
        with self._lock:
            self._error = f"{where}: {exc}"
        stop.set()

    def _capture_loop(self, source, stop):
        try:
            while not stop.is_set():
                frame = source.read()
                if frame is not None:
                    self._on_frame(*frame)
        except Exception as e:
            self._fail(stop, "capture stopped", e)

    def _flow_loop(self, source, stop):
        try:
            while not stop.is_set():
                self._flow_step(source.clock)
        except Exception as e:
            self._fail(stop, "flow tracking stopped", e)

    def _worker_loop(self, source, stop):
        while not stop.wait(self.tick_s / source.speed):
            try:
                self._predict_step(source.clock())
            except Exception as e:      # one bad window must not end the capture
                with self._lock:
                    self._error = f"{PREDICTION_ERROR}: {e}"

    # ---------- public ----------

    def start(self, source, interface, local_ips=(), gateway_ips=()):
        with self._control:
            self._stop_locked()
            service, _ = self._deps()
            if not getattr(service, "loaded", True):
                source.close()
                raise RuntimeError("The model is not loaded yet - try again in a few seconds")
            with self._lock:
                self._reset(interface, local_ips, gateway_ips)
                self._source = source
                self._stop = stop = threading.Event()
                self._running = True
                self._started_at = time.time()
            self._threads = [threading.Thread(target=loop, args=(source, stop), name=f"live-{name}", daemon=True)
                             for name, loop in (("capture", self._capture_loop), ("flows", self._flow_loop),
                                                ("worker", self._worker_loop))]
            for t in self._threads:
                t.start()
        return {"running": True, "interface": interface, "local_ips": self.local_ips,
                "gateway_ips": self.gateway_ips, "ipv6": self.ipv6}

    def _stop_locked(self):
        self._stop.set()
        for t in self._threads:
            t.join(timeout=3)
        self._threads = []
        if self._source is not None:
            try:
                self._source.close()
            except Exception:
                pass
            self._source = None
        self._running = False

    def stop(self):
        with self._control:
            self._stop_locked()
        return self.poll(after=float("inf"))

    def poll(self, after=-1, limit=POLL_LIMIT_MAX):
        """
        Results with window number > after, oldest first, at most `limit`.
        queue_depth: newer results still waiting for the next poll.
        skipped: results that fell out of the buffer before being polled.
        """
        limit = max(1, min(int(limit), POLL_LIMIT_MAX))
        with self._lock:
            newer = [r for r in self._results if r["window"] > after]
            oldest = self._results[0]["window"] if self._results else self._windows
            skipped = max(0, oldest - (after + 1)) if after != float("inf") else 0
            running = self._running and not self._stop.is_set()
            return {
                "running": running,
                "interface": self.interface,
                "packets": self._packets,
                "flows": self._flows,
                "windows": self._windows,
                "results": [dict(r) for r in newer[:limit]],
                "skipped": skipped,
                "queue_depth": max(0, len(newer) - limit),
                "dropped": self._dropped,
                "packets_analysed": self._parsed,
                "flows_in_progress": len(self._table.flows),
                "packet_queue": self._queue.qsize(),
                "ipv6": self.ipv6,
                "local_ips": self.local_ips,
                "gateway_ips": self.gateway_ips,
                "started_at": _utc(self._started_at) if self._started_at else None,
                "error": self._error,
            }


# ============================================================
# Interfaces and addresses (scapy)
# ============================================================


def _interfaces():
    from scapy.config import conf
    from scapy.interfaces import get_working_ifaces

    if sys.platform == "win32" and not conf.use_pcap:
        raise RuntimeError("Npcap was not found - install it from https://npcap.com and restart the backend")
    return list(get_working_ifaces())


def _usable(ip):
    return bool(ip) and not ip.startswith(("127.", "169.254.", "0."))


def list_interfaces():
    """[{"name", "description", "ip", "default"}], usable ones (with an IPv4 address) first."""
    from scapy.config import conf

    default = getattr(conf.iface, "name", None)
    found = [{"name": i.name, "description": i.description or i.name, "ip": i.ip or None,
              "default": i.name == default} for i in _interfaces()]
    return sorted(found, key=lambda i: (not _usable(i["ip"]), not i["default"], i["name"]))


def _find_interface(name):
    for iface in _interfaces():
        if name in (iface.name, iface.description, getattr(iface, "network_name", None)):
            return iface
    raise ValueError(f"Unknown interface '{name}' - choose one from /api/live/interfaces")


def _local_and_gateway_ips(iface):
    """This machine's IPv4 addresses and every gateway in the routing table: never targets."""
    from scapy.config import conf

    local = {i.ip for i in _interfaces() if i.ip}
    if getattr(iface, "ip", None):
        local.add(iface.ip)
    try:
        import prevention_executor as pe
        local |= pe._local_addresses()
    except Exception:
        pass
    gateways = set()
    try:
        for route in conf.route.routes:
            if route[2] and route[2] != "0.0.0.0":
                gateways.add(route[2])
    except Exception:
        pass
    return local, gateways


# ============================================================
# Module interface used by app.py
# ============================================================

_engine = LiveEngine()


def start(interface):
    iface = _find_interface(interface)
    local, gateways = _local_and_gateway_ips(iface)
    return _engine.start(NpcapSource(iface), iface.name, local, gateways)


def start_replay(path, speed=1.0, local_ips=(), gateway_ips=()):
    """Plays a saved capture through the live engine (rehearsal without a network)."""
    return _engine.start(PcapReplaySource(path, speed), f"replay:{Path(path).name}", local_ips, gateway_ips)


def poll(after=-1, limit=POLL_LIMIT_MAX):
    return _engine.poll(after, limit)


def stop():
    return _engine.stop()
