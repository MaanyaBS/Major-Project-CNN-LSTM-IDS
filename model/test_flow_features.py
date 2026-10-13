"""
Tests for model/flow_features.py: packets -> flows -> the 20 CICIDS2017 features.

Run:  python model/test_flow_features.py

Expected values come from CICIDS2017 rows and the CICFlowMeter-V3 rules
that were checked against 400,000 of them (see flow_features.py).
"""

import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flow_features as ff  # noqa: E402

A, B = "192.0.2.66", "192.0.2.1"     # attacker / victim


def pkt(ts, src, dst, sport, dport, payload=0, flags=0, proto=ff.TCP):
    return ff.Packet(ts, src, dst, sport, dport, proto, payload, flags)


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


def one_flow(packets, **kw):
    flows = ff.flows_from_packets(packets, **kw)
    assert len(flows) == 1, f"expected 1 flow, got {len(flows)}"
    return flows[0].features()


def test_cicids_row_two_padded_acks():
    # A real CICIDS2017 row: 2 forward packets of 6 bytes (padded bare ACKs), nothing back.
    f = one_flow([pkt(0.0, A, B, 54865, 80, 6), pkt(0.000003, A, B, 54865, 80, 6)])
    assert f["Total Length of Fwd Packets"] == 12 and f["Subflow Fwd Packets"] == 2
    assert f["Packet Length Mean"] == 6.0 and f["Packet Length Std"] == 0.0
    assert f["Average Packet Size"] == 9.0, "first packet must be counted twice: (12 + 6) / 2"
    assert close(f["Flow IAT Max"], 3.0), "IATs are in microseconds"


def test_first_packet_counted_twice_and_sample_std():
    f = one_flow([pkt(0.0, A, B, 1000, 80, 10), pkt(0.001, A, B, 1000, 80, 4)])
    vals = [10, 10, 4]                                   # first packet doubled
    mean = sum(vals) / 3
    std = math.sqrt(sum((v - mean) ** 2 for v in vals) / 2)
    assert close(f["Packet Length Mean"], mean) and close(f["Packet Length Std"], std)
    assert close(f["Packet Length Variance"], std ** 2)
    assert close(f["Average Packet Size"], 24 / 2)
    assert close(f["Fwd Packet Length Mean"], 7.0) and f["Fwd Packet Length Max"] == 10
    assert close(f["Avg Fwd Segment Size"], 7.0)


def test_direction_and_backward_stats():
    f = one_flow([pkt(0.0, A, B, 1000, 22, 0),           # forward = initiator
                  pkt(0.0001, B, A, 22, 1000, 30),
                  pkt(0.0002, B, A, 22, 1000, 10)])
    assert f["Destination Port"] == 22
    assert f["Total Length of Bwd Packets"] == 40 and f["Bwd Packet Length Max"] == 30
    assert close(f["Bwd Packet Length Mean"], 20.0) and close(f["Bwd Packet Length Std"], math.sqrt(200))
    assert f["Subflow Bwd Bytes"] == 40 and f["Max Packet Length"] == 30


def test_fwd_iat_std_is_sample_std_in_microseconds():
    f = one_flow([pkt(0.0, A, B, 1000, 80), pkt(0.000100, A, B, 1000, 80), pkt(0.000400, A, B, 1000, 80)])
    assert close(f["Fwd IAT Std"], abs(300 - 100) / math.sqrt(2), 1e-6)
    assert close(f["Flow IAT Max"], 300, 1e-6)
    two = one_flow([pkt(0.0, A, B, 1000, 80), pkt(0.5, A, B, 1000, 80)])
    assert two["Fwd IAT Std"] == 0.0, "a single interval has no spread"


def test_fin_ends_the_flow_and_later_packets_start_a_new_one():
    flows = ff.flows_from_packets([pkt(0.0, A, B, 1000, 80, 0), pkt(0.1, A, B, 1000, 80, 0, ff.FIN),
                                   pkt(0.2, B, A, 80, 1000, 0)])
    assert len(flows) == 2
    assert flows[1].features()["Destination Port"] == 1000, "the leftover packet's own direction defines the new flow"


def test_rst_ends_the_flow_only_when_enabled():
    scan = [pkt(0.0, A, B, 40000, 443, 2), pkt(0.00005, B, A, 443, 40000, 6, ff.RST)]
    after = scan + [pkt(0.0001, A, B, 40000, 443, 0)]          # a packet after the RST
    assert len(ff.flows_from_packets(after)) == 1, "end_on_rst=False: the RST does not end the flow"
    assert len(ff.flows_from_packets(after, end_on_rst=True)) == 2, "end_on_rst=True: it does"
    for rst in (False, True):                                   # a scan flow is the same either way
        f = one_flow(scan, end_on_rst=rst)
        assert (f["Total Length of Fwd Packets"], f["Total Length of Bwd Packets"]) == (2, 6)
        assert close(f["Flow IAT Max"], 50.0, 1e-6)


