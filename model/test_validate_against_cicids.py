"""
Tests for model/validate_against_cicids.py on a synthetic capture and a CSV
written the way UNB's TrafficLabelling files are (leading spaces in column
names, local time, afternoon hours without AM/PM, minute resolution).

Run:  python model/test_validate_against_cicids.py
"""

import os
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flow_features as ff  # noqa: E402
import validate_against_cicids as v  # noqa: E402

ATT, VIC, WEB = "172.16.0.1", "192.168.10.50", "192.168.10.3"
T0 = datetime(2017, 7, 7, 17, 1, 0, tzinfo=timezone.utc).timestamp()   # 14:01 in New Brunswick (UTC-3)


def _frames():
    from scapy.layers.inet import IP, TCP
    from scapy.layers.l2 import Ether

    E = lambda: Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
    out = []
    for i in range(30):                                       # scan: SYN -> RST/ACK
        t = T0 + i * 1.5
        out += [(E() / IP(src=ATT, dst=VIC) / TCP(sport=40000 + i, dport=20 + i, flags="S",
                                                  options=[("MSS", 1460)]), t),
                (E() / IP(src=VIC, dst=ATT) / TCP(sport=20 + i, dport=40000 + i, flags="RA"), t + 0.0001)]
    for i in range(10):                                       # web: request, response, FIN
        t = T0 + 2 + i * 3
        out += [(E() / IP(src=WEB, dst=VIC) / TCP(sport=50000 + i, dport=80, flags="PA") / (b"g" * 300), t),
                (E() / IP(src=VIC, dst=WEB) / TCP(sport=80, dport=50000 + i, flags="PA") / (b"r" * 900), t + 0.01),
                (E() / IP(src=WEB, dst=VIC) / TCP(sport=50000 + i, dport=80, flags="FA"), t + 0.02)]
    for k in range(2):                                        # same 5-tuple twice in one minute
        t = T0 + 50 + k * 2
        out += [(E() / IP(src=ATT, dst=VIC) / TCP(sport=41000, dport=443, flags="S"), t),
                (E() / IP(src=VIC, dst=ATT) / TCP(sport=443, dport=41000, flags="RA"), t + 0.0001)]
    for t in (T0 + 10, T0 + 80):                              # one port pair scanned again a minute later:
        out += [(E() / IP(src=ATT, dst=VIC) / TCP(sport=42000, dport=8080, flags="S"), t),   # 2 flows only if
                (E() / IP(src=VIC, dst=ATT) / TCP(sport=8080, dport=42000, flags="RA"), t + 0.0001)]  # RST ends one
    early = T0 - 90                                           # starts before the slice
    out += [(E() / IP(src=WEB, dst=VIC) / TCP(sport=51000, dport=80, flags="PA") / (b"e" * 50), early),
            (E() / IP(src=WEB, dst=VIC) / TCP(sport=51000, dport=80, flags="FA"), T0 + 5)]
    frames = []
    for p, t in sorted(out, key=lambda x: x[1]):
        p.time = t
        frames.append(p)
    return frames


def _official_csv(path, flows, perturb=5):
    """CIC-style CSV from flows: leading-space columns, 'M/D/YYYY h:mm' local time, no AM/PM."""
    import pandas as pd

    rows = []
    for n, f in enumerate(flows):
        local = datetime.fromtimestamp(f.start, timezone.utc) - timedelta(hours=3)
        feats = f.features()
        if n < perturb:
            feats["Flow IAT Max"] *= 1.5
        rows.append({"Flow ID": "x", "Source IP": f.src, "Source Port": f.sport, "Destination IP": f.dst,
                     "Destination Port": f.dport, "Protocol": f.proto,
                     "Timestamp": f"{local.month}/{local.day}/{local.year} {local.hour % 12 or 12}:{local.minute:02d}",
                     "Flow Duration": f.duration_us, "Total Fwd Packets": len(f.fwd),
                     "Total Backward Packets": len(f.bwd), **feats,
                     "Label": "PortScan" if f.src == ATT else "BENIGN"})
    rows.append({**rows[-1], "Timestamp": "7/7/2017 1:30", "Source Port": 999})   # outside the slice
    df = pd.DataFrame(rows)
    df.columns = [" " + c if c != "Flow ID" else c for c in df.columns]
    df.to_csv(path, index=False)
    return df


def test_end_to_end_on_a_synthetic_day():
    from scapy.utils import wrpcap

    with tempfile.TemporaryDirectory() as tmp:
        pcap, csv, zpath, out = (os.path.join(tmp, n) for n in ("day.pcap", "PortScan.csv", "flows.zip", "r.md"))
        frames = _frames()
        wrpcap(pcap, frames)
        truth = [f for f in ff.flows_from_packets(ff.iter_packets(pcap), end_on_rst=True) if f.start >= T0 - 60]
        _official_csv(csv, truth)
        with zipfile.ZipFile(zpath, "w") as z:
            z.write(csv, "TrafficLabelling /Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv")
            z.write(csv, "TrafficLabelling /Monday-WorkingHours.pcap_ISCX.csv")
        results, best = v.run(pcap, zpath, "2017-07-07 17:00", 5, out, sample=1000)
        report = open(out, encoding="utf-8").read()

    r = results[True]
    assert r["offset"] == -3, f"time-zone offset {r['offset']}"
    assert best is True, "the CSV was built with end_on_rst=True"
    assert len(r["rows"]) == len(truth), "the row outside the slice is not counted"
    assert len(r["pairs"]) == len(truth) - 2, "the two same-minute flows on one 5-tuple are left out"
    assert r["dropped"] == 2
    iat = r["cmp"]["Flow IAT Max"]["agree"]
    assert (~iat).sum() == 5, "the five perturbed rows disagree on Flow IAT Max"
    others = [c for c in ff.FEATURE_COLS if c != "Flow IAT Max"]
    assert all(r["cmp"][c]["agree"].all() for c in others), "every other feature agrees exactly"
    assert abs(r["all_ok"].mean() - (len(r["pairs"]) - 5) / len(r["pairs"])) < 1e-12
    assert "UTC-3" in report and "Flow IAT Max" in report and "PortScan" in report


def test_timestamp_readings():
    cands, formats, orders = v.parse_timestamps(["7/7/2017 1:55", "07/07/2017 13:55:20", "7/7/2017 2:01 PM", "junk"])
    assert {c[0].hour for c in cands[0]} == {1, 13} and cands[0][0][1] == 60, "no AM/PM: both readings, minute"
    assert [c[0].hour for c in cands[1]] == [13] and cands[1][0][1] == 1, "24-hour with seconds"
    assert [c[0].hour for c in cands[2]] == [14], "PM honoured"
    assert cands[3] == [] and formats["unparsed"] == 1
    _, _, orders = v.parse_timestamps(["25/7/2017 9:00"])
    assert orders == ["dm"], "a day above 12 settles the date order"


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except BaseException as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
