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


def test_fast_reader_matches_scapy_decoding():
    from scapy.layers.inet import IP, TCP, UDP
    from scapy.layers.inet6 import IPv6
    from scapy.layers.l2 import Dot1Q, Ether
    from scapy.utils import PcapNgWriter, PcapReader, wrpcap

    E = lambda **kw: Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02", **kw)   # no MAC lookups
    frames = [
        E() / IP(src=A, dst=B) / TCP(sport=40000, dport=443, flags="S", options=[("MSS", 1460)]),
        E() / IP(src=B, dst=A) / TCP(sport=443, dport=40000, flags="RA"),
        E() / IP(src=B, dst=A, options=b"\x01" * 4) / TCP(sport=443, dport=40000, flags="PA") / (b"y" * 300),
        E() / Dot1Q(vlan=5) / IP(src=A, dst=B) / UDP(sport=5353, dport=53) / (b"q" * 40),
        E() / IP(src=A, dst=B, frag=10) / (b"z" * 40),                 # later fragment: skipped
        E(type=0x0806) / (b"\x00" * 28),                              # ARP, not IP: skipped
        E() / IPv6() / TCP(),                                          # IPv6 TCP: read
        E() / IP(src=A, dst=B, proto=1) / (b"i" * 8),                  # ICMP: skipped
    ]
    for i, f in enumerate(frames):
        f.time = 1700000000 + i * 0.123457
    with tempfile.TemporaryDirectory() as tmp:
        for name, write in (("a.pcap", lambda p: wrpcap(p, frames)),
                            ("a.pcapng", lambda p: PcapNgWriter(p).write(frames))):
            path = os.path.join(tmp, name)
            write(path)
            with PcapReader(path) as r:
                slow = [p for p in (ff.packet_from_scapy(x) for x in r) if p is not None]
            fast = list(ff.iter_packets(path))
            assert fast == slow, f"{name}: fast reader differs from scapy decoding"
            assert len(fast) == 5, f"{name}: expected the 5 TCP/UDP packets, got {len(fast)}"
    raw_ip = bytes(IP(src=A, dst=B) / TCP(sport=1, dport=2, flags="S"))
    assert ff.packet_from_bytes(raw_ip, ff.LINKTYPE_RAW, 0.0).payload == 6, "raw-IP link type, padded to Ethernet minimum"


V6A, V6B = "2001:db8::66", "2001:db8::1"   # IPv6 documentation prefix


def test_ipv6_fast_reader_matches_scapy_decoding():
    from scapy.layers.inet import TCP, UDP
    from scapy.layers.inet6 import (ICMPv6EchoRequest, IPv6, IPv6ExtHdrDestOpt, IPv6ExtHdrFragment,
                                    IPv6ExtHdrHopByHop)
    from scapy.layers.l2 import Dot1Q, Ether
    from scapy.packet import Padding, Raw
    from scapy.utils import PcapNgWriter, PcapReader, wrpcap

    E = lambda **kw: Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02", **kw)
    frames = [
        E() / IPv6(src="2001:0db8:0:0:0:0:0:0066", dst=V6B)               # written long, read compressed
        / TCP(sport=40000, dport=443, flags="S", options=[("MSS", 1440)]),
        E() / IPv6(src=V6B, dst=V6A) / TCP(sport=443, dport=40000, flags="PA") / (b"y" * 1200),
        E() / IPv6(src=V6A, dst=V6B) / UDP(sport=50000, dport=443) / (b"q" * 1252),   # QUIC-like
        E() / IPv6(src=V6A, dst=V6B) / IPv6ExtHdrHopByHop() / IPv6ExtHdrDestOpt()
        / UDP(sport=5353, dport=53) / (b"d" * 50),                         # extension headers skipped over
        E() / Dot1Q(vlan=7) / IPv6(src=V6A, dst=V6B) / TCP(sport=1, dport=22, flags="A") / (b"v" * 10),
        E() / IPv6(src=V6A, dst=V6B) / UDP(sport=7, dport=7) / (b"p" * 2) / Padding(b"\x00" * 12),  # trailer
        E() / IPv6(src=V6A, dst=V6B) / IPv6ExtHdrFragment(offset=0, m=1, id=9)
        / UDP(sport=9, dport=9) / (b"f" * 64),                             # first fragment: read
        E() / IPv6(src=V6A, dst=V6B) / IPv6ExtHdrFragment(offset=8, id=9, nh=17) / Raw(b"f" * 64),  # later: skipped
        E() / IPv6(src=V6A, dst=V6B) / ICMPv6EchoRequest(),                  # ICMPv6: skipped
        E() / IPv6(src=V6A, dst=V6B, nh=50) / Raw(b"\x00" * 40),             # ESP (encrypted): skipped
    ]
    for i, f in enumerate(frames):
        f.time = 1700000000 + i * 0.25
    with tempfile.TemporaryDirectory() as tmp:
        for name, write in (("v6.pcap", lambda p: wrpcap(p, frames)),
                            ("v6.pcapng", lambda p: PcapNgWriter(p).write(frames))):
            path = os.path.join(tmp, name)
            write(path)
            with PcapReader(path) as r:
                slow = [p for p in (ff.packet_from_scapy(x) for x in r) if p is not None]
            fast = list(ff.iter_packets(path))
            assert fast == slow, f"{name}: fast reader differs from scapy decoding:\n{fast}\n{slow}"
            assert [p.payload for p in fast] == [0, 1200, 1252, 50, 10, 2, 64], [p.payload for p in fast]
            assert fast[0].src == V6A and fast[0].flags == 0x02
            assert list(ff.iter_packets(path, ipv6=False)) == [], "ipv6=False reads IPv4 only"


