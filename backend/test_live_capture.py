"""
Tests for backend/live_capture.py, without a network, TensorFlow or the firewall.

Run:  python backend/test_live_capture.py

The model is a stand-in (a scan = most flows got a 6-byte RST back); the
prevention policy is the real one (model/class_action_mapping.py); the
firewall call is a recorder with the contract of
prevention_runtime.execute_for_result.
"""

import os
import sys
import tempfile
import threading
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_capture as lc  # noqa: E402
from class_action_mapping import get_action  # noqa: E402

ff = lc.ff
TAB, LAP, GW, WEB = "10.66.33.57", "10.66.33.4", "10.66.33.227", "142.250.183.14"
BWD_BYTES = ff.FEATURE_COLS.index("Total Length of Bwd Packets")


class FakeService:
    loaded = True
    labels = ["BENIGN", "PortScan"]

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def predict_matrix(self, X):
        if self.fail:
            raise ValueError("model exploded")
        self.calls.append(X.copy())
        scan = (X[:, BWD_BYTES] == 6).mean() >= 0.5
        return np.array([[0.05, 0.95]] if scan else [[0.97, 0.03]])

    def _build_result(self, probs):
        i = int(np.argmax(probs))
        return {"predicted_class": self.labels[i], "confidence": float(probs[i]),
                "prevention": get_action(self.labels[i], float(probs[i]))}


class Recorder:
    """execute_for_result's contract: None unless auto_action; a dict otherwise."""

    def __init__(self):
        self.calls = []

    def __call__(self, result, target_ip):
        self.calls.append((result["predicted_class"], target_ip))
        if result["prevention"]["status"] != "auto_action":
            return None
        if target_ip is None:
            return {"executed": False, "reason": "no target", "target_ip": None}
        return {"executed": True, "rule_name": f"IDS_DEMO_block_ip_{target_ip}", "target_ip": target_ip}


def engine(**kw):
    e = lc.LiveEngine(service=kw.pop("service", FakeService()), execute=kw.pop("execute", Recorder()),
                      ipv6=kw.pop("ipv6", True), **kw)
    e.local_ips, e.gateway_ips = [LAP], [GW]
    return e


