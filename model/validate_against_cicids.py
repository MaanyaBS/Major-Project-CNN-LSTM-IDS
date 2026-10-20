"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Extractor Check Against the Original CICIDS2017 Flows
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Does model/flow_features.py compute what CICFlowMeter-V3 computed for the
training data? The same packets (UNB's original Friday-WorkingHours.pcap) go
through our extractor, and each of our flows is compared, feature by feature,
with the official row for that flow in UNB's GeneratedLabelledFlows CSV
("TrafficLabelling": it keeps Flow ID, addresses, ports and Timestamp, which
the cleaned training CSVs dropped). Run in Colab: the pcap is about 8 GB.
Neither file is committed (UNB's terms; size).

Matching
- A row matches one of our flows when the 5-tuple is equal in the same
  direction and our flow starts inside the row's timestamp: to the minute in
  these files (to the second if seconds are present).
- The CSV timestamp is local time, and afternoon times are written in 12-hour
  form without AM/PM, so both readings of the hour are tried. The time-zone
  offset is not assumed: every whole-hour offset is tried on a sample of rows
  and the one with the most matches is used (expected: UTC-3, New Brunswick
  summer time).
- nmap reuses source ports and CICIDS2017 ran many scans, so a row with two
  candidate flows in its minute, or a flow claimed by two rows, is left out:
  only one-to-one matches are compared. The match rate is reported.
- Our extractor reads from MARGIN_S before the slice to MARGIN_S after it, so
  flows that start inside the slice are complete; only those are compared.

Values are compared twice: strictly (within 1e-4 relative) and at the
precision the CSV printed. The official CSV writes large values with three
significant digits ("1.02E+07"), so a strictly correct 10,154,600 cannot
equal its row; the main figures use the printed precision, the strict ones
are shown next to them.

Both end_on_rst settings are run (CICFlowMeter-V3's handling of RST is not
documented); the report shows which agrees better.

Usage:
  python model/validate_against_cicids.py --pcap Friday-WorkingHours.pcap \\
      --csv GeneratedLabelledFlows.zip --start "2017-07-07 17:00" --minutes 10 \\
      --out model/results/extractor_validation.md
--csv takes the CSV itself or the zip (the PortScan CSV is picked from it).
--start is UTC; 17:00 UTC is 14:00 in New Brunswick, inside the PortScan
period of the Friday afternoon.
"""

import argparse
import io
import re
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_features as ff  # noqa: E402

FEATURES = ff.FEATURE_COLS
DIAGNOSTIC = ["Total Fwd Packets", "Total Backward Packets", "Flow Duration"]
MARGIN_S = ff.ACTIVE_TIMEOUT_S + 10
TS_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?\s*$")
UTC = timezone.utc


# ---------- inputs ----------

def read_official(path, pattern="PortScan"):
    """The official flow CSV (or the one matching `pattern` inside a zip), column names stripped."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv") and pattern.lower() in n.lower()]
            if len(names) != 1:
                raise SystemExit(f"Expected one CSV matching '{pattern}' in {path.name}, found {names}")
            print(f"  using {names[0]} from {path.name}")
            raw = z.read(names[0])
        df = pd.read_csv(io.BytesIO(raw), encoding="latin-1", dtype=str, skipinitialspace=True)
    else:
        df = pd.read_csv(path, encoding="latin-1", dtype=str, skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(subset=["Timestamp", "Source IP", "Source Port", "Destination Port"]).reset_index(drop=True)
    for c in ("Source Port", "Destination Port", "Protocol"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["Source Port", "Destination Port", "Protocol"]).reset_index(drop=True)


def parse_timestamps(values):
    """
    Raw Timestamp strings -> per row a list of (naive local datetime, resolution s),
    plus a report of the formats seen. Ambiguities are kept as several candidates.
    """
    parsed, formats = [], Counter()
    first_gt12 = second_gt12 = False
    matches = [TS_RE.match(str(v)) for v in values]
    for m in matches:
        if m:
            first_gt12 |= int(m.group(1)) > 12
            second_gt12 |= int(m.group(2)) > 12
    orders = ["md"] if second_gt12 and not first_gt12 else ["dm"] if first_gt12 and not second_gt12 else ["md", "dm"]
    for m in matches:
        if not m:
            parsed.append([])
            formats["unparsed"] += 1
            continue
        a, b, year, hh, mm, ss, ampm = m.groups()
        a, b, year, hh, mm = int(a), int(b), int(year), int(hh), int(mm)
        res = 1 if ss is not None else 60
        if ampm:
            hours = [hh % 12 + (12 if ampm.lower() == "pm" else 0)]
        else:
            hours = [hh, hh + 12] if hh < 12 else [hh]
            hours += [0] if hh == 12 else []
        formats[("seconds" if ss else "minutes") + (", AM/PM" if ampm else ", no AM/PM")] += 1
        cands = set()
        for order in orders:
            month, day = (a, b) if order == "md" else (b, a)
            if not (1 <= month <= 12 and 1 <= day <= 31):
                continue
            for h in hours:
                try:
                    cands.add((datetime(year, month, day, h, mm, int(ss or 0)), res))
                except ValueError:
                    pass
        parsed.append(sorted(cands))
    return parsed, formats, orders


def read_slice(pcap, start, end, report_every=1_000_000):
    """Packets from start - MARGIN_S to end + MARGIN_S (UTC epoch seconds), read once."""
    t0, t1 = start - MARGIN_S, end + MARGIN_S
    kept, seen, began = [], 0, time.time()
    for p in ff.iter_packets(pcap):
        seen += 1
        if seen % report_every == 0:
            print(f"  {seen:,} packets read ({time.time() - began:.0f} s), at "
                  f"{datetime.fromtimestamp(p.ts, UTC):%H:%M:%S} UTC, {len(kept):,} kept")
        if p.ts < t0:
            continue
        if p.ts > t1:
            break
        kept.append(p)
    print(f"  {seen:,} packets read, {len(kept):,} in the slice with margins")
    return kept


def our_flows(packets, start, end, end_on_rst):
    rows = []
    for f in ff.flows_from_packets(packets, end_on_rst=end_on_rst):
        if start <= f.start < end:
            rows.append({**f.features(), **f.info(), "Total Fwd Packets": len(f.fwd),
                         "Total Backward Packets": len(f.bwd), "Flow Duration": f.duration_us})
    return pd.DataFrame(rows)


# ---------- matching ----------

def _keys(df, reverse=False):
    s, d = ("Destination", "Source") if reverse else ("Source", "Destination")
    return list(zip(df[f"{s} IP"].astype(str), df[f"{s} Port"].astype(int), df[f"{d} IP"].astype(str),
                    df[f"{d} Port"].astype(int), df["Protocol"].astype(int)))


def match(ours, official, cands, offset_h, rows=None, reverse=False):
    """One-to-one (official row, our flow) pairs for one time-zone offset."""
    index = defaultdict(list)
    for i, (k, t) in enumerate(zip(_keys(ours), ours["Flow Start"])):
        index[k].append((t, i))
    keys = _keys(official, reverse)
    shift = timedelta(hours=offset_h)
    pairs, ambiguous = [], 0
    for j in (range(len(official)) if rows is None else rows):
        hits = set()
        flows = index.get(keys[j])
        if not flows:
            continue
        for local, res in cands[j]:
            t = (local - shift).replace(tzinfo=UTC).timestamp()
            hits.update(i for start, i in flows if t <= start < t + res)
        if len(hits) == 1:
            pairs.append((j, hits.pop()))
        elif hits:
            ambiguous += 1
    claimed = Counter(i for _, i in pairs)
    unique = [(j, i) for j, i in pairs if claimed[i] == 1]
    return unique, ambiguous + (len(pairs) - len(unique))


def find_offset(ours, official, cands, sample=30_000, seed=0):
    rows = np.random.default_rng(seed).permutation(len(official))[:sample]
    scores = {h: len(match(ours, official, cands, h, rows)[0]) for h in range(-12, 13)}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        raise SystemExit("No official row matched any of our flows at any time-zone offset: check that the CSV "
                         "belongs to the same day as the pcap and that --start falls inside it")
    return best, scores


def in_slice(official, cands, offset_h, start, end):
    """Official rows whose timestamp (any reading) falls inside the slice."""
    shift = timedelta(hours=offset_h)
    keep = []
    for j, cs in enumerate(cands):
        if any(start - res < (local - shift).replace(tzinfo=UTC).timestamp() < end for local, res in cs):
            keep.append(j)
    return keep


# ---------- comparison ----------

NUMBER_RE = re.compile(r"^[-+]?\d*(?:\.(\d*))?(?:[eE]([-+]?\d+))?$")


def printed_tolerance(text):
    """Half a unit in the last digit the CSV printed: '1.02E+07' -> 50000, '516.25' -> 0.005, '52' -> 0.5."""
    m = NUMBER_RE.match(str(text).strip())
    if not m:
        return 0.0
    return 0.5 * 10.0 ** (int(m.group(2) or 0) - len(m.group(1) or ""))

def compare(ours, official, pairs):
    a = ours.iloc[[i for _, i in pairs]]
    b = official.iloc[[j for j, _ in pairs]]
    out = {}
    for col in FEATURES + DIAGNOSTIC:
        x = a[col].to_numpy(float)
        y = pd.to_numeric(b[col], errors="coerce").to_numpy(float)
        diff = np.abs(x - y)
        strict = diff <= np.maximum(1e-6, 1e-4 * np.abs(y))
        printed = np.array([printed_tolerance(t) for t in b[col]]) * (1 + 1e-9)
        ok = strict | (diff <= printed)
        rel = diff / np.maximum(np.abs(y), 1e-9)
        out[col] = {"agree": ok, "strict": strict, "diff": diff, "rel": rel, "ours": x, "theirs": y,
                    "printed": b[col].astype(str).str.strip().to_numpy()}
    return a.reset_index(drop=True), b.reset_index(drop=True), out


def run(pcap, csv, start_text, minutes, out_path, sample):
    start = datetime.strptime(start_text, "%Y-%m-%d %H:%M").replace(tzinfo=UTC).timestamp()
    end = start + minutes * 60
    print("Reading the official flows ...")
    official = read_official(csv)
    cands, formats, orders = parse_timestamps(official["Timestamp"])
    print(f"  {len(official):,} rows; timestamp formats {dict(formats)}; date order tried {orders}")
    print("Reading the pcap slice ...")
    packets = read_slice(pcap, start, end)
    if not packets:
        raise SystemExit("No packets in the slice: check --start (UTC) against the pcap's times")

    results = {}
    for rst in (False, True):
        print(f"Extracting flows (end_on_rst={rst}) ...")
        ours = our_flows(packets, start, end, rst)
        offset, scores = find_offset(ours, official, cands, sample)
        rows = in_slice(official, cands, offset, start, end)
        pairs, dropped = match(ours, official, cands, offset, rows)
        matched_rows = {j for j, _ in pairs}
        reverse_only = len(match(ours, official, cands, offset, [j for j in rows if j not in matched_rows],
                                 reverse=True)[0])
        a, b, cmp_ = compare(ours, official, pairs)
        all_ok = np.all([cmp_[c]["agree"] for c in FEATURES], axis=0) if pairs else np.array([])
        all_strict = np.all([cmp_[c]["strict"] for c in FEATURES], axis=0) if pairs else np.array([])
        results[rst] = dict(ours=ours, offset=offset, scores=scores, rows=rows, pairs=pairs, dropped=dropped,
                            reverse_only=reverse_only, a=a, b=b, cmp=cmp_, all_ok=all_ok, all_strict=all_strict)
        print(f"  {len(ours):,} flows; offset UTC{offset:+d}; {len(rows):,} official rows in the slice; "
              f"{len(pairs):,} matched one-to-one; all 20 features agree on {all_ok.mean():.1%} "
              f"({all_strict.mean():.1%} strictly)")

    best = max(results, key=lambda r: (results[r]["all_ok"].mean() if len(results[r]["all_ok"]) else 0,
                                       len(results[r]["pairs"])))
    report = write_report(results, best, pcap, csv, start, end, formats, orders)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(report, encoding="utf-8")
    print(f"\nReport -> {out_path}\n")
    print(report)
    return results, best


def _git_rev():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def write_report(results, best, pcap, csv, start, end, formats, orders):
    r = results[best]
    a, b, cmp_, pairs = r["a"], r["b"], r["cmp"], r["pairs"]
    labels = b["Label"].astype(str).str.strip() if "Label" in b else pd.Series(["?"] * len(b))
    fmt = lambda t: datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d %H:%M UTC")
    L = ["# Extractor Check Against the Original CICIDS2017 Flows", "",
         f"Our extractor (`model/flow_features.py`, commit {_git_rev()}) on UNB's original packets, "
         f"compared flow by flow with CICFlowMeter-V3's official rows.", "",
         "| | |", "|---|---|",
         f"| Packets | `{Path(pcap).name}`, flows starting {fmt(start)} to {fmt(end)} |",
         f"| Official rows | `{Path(csv).name}` (TrafficLabelling) |",
         f"| Timestamp formats seen | {', '.join(f'{k}: {v:,}' for k, v in formats.items())} (date order tried: {', '.join(orders)}) |",
         f"| Time-zone offset found | UTC{r['offset']:+d} (most matches of all whole-hour offsets) |", "",
         "## Matching", "",
         "| end_on_rst | Our flows | Official rows in slice | One-to-one matches | Left out (2+ candidates) "
         "| Matched only reversed | All 20 features agree (as printed) | Strictly |",
         "|---|---|---|---|---|---|---|---|"]
    for rst, x in results.items():
        n = len(x["pairs"])
        L.append(f"| {rst} | {len(x['ours']):,} | {len(x['rows']):,} | {n:,} ({n / max(1, len(x['rows'])):.1%}) "
                 f"| {x['dropped']:,} | {x['reverse_only']:,} | {x['all_ok'].mean():.2%} | {x['all_strict'].mean():.2%} |")
    L += ["", f"Details below use end_on_rst={best} (the better agreement).", "",
          "## Per Feature", "",
          "| Feature | Agree (as printed) | Strictly | Median abs. difference where they differ "
          "| Median rel. difference where they differ |",
          "|---|---|---|---|---|"]
    for col in FEATURES + DIAGNOSTIC:
        c = cmp_[col]
        bad = ~c["agree"]
        med_abs = f"{np.median(c['diff'][bad]):.6g}" if bad.any() else "-"
        med_rel = f"{np.median(c['rel'][bad]):.2%}" if bad.any() else "-"
        name = col + (" *(diagnostic, not a model feature)*" if col in DIAGNOSTIC else "")
        L.append(f"| {name} | {c['agree'].mean():.2%} | {c['strict'].mean():.2%} | {med_abs} | {med_rel} |")
    L += ["", "## By Official Label", "", "| Label | Matched flows | All 20 features agree |", "|---|---|---|"]
    for lab, idx in labels.groupby(labels).groups.items():
        L.append(f"| {lab} | {len(idx):,} | {r['all_ok'][list(idx)].mean():.2%} |")
    worst = sorted(FEATURES, key=lambda c: cmp_[c]["agree"].mean())[:3]
    L += ["", "## Examples of Disagreement (three least-agreeing features)", ""]
    for col in worst:
        bad = np.flatnonzero(~cmp_[col]["agree"])
        if not len(bad):
            continue
        order = bad[np.argsort(-cmp_[col]["rel"][bad])][:5]
        L += [f"**{col}**", "", "| Flow | Label | Ours | Official (as printed) | Fwd/Bwd packets (ours / official) |",
              "|---|---|---|---|---|"]
        for k in order:
            flow = f"{a.at[k, 'Source IP']}:{a.at[k, 'Source Port']} -> {a.at[k, 'Destination IP']}:{int(a.at[k, 'Destination Port'])}"
            L.append(f"| {flow} | {labels.iat[k]} | {cmp_[col]['ours'][k]:.6g} | {cmp_[col]['printed'][k]} "
                     f"| {int(a.at[k, 'Total Fwd Packets'])}/{int(a.at[k, 'Total Backward Packets'])} / "
                     f"{int(b.at[k, 'Total Fwd Packets'])}/{int(b.at[k, 'Total Backward Packets'])} |")
        L.append("")
    L += ["Agreement: equal at the precision the official CSV printed (it writes large values with three "
          "significant digits, e.g. 1.02E+07); 'Strictly': within 1e-4 relative (1e-6 absolute). "
          "Rows left out (2+ candidate flows in the same minute, mostly reused nmap source ports) are not "
          "evidence either way.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Compare flow_features.py with the official CICIDS2017 flows")
    ap.add_argument("--pcap", required=True, help="UNB Friday-WorkingHours.pcap")
    ap.add_argument("--csv", required=True, help="TrafficLabelling PortScan CSV, or GeneratedLabelledFlows.zip")
    ap.add_argument("--start", default="2017-07-07 17:00", help="slice start, UTC (default: inside PortScan)")
    ap.add_argument("--minutes", type=int, default=10)
    ap.add_argument("--sample", type=int, default=30_000, help="rows used to find the time-zone offset")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results" / "extractor_validation.md"))
    a = ap.parse_args()
    run(a.pcap, a.csv, a.start, a.minutes, a.out, a.sample)


if __name__ == "__main__":
    main()
