"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Packet -> Flow -> CICIDS2017 Feature Extractor
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Turns packets (a live interface or a Wireshark .pcap/.pcapng) into
bidirectional flows and computes the 20 features the CNN-LSTM was trained
on, with the same definitions CICFlowMeter-V3 used to build CICIDS2017.

The definitions below were checked against 400,000 rows of the CICIDS2017
CSVs, including CICFlowMeter-V3's quirks, which the model learned and so
must be reproduced:
  - "Packet Length Mean/Std/Variance" count the flow's FIRST packet twice;
    "Average Packet Size" = (sum of lengths + first length) / packets.
  - Every standard deviation is the sample std (n-1); one value gives 0.
  - Subflow values equal the flow totals (one subflow per flow).
  - Lengths are transport payload bytes INCLUDING Ethernet padding: an
    nmap SYN (44-byte IP packet) counts 2 bytes, a bare RST/ACK 6 bytes.
    CICIDS2017 was captured on wired Ethernet; Wi-Fi frames carry no such
    padding, so pad_to_ethernet=True pads every packet to Ethernet's 60-byte
    minimum frame, as if captured there.
  - Times are microseconds.

Flow termination follows CICFlowMeter-V3: a flow ends at its first FIN
packet (included), or when a packet arrives more than 120 s after the flow
started (the 120 s "flow timeout"). There is no idle termination: V3's 5 s
"activity timeout" only feeds the Active/Idle statistics, which are not among
the 20 features. Whether V3 also ended flows on RST is not certain, so
end_on_rst is a parameter (default False until the CICIDS validation,
model/validate_against_cicids.py, decides).