def test_fin_ends_the_flow_under_both_settings():
    pk = [pkt(0.0, A, B, 1000, 80), pkt(0.1, A, B, 1000, 80, 0, ff.FIN), pkt(0.2, A, B, 1000, 80)]
    for rst in (False, True):
        assert len(ff.flows_from_packets(pk, end_on_rst=rst)) == 2


def test_file_path_never_ends_flows_on_idle():
    # CICFlowMeter-V3 has no idle termination: 100 s of silence, still one flow.
    pk = [pkt(0.0, A, B, 1000, 443), pkt(100.0, A, B, 1000, 443), pkt(119.0, A, B, 1000, 443)]
    assert len(ff.flows_from_packets(pk)) == 1


def test_flow_timeout_is_measured_from_flow_start():
    # A busy flow still ends 120 s after it started (file behaviour).
    pk = [pkt(float(t), A, B, 1000, 80) for t in range(0, 130, 5)]   # 0 .. 125 s
    flows = ff.flows_from_packets(pk)
    assert len(flows) == 2 and flows[0].last <= 120.0


def test_live_tick_ends_flows_only_past_the_flow_timeout():
    other = [pkt(float(t), B, A, 9, 9) for t in range(0, 30)]   # keeps capture time moving
    pk = sorted([pkt(0.0, A, B, 1000, 80)] + other, key=lambda p: p.ts)
    ended = ff.flows_from_packets(pk, live_flow_timeout_s=10)
    first = next(f for f in ended if f.sport == 1000)
    assert ended.index(first) == 0, "ended by the tick at ~10 s, before the end-of-capture flush"
    table = ff.FlowTable(active_timeout_s=10)
    table.add(pkt(0.0, A, B, 1000, 80))
    assert table.tick(9.9) == [] and len(table.tick(10.1)) == 1


def test_flows_returned_in_end_order():
    table = ff.FlowTable(active_timeout_s=1)
    table.add(pkt(0.0, A, B, 1, 80))
    table.add(pkt(0.5, A, B, 2, 80))
    table.add(pkt(0.2, A, B, 1, 80))
    ended = table.tick(5.0)
    assert [f.sport for f in ended] == [1, 2], "sorted by last packet time"


def test_udp_flows():
    f = one_flow([pkt(0.0, A, B, 5353, 53, 30, proto=ff.UDP), pkt(0.01, B, A, 53, 5353, 90, proto=ff.UDP)])
    assert f["Destination Port"] == 53 and f["Total Length of Bwd Packets"] == 90


def test_scapy_lengths_include_ethernet_padding():
    from scapy.layers.inet import IP, TCP
    from scapy.layers.l2 import Ether

    syn = Ether() / IP(src=A, dst=B) / TCP(sport=40000, dport=443, flags="S", options=[("MSS", 1460)])
    rst = Ether() / IP(src=B, dst=A) / TCP(sport=443, dport=40000, flags="RA")
    data = Ether() / IP(src=A, dst=B) / TCP(sport=40000, dport=443, flags="PA") / (b"x" * 100)
    for p in (syn, rst, data):
        p.time = 0.0
    syn, rst, data = (ff.packet_from_scapy(Ether(bytes(p))) for p in (syn, rst, data))
    assert syn.payload == 2 and rst.payload == 6, "nmap SYN = 2, bare RST/ACK = 6, as in CICIDS2017 PortScan rows"
    assert data.payload == 100
    raw = ff.packet_from_scapy(Ether(bytes(Ether() / IP(src=B, dst=A) / TCP(flags="RA"))), pad_to_ethernet=False)
    assert raw.payload == 0
    assert ff.packet_from_scapy(Ether() / IP(src=A, dst=B, proto=1)) is None, "non TCP/UDP ignored"


def test_pcap_round_trip():
    from scapy.layers.inet import IP, TCP
    from scapy.layers.l2 import Ether
    from scapy.utils import wrpcap

    pkts = []
    for i, port in enumerate((22, 80, 443)):
        syn = Ether() / IP(src=A, dst=B) / TCP(sport=50000 + i, dport=port, flags="S", options=[("MSS", 1460)])
        rst = Ether() / IP(src=B, dst=A) / TCP(sport=port, dport=50000 + i, flags="RA")
        syn.time, rst.time = i * 0.01, i * 0.01 + 0.00005
        pkts += [syn, rst]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "scan.pcap")
        wrpcap(path, pkts)
        df = ff.flows_from_pcap(path)
    assert list(df.columns[:20]) == ff.FEATURE_COLS and "Source IP" in df.columns
    assert len(df) == 3 and set(df["Destination Port"]) == {22, 80, 443}
    assert (df["Source IP"] == A).all() and (df["Total Length of Bwd Packets"] == 6).all()
    assert (df["Flow IAT Max"].round(3) == 50.0).all()


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