def frame(src, dst, sport, dport, flags="", payload=b"", proto="tcp"):
    from scapy.layers.inet import IP, TCP, UDP
    from scapy.layers.inet6 import IPv6
    from scapy.layers.l2 import Ether

    ip = IPv6(src=src, dst=dst) if ":" in src else IP(src=src, dst=dst)
    l4 = TCP(sport=sport, dport=dport, flags=flags) if proto == "tcp" else UDP(sport=sport, dport=dport)
    return bytes(Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02") / ip / l4 / payload)


def scan_frames(n=30, t0=1000.0):
    """nmap -sT style: SYN to a closed port, RST/ACK back, one port at a time."""
    out = []
    for i in range(n):
        out.append((frame(TAB, LAP, 40000 + i, 1 + i, "S"), t0 + i * 0.01))
        out.append((frame(LAP, TAB, 1 + i, 40000 + i, "RA"), t0 + i * 0.01 + 0.0002))
    return out


def browse_frames(n=12, t0=1000.0):
    """The laptop's own HTTPS requests (FIN-closed) and DNS from the gateway."""
    out = []
    for i in range(n):
        t = t0 + i * 0.1
        out += [(frame(LAP, WEB, 50000 + i, 443, "PA", b"g" * 400), t),
                (frame(WEB, LAP, 443, 50000 + i, "PA", b"r" * 1200), t + 0.02),
                (frame(LAP, WEB, 50000 + i, 443, "FA"), t + 0.03)]
    out += [(frame(GW, LAP, 53, 5353, proto="udp", payload=b"d" * 80), t0 + 0.5)]
    return out


def feed(e, frames, now=None):
    for data, ts in frames:
        e._on_frame(data, ts, ff.LINKTYPE_ETHERNET)
    clock = (lambda: now) if now is not None else (lambda: frames[-1][1])
    while e._flow_step(clock, timeout=0):
        pass


def test_scan_is_detected_and_the_scanner_is_blocked():
    rec = Recorder()
    e = engine(execute=rec)
    feed(e, scan_frames())
    assert e._flows == 30, "every SYN -> RST flow ends at its RST, no timeout needed"
    r = e._predict_step(1001.0)
    assert r["predicted_class"] == "PortScan" and r["prevention"]["status"] == "auto_action"
    assert r["source_ip"] == TAB and rec.calls == [("PortScan", TAB)]
    assert r["execution"]["executed"] is True, "the engine runs prevention itself, not poll()"
    assert r["window"] == 0 and len(r["window_flows"]) == 10
    assert r["window_flows"][-1] == {"src": TAB, "sport": 40029, "dst": LAP, "dport": 30, "proto": "TCP"}
    assert e._service.calls[0].shape == (10, 20), "one window of 10 flows x 20 features"
    assert e._predict_step(1002.0) is None, "no new flow ended -> no new prediction"
    feed(e, scan_frames(1, t0=1003.0))
    assert e._predict_step(1003.5)["window"] == 1


def test_benign_traffic_is_not_acted_on():
    rec = Recorder()
    e = engine(execute=rec)
    feed(e, browse_frames(), now=1010.0)
    r = e._predict_step(1010.0)
    assert r["predicted_class"] == "BENIGN" and "execution" not in r
    assert r["source_ip"] is None, "only the laptop, the gateway and a public server sent traffic"
    assert rec.calls == [("BENIGN", None)]


def test_the_laptop_and_gateway_are_never_targets():
    e = engine()
    rows = []
    for i in range(5):                        # flows the laptop and the gateway start
        rows += [frame(LAP, TAB, 1 + i, 40000 + i, "S"), frame(TAB, LAP, 40000 + i, 1 + i, "RA"),
                 frame(GW, LAP, 53, 6000 + i, "RA")]
    feed(e, [(d, 1000.0 + i * 0.01) for i, d in enumerate(rows)])
    r = e._predict_step(1001.0)
    assert r is not None and r["source_ip"] is None, "10 flows from the laptop and the gateway: no target"
    feed(e, [(frame(TAB, LAP, 41000, 445, "S"), 1001.0), (frame(LAP, TAB, 445, 41000, "RA"), 1001.001)])
    r = e._predict_step(1002.0)
    assert r["source_ip"] == TAB, "one flow from the tablet among them: the tablet is the only candidate"


def test_nothing_is_predicted_before_ten_flows():
    e = engine()
    feed(e, scan_frames(9))
    assert e._flows == 9 and e._predict_step(1001.0) is None


def test_flow_timeout_ends_quiet_flows_on_the_tick():
    e = engine(flow_timeout_s=5)
    e._on_frame(frame(TAB, LAP, 7000, 8000, payload=b"x", proto="udp"), 1000.0, ff.LINKTYPE_ETHERNET)
    e._flow_step(lambda: 1000.0, timeout=0)
    for now in (1001.0, 1002.5, 1004.9):
        e._flow_step(lambda: now, timeout=0)
    assert e._flows == 0, "not past the 5 s flow timeout yet"
    e._flow_step(lambda: 1006.0, timeout=0)
    assert e._flows == 1


def test_a_backlog_is_timed_by_its_own_packets():
    # The clock is far ahead of four queued packets of one flow (as when the
    # flow thread falls behind): they must still form one flow.
    e = engine(flow_timeout_s=5)
    for t in (0.0, 1.0, 2.0, 3.0):
        e._on_frame(frame(TAB, LAP, 7000, 8000, payload=b"x", proto="udp"), 1000.0 + t, ff.LINKTYPE_ETHERNET)
    while e._flow_step(lambda: 2000.0, timeout=0):
        pass
    assert e._flows == 1 and e._recent[-1][1]["Packets"] == 4


def test_a_full_queue_drops_and_counts():
    e = engine(queue_max=3)
    for i in range(5):
        e._on_frame(frame(TAB, LAP, 40000 + i, 80, "S"), 1000.0, ff.LINKTYPE_ETHERNET)
    e._on_frame(b"\x00" * 20, 1000.0, ff.LINKTYPE_ETHERNET)                       # not IP
    p = e.poll()
    assert (p["packets"], p["packets_analysed"], p["dropped"], p["packet_queue"]) == (6, 5, 2, 3)


def test_ipv6_is_analysed_unless_switched_off():
    v6 = frame("2001:db8::66", "2001:db8::1", 50000, 443, payload=b"q" * 1200, proto="udp")
    on, off = engine(ipv6=True), engine(ipv6=False)
    for e in (on, off):
        e._on_frame(v6, 1000.0, ff.LINKTYPE_ETHERNET)
    assert on.poll()["packets_analysed"] == 1 and off.poll()["packets_analysed"] == 0
    os.environ[lc.IPV6_ENV] = "0"
    try:
        assert lc.LiveEngine(service=FakeService(), execute=Recorder()).ipv6 is False
    finally:
        del os.environ[lc.IPV6_ENV]
    assert lc.LiveEngine(service=FakeService(), execute=Recorder()).ipv6 is True, "on by default"


def test_poll_pages_and_reports_what_it_skipped():
    e = engine(results_max=20)
    for w in range(30):                       # 30 results made, only the last 20 kept
        e._results.append({"window": w, "predicted_class": "BENIGN"})
    e._windows = 30
    p = e.poll(-1)
    assert [r["window"] for r in p["results"]] == list(range(10, 30))
    assert p["skipped"] == 10 and p["queue_depth"] == 0
    p = e.poll(-1, limit=5)
    assert [r["window"] for r in p["results"]] == [10, 11, 12, 13, 14] and p["queue_depth"] == 15
    p = e.poll(12, limit=500)
    assert len(p["results"]) == 17 and p["skipped"] == 0, "limit is capped at 50, nothing skipped after 12"
    assert e.poll(29)["results"] == [] and e.poll(29)["skipped"] == 0
    p["results"][0]["predicted_class"] = "changed"
    assert e._results[13]["predicted_class"] == "BENIGN", "poll hands out copies"


def _write_pcap(path, frames):
    from scapy.layers.l2 import Ether
    from scapy.utils import wrpcap

    pkts = []
    for data, ts in frames:
        p = Ether(data)
        p.time = ts
        pkts.append(p)
    wrpcap(path, pkts)


def _wait(e, until, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        p = e.poll(-1)
        if until(p):
            return p
        time.sleep(0.05)
    raise AssertionError(f"timed out; last poll: { {k: v for k, v in p.items() if k != 'results'} }")


def test_replay_through_the_threads_detects_blocks_and_stops():
    rec = Recorder()
    e = lc.LiveEngine(service=FakeService(), execute=rec, ipv6=True, tick_s=0.25)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "scan.pcap")
        _write_pcap(path, browse_frames() + scan_frames(t0=1002.0))
        info = e.start(lc.PcapReplaySource(path, speed=4.0), "replay", [LAP], [GW])
        assert info["running"] is True
        p = _wait(e, lambda p: any(r["predicted_class"] == "PortScan" for r in p["results"]))
        scan = next(r for r in p["results"] if r["predicted_class"] == "PortScan")
        assert scan["source_ip"] == TAB and scan["execution"]["executed"] is True
        assert p["running"] is True and p["error"] is None and p["dropped"] == 0
        stopped = e.stop()
        assert stopped["running"] is False and stopped["results"] == []
        assert not [t for t in threading.enumerate() if t.name.startswith("live-")], "threads joined"
        # A new start begins a fresh numbering (the UI resets `after` to -1 on Start)
        e.start(lc.PcapReplaySource(path, speed=4.0), "replay", [LAP], [GW])
        p = _wait(e, lambda p: p["windows"] >= 1)
        assert p["results"][0]["window"] == 0
        e.stop()


def test_a_failing_prediction_does_not_stop_the_capture():
    e = lc.LiveEngine(service=FakeService(fail=True), execute=Recorder(), tick_s=0.25)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "scan.pcap")
        _write_pcap(path, scan_frames())
        e.start(lc.PcapReplaySource(path, speed=4.0), "replay", [LAP], [GW])
        p = _wait(e, lambda p: p["error"] is not None)
        assert "model exploded" in p["error"] and p["running"] is True
        e._service.fail = False                                    # the model recovers
        e._predicted_at_flow = -1                                  # (let the same window be retried)
        p = _wait(e, lambda p: p["windows"] >= 1)
        assert p["error"] is None, "the error clears once predictions work again"
        e.stop()


def test_start_refuses_before_the_model_is_loaded():
    class Closed:
        closed = False

        def close(self):
            Closed.closed = True

    svc = FakeService()
    svc.loaded = False
    e = lc.LiveEngine(service=svc, execute=Recorder())
    try:
        e.start(Closed(), "x")
        raise AssertionError("start() should refuse")
    except RuntimeError as err:
        assert "not loaded" in str(err)
    assert Closed.closed and e.poll()["running"] is False


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