Live capture (flows_from_packets(..., live_flow_timeout_s=...), used by the
backend's live engine) checks the flow timeout every second from flow start
and ends flows on RST: a scan flow (SYN -> RST/ACK) has the same feature
values whether it ends at the RST or at the timeout, so scans are reported
within seconds while long benign flows still end on FIN or the timeout.

IPv4 and IPv6 are both read (ipv6=False reads IPv4 only). On a phone hotspot
most traffic is IPv6, much of it QUIC (UDP 443), so leaving it out would hide
most of what the model is asked to judge. IPv6 lengths are the transport
payload after any extension headers, exactly as for IPv4; the 20 features
contain no addresses. An IPv6 packet is never shorter than Ethernet's minimum,
so padding never changes it. How well the 2017-trained model judges IPv6 and
QUIC traffic is measured on real captures, not assumed.

Usage:
    python model/flow_features.py capture.pcapng -o flows.csv
The CSV has the 20 feature columns plus "Source IP" and can be uploaded to
the dashboard like any other flow CSV.
"""

import argparse
import math
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_chronological_split import FEATURE_COLS  # noqa: E402

TCP, UDP = 6, 17
FIN, RST = 0x01, 0x04
ACTIVE_TIMEOUT_S = 120.0
ETHERNET_MIN_IP_BYTES = 46          # 60-byte minimum frame - 14-byte Ethernet header
INFO_COLS = ["Source IP", "Source Port", "Destination IP", "Protocol", "Flow Start", "Flow End", "Packets"]

# IPv6 extension headers that can sit between the IPv6 header and TCP/UDP.
# Hop-by-hop, routing, destination options, mobility, HIP, shim6: next header
# in byte 0, length in byte 1 as 8-byte units after the first 8 bytes.
IPV6_EXT_HEADERS = {0, 43, 60, 135, 139, 140}
IPV6_FRAGMENT, IPV6_AH = 44, 51     # fixed 8 bytes / length in 4-byte units minus 2


@dataclass(frozen=True)
class Packet:
    """The fields of one IPv4 or IPv6 TCP/UDP packet that flow features need."""
    ts: float          # seconds
    src: str
    dst: str
    sport: int
    dport: int
    proto: int         # 6 TCP, 17 UDP
    payload: int       # transport payload bytes (incl. Ethernet padding when padded)
    flags: int = 0     # TCP flags


def packet_from_scapy(pkt, pad_to_ethernet=True, ipv6=True):
    """scapy packet -> Packet, or None for anything that is not IPv4/IPv6 TCP/UDP."""
    from scapy.layers.inet import IP, TCP as STCP, UDP as SUDP

    if IP not in pkt:
        return _ipv6_from_scapy(pkt, pad_to_ethernet) if ipv6 else None
    ip = pkt[IP]
    if ip.frag:                                   # later fragments carry no ports
        return None
    ip_len = ip.len if ip.len else len(bytes(ip))
    if pad_to_ethernet:
        ip_len = max(ip_len, ETHERNET_MIN_IP_BYTES)
    if STCP in ip:
        l4 = ip[STCP]
        header, flags = (l4.dataofs or 5) * 4, int(l4.flags)
    elif SUDP in ip:
        l4, header, flags = ip[SUDP], 8, 0
    else:
        return None
    payload = max(0, ip_len - ip.ihl * 4 - header)
    return Packet(float(pkt.time), ip.src, ip.dst, int(l4.sport), int(l4.dport),
                  TCP if STCP in ip else UDP, payload, flags)


def _ipv6_from_scapy(pkt, pad_to_ethernet):
    from scapy.layers.inet import TCP as STCP, UDP as SUDP
    from scapy.layers.inet6 import IPv6, IPv6ExtHdrFragment

    if IPv6 not in pkt:
        return None
    ip6 = pkt[IPv6]
    frag = ip6.getlayer(IPv6ExtHdrFragment)
    if frag is not None and frag.offset:          # later fragments carry no ports
        return None
    if STCP in ip6:
        l4 = ip6[STCP]
        header, flags = (l4.dataofs or 5) * 4, int(l4.flags)
    elif SUDP in ip6:
        l4, header, flags = ip6[SUDP], 8, 0
    else:
        return None
    raw = bytes(ip6)                              # may also hold an Ethernet trailer
    l4_offset = len(raw) - len(bytes(l4))         # 40 + extension headers
    ip_len = 40 + ip6.plen if ip6.plen else len(raw)
    if pad_to_ethernet:
        ip_len = max(ip_len, ETHERNET_MIN_IP_BYTES)
    payload = max(0, ip_len - l4_offset - header)
    return Packet(float(pkt.time), ip6.src, ip6.dst, int(l4.sport), int(l4.dport),
                  TCP if STCP in ip6 else UDP, payload, flags)


# Fast path: read only the IP and TCP/UDP headers straight from the bytes.
# About 30x faster than full scapy decoding (which also decodes TLS, DNS,
# ...); gives identical Packet values (checked in the tests).
LINKTYPE_NULL, LINKTYPE_ETHERNET, LINKTYPE_RAW, LINKTYPE_LINUX_SLL = 0, 1, 101, 113
LINKTYPE_IPV4, LINKTYPE_IPV6 = 228, 229
ETHERTYPES_IP = (b"\x08\x00", b"\x86\xdd")
# Loopback (NULL) captures store the address family in the capturing host's
# byte order: AF_INET is 2 everywhere, AF_INET6 is 23 on Windows (Npcap),
# 24 on NetBSD/OpenBSD, 28 on FreeBSD, 30 on macOS.
NULL_FAMILIES_IP = {2, 23, 24, 28, 30}


def _ip_offset(data, linktype):
    """Byte offset of the IP header in a captured frame, or None if not IP."""
    if linktype == LINKTYPE_ETHERNET:
        off, ethertype = 14, data[12:14]
        while ethertype in (b"\x81\x00", b"\x88\xa8") and len(data) >= off + 4:   # VLAN tags
            ethertype, off = data[off + 2:off + 4], off + 4
        return off if ethertype in ETHERTYPES_IP else None
    if linktype in (LINKTYPE_RAW, LINKTYPE_IPV4, LINKTYPE_IPV6):
        return 0
    if linktype == LINKTYPE_LINUX_SLL:
        return 16 if data[14:16] in ETHERTYPES_IP else None
    if linktype == LINKTYPE_NULL:                 # BSD/Npcap loopback: 4-byte address family
        family = data[:4]
        if (int.from_bytes(family, "little") in NULL_FAMILIES_IP
                or int.from_bytes(family, "big") in NULL_FAMILIES_IP):
            return 4
    return None


def _ipv6_transport(ip):
    """IPv6 packet bytes -> (offset of its TCP/UDP header, protocol), or None."""
    nh, off = ip[6], 40
    while nh not in (TCP, UDP):
        if len(ip) < off + 8:
            return None
        if nh in IPV6_EXT_HEADERS:
            nh, off = ip[off], off + (ip[off + 1] + 1) * 8
        elif nh == IPV6_FRAGMENT:
            if int.from_bytes(ip[off + 2:off + 4], "big") & 0xFFF8:   # later fragments carry no ports
                return None
            nh, off = ip[off], off + 8
        elif nh == IPV6_AH:
            nh, off = ip[off], off + (ip[off + 1] + 2) * 4
        else:                                     # ESP (encrypted), ICMPv6, no next header, ...
            return None
    return off, nh


def _packet_from_ipv6(ip, ts, pad_to_ethernet):
    if len(ip) < 40:
        return None
    found = _ipv6_transport(ip)
    if found is None:
        return None
    off, proto = found
    l4 = ip[off:]
    if proto == TCP and len(l4) >= 14:
        header, flags = ((l4[12] >> 4) or 5) * 4, l4[13]
    elif proto == UDP and len(l4) >= 8:
        header, flags = 8, 0
    else:
        return None
    plen = int.from_bytes(ip[4:6], "big")
    ip_len = 40 + plen if plen else len(ip)       # 0 = jumbogram: no Ethernet trailer possible
    if pad_to_ethernet:
        ip_len = max(ip_len, ETHERNET_MIN_IP_BYTES)
    return Packet(ts, socket.inet_ntop(socket.AF_INET6, ip[8:24]),
                  socket.inet_ntop(socket.AF_INET6, ip[24:40]),
                  int.from_bytes(l4[0:2], "big"), int.from_bytes(l4[2:4], "big"), proto,
                  max(0, ip_len - off - header), flags)


def packet_from_bytes(data, linktype, ts, pad_to_ethernet=True, ipv6=True):
    """Captured frame bytes -> Packet, or None for anything that is not IPv4/IPv6 TCP/UDP."""
    off = _ip_offset(data, linktype)
    if off is None or len(data) < off + 20:
        return None
    ip = data[off:]
    if ip[0] >> 4 == 6:
        return _packet_from_ipv6(ip, ts, pad_to_ethernet) if ipv6 else None
    if ip[0] >> 4 != 4:
        return None
    ihl = (ip[0] & 0x0F) * 4
    if int.from_bytes(ip[6:8], "big") & 0x1FFF:   # later fragments carry no ports
        return None
    proto = ip[9]
    l4 = ip[ihl:]
    if proto == TCP and len(l4) >= 14:
        header, flags = ((l4[12] >> 4) or 5) * 4, l4[13]
    elif proto == UDP and len(l4) >= 8:
        header, flags = 8, 0
    else:
        return None
    ip_len = int.from_bytes(ip[2:4], "big") or len(ip)
    if pad_to_ethernet:
        ip_len = max(ip_len, ETHERNET_MIN_IP_BYTES)
    return Packet(ts, ".".join(map(str, ip[12:16])), ".".join(map(str, ip[16:20])),
                  int.from_bytes(l4[0:2], "big"), int.from_bytes(l4[2:4], "big"), proto,
                  max(0, ip_len - ihl - header), flags)


def _sample_std(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))


class Flow:
    """One bidirectional flow; forward = the direction of its first packet."""

    __slots__ = ("src", "dst", "sport", "dport", "proto", "start", "last",
                 "fwd", "bwd", "fwd_us", "all_us", "first_len")

    def __init__(self, p):
        self.src, self.dst, self.sport, self.dport, self.proto = p.src, p.dst, p.sport, p.dport, p.proto
        self.start = self.last = p.ts
        self.fwd, self.bwd, self.fwd_us, self.all_us = [], [], [], []
        self.first_len = p.payload
        self.add(p)

    def add(self, p):
        # Whole microseconds, as CICFlowMeter-V3 timestamps packets. Epoch
        # seconds as a float resolve only ~0.24 us, so a 100 us gap would
        # otherwise come out as 99.9 us; rounding restores the captured value.
        us = round(p.ts * 1_000_000)
        if p.src == self.src and p.sport == self.sport:
            self.fwd.append(p.payload)
            self.fwd_us.append(us)
        else:
            self.bwd.append(p.payload)
        self.all_us.append(us)
        self.last = p.ts

    @property
    def duration_us(self):
        return self.all_us[-1] - self.all_us[0]

    def features(self):
        fwd, bwd = self.fwd, self.bwd
        lengths = fwd + bwd
        doubled = [self.first_len] + lengths       # CICFlowMeter-V3 counts the first packet twice
        flow_iat = [b - a for a, b in zip(self.all_us, self.all_us[1:])]
        fwd_iat = [b - a for a, b in zip(self.fwd_us, self.fwd_us[1:])]
        pl_std = _sample_std(doubled)
        fwd_mean = sum(fwd) / len(fwd)
        bwd_mean = sum(bwd) / len(bwd) if bwd else 0.0
        values = {
            "Destination Port": self.dport,
            "Total Length of Fwd Packets": sum(fwd),
            "Total Length of Bwd Packets": sum(bwd),
            "Fwd Packet Length Max": max(fwd),
            "Fwd Packet Length Mean": fwd_mean,
            "Bwd Packet Length Max": max(bwd) if bwd else 0,
            "Bwd Packet Length Mean": bwd_mean,
            "Bwd Packet Length Std": _sample_std(bwd),
            "Flow IAT Max": max(flow_iat) if flow_iat else 0.0,
            "Fwd IAT Std": _sample_std(fwd_iat),
            "Max Packet Length": max(lengths),
            "Packet Length Mean": sum(doubled) / len(doubled),
            "Packet Length Std": pl_std,
            "Packet Length Variance": pl_std ** 2,
            "Average Packet Size": sum(doubled) / len(lengths),
            "Avg Fwd Segment Size": fwd_mean,
            "Avg Bwd Segment Size": bwd_mean,
            "Subflow Fwd Packets": len(fwd),
            "Subflow Fwd Bytes": sum(fwd),
            "Subflow Bwd Bytes": sum(bwd),
        }
        assert list(values) == FEATURE_COLS
        return values

    def info(self):
        return {"Source IP": self.src, "Source Port": self.sport, "Destination IP": self.dst,
                "Protocol": self.proto, "Flow Start": self.start, "Flow End": self.last,
                "Packets": len(self.all_us)}


class FlowTable:
    """
    Groups packets into flows. add() and expire() return the flows that just
    ended, in the order they ended - the order the model's windows use.
    """

    def __init__(self, active_timeout_s=ACTIVE_TIMEOUT_S, end_on_rst=False):
        self.active_timeout_s = active_timeout_s
        self.end_on_rst = end_on_rst
        self.flows = {}

    @staticmethod
    def _key(p):
        a, b = (p.src, p.sport), (p.dst, p.dport)
        return (a, b, p.proto) if a <= b else (b, a, p.proto)

    def add(self, p):
        ended = []
        key = self._key(p)
        flow = self.flows.get(key)
        if flow is not None and p.ts - flow.start > self.active_timeout_s:
            ended.append(self.flows.pop(key))
            flow = None
        if flow is None:
            # CICFlowMeter-V3 checks FIN only on a flow that already exists: a
            # flow whose FIRST packet carries FIN (the tail of an earlier
            # connection's teardown) stays open, and the reply joins it.
            self.flows[key] = Flow(p)
            return ended
        flow.add(p)
        if p.proto == TCP and (p.flags & FIN or (self.end_on_rst and p.flags & RST)):
            ended.append(self.flows.pop(key))
        return ended

    def tick(self, now):
        """Live mode: end flows that started more than active_timeout_s ago."""
        done = [k for k, f in self.flows.items() if now - f.start > self.active_timeout_s]
        return sorted((self.flows.pop(k) for k in done), key=lambda f: f.last)

    def flush(self):
        """End every remaining flow (end of a capture file)."""
        done = sorted(self.flows.values(), key=lambda f: f.last)
        self.flows.clear()
        return done


def flows_to_frame(flows):
    import pandas as pd

    rows = [{**f.features(), **f.info()} for f in flows]
    return pd.DataFrame(rows, columns=FEATURE_COLS + INFO_COLS)


def flows_from_packets(packets, end_on_rst=False, live_flow_timeout_s=None, tick_s=1.0):
    """
    Packet iterable (time-ordered) -> list of ended flows, in end order.

    Default: CICFlowMeter-V3 file behaviour (FIN, optional RST, 120 s flow
    timeout checked when the flow's next packet arrives, rest at the end).
    live_flow_timeout_s: replays the live engine instead - the flow timeout
    is checked every tick_s seconds of capture time, from flow start.
    """
    live = live_flow_timeout_s is not None
    table = FlowTable(active_timeout_s=live_flow_timeout_s if live else ACTIVE_TIMEOUT_S,
                      end_on_rst=end_on_rst)
    ended, next_tick = [], None
    for p in packets:
        if live:
            if next_tick is None:
                next_tick = p.ts + tick_s
            while p.ts >= next_tick:
                ended += table.tick(next_tick)
                next_tick += tick_s
        ended += table.add(p)
    return ended + table.flush()


def iter_packets(path, pad_to_ethernet=True, max_packets=None, ipv6=True):
    """
    Wireshark .pcap/.pcapng -> Packet stream (IPv4 and IPv6 TCP/UDP), read lazily
    from the raw bytes (fast path). Timestamps are an exact integer count of
    ticks divided once, i.e. correctly rounded - the same value scapy's
    PcapReader computes with Decimal, without its per-packet cost.
    """
    from scapy.utils import RawPcapReader

    with RawPcapReader(str(path)) as reader:
        for i, (data, meta) in enumerate(reader):
            if max_packets is not None and i >= max_packets:
                break
            if hasattr(meta, "tsresol"):                       # pcapng
                linktype = meta.linktype
                ts = ((meta.tshigh << 32) + meta.tslow) / int(meta.tsresol)
            else:                                              # pcap
                linktype = reader.linktype
                scale = 10 ** 9 if reader.nano else 10 ** 6
                ts = (meta.sec * scale + meta.usec) / scale
            p = packet_from_bytes(data, linktype, ts, pad_to_ethernet, ipv6)
            if p is not None:
                yield p


def flows_from_pcap(path, pad_to_ethernet=True, end_on_rst=False, live_flow_timeout_s=None, max_packets=None,
                    ipv6=True):
    """Wireshark .pcap/.pcapng -> DataFrame of flows (20 features + flow info)."""
    packets = iter_packets(path, pad_to_ethernet, max_packets, ipv6)
    return flows_to_frame(flows_from_packets(packets, end_on_rst, live_flow_timeout_s))


def main():
    parser = argparse.ArgumentParser(description="Wireshark capture -> CICIDS2017-style flow CSV")
    parser.add_argument("pcap", help=".pcap or .pcapng file")
    parser.add_argument("-o", "--output", help="CSV to write (default: <pcap>.flows.csv)")
    parser.add_argument("--no-ethernet-padding", action="store_true",
                        help="use the captured lengths as they are (not recommended for Wi-Fi captures)")
    parser.add_argument("--end-on-rst", action="store_true", help="also end TCP flows at the first RST")
    parser.add_argument("--ipv4-only", action="store_true", help="skip IPv6 packets")
    args = parser.parse_args()

    df = flows_from_pcap(args.pcap, pad_to_ethernet=not args.no_ethernet_padding, end_on_rst=args.end_on_rst,
                         ipv6=not args.ipv4_only)
    out = Path(args.output or f"{args.pcap}.flows.csv")
    df.to_csv(out, index=False)
    print(f"{len(df):,} flows -> {out}  ({len(df) // 10} model windows of 10 flows)")


if __name__ == "__main__":
    main()