def test_ipv6_other_link_types_and_ah():
    from scapy.layers.inet import TCP
    from scapy.layers.inet6 import IPv6

    tcp = bytes(TCP(sport=1234, dport=80, flags="PA") / (b"h" * 30))
    ip6 = bytes(IPv6(src=V6A, dst=V6B) / TCP(sport=1234, dport=80, flags="PA") / (b"h" * 30))
    for linktype in (ff.LINKTYPE_RAW, ff.LINKTYPE_IPV6):
        p = ff.packet_from_bytes(ip6, linktype, 0.0)
        assert (p.src, p.dport, p.payload) == (V6A, 80, 30), linktype
    for family in (23, 24, 28, 30):                                  # loopback, per OS
        for order in ("little", "big"):
            p = ff.packet_from_bytes(family.to_bytes(4, order) + ip6, ff.LINKTYPE_NULL, 0.0)
            assert p is not None and p.payload == 30, (family, order)
    assert ff.packet_from_bytes((99).to_bytes(4, "little") + ip6, ff.LINKTYPE_NULL, 0.0) is None
    # Authentication Header (24 bytes: length field 24/4 - 2 = 4) in front of TCP
    ah = bytes([ff.TCP, 4, 0, 0]) + b"\x00" * 20
    hdr = bytearray(ip6[:40])
    hdr[4:6], hdr[6] = (len(ah) + len(tcp)).to_bytes(2, "big"), ff.IPV6_AH
    p = ff.packet_from_bytes(bytes(hdr) + ah + tcp, ff.LINKTYPE_RAW, 0.0)
    assert (p.sport, p.dport, p.payload) == (1234, 80, 30), "AH skipped over"
    assert ff.packet_from_bytes(ip6[:30], ff.LINKTYPE_RAW, 0.0) is None, "truncated IPv6 header"


def test_ipv6_and_ipv4_flows_from_one_capture():
    from scapy.layers.inet import IP, TCP, UDP
    from scapy.layers.inet6 import IPv6
    from scapy.layers.l2 import Ether
    from scapy.utils import wrpcap

    E = lambda: Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
    pkts = [E() / IP(src=A, dst=B) / TCP(sport=50000, dport=22, flags="S"),
            E() / IP(src=B, dst=A) / TCP(sport=22, dport=50000, flags="RA"),
            E() / IPv6(src=V6A, dst=V6B) / UDP(sport=50001, dport=443) / (b"q" * 1200),
            E() / IPv6(src=V6B, dst=V6A) / UDP(sport=443, dport=50001) / (b"r" * 300)]
    for i, p in enumerate(pkts):
        p.time = i * 0.01
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mixed.pcap")
        wrpcap(path, pkts)
        both = ff.flows_from_pcap(path, end_on_rst=True)
        v4 = ff.flows_from_pcap(path, end_on_rst=True, ipv6=False)
    assert len(both) == 2 and len(v4) == 1
    quic = both[both["Source IP"] == V6A].iloc[0]
    assert (quic["Destination Port"], quic["Total Length of Fwd Packets"], quic["Total Length of Bwd Packets"]) \
        == (443, 1200, 300)
    assert v4.iloc[0]["Source IP"] == A


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
