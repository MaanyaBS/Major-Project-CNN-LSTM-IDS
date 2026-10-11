"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Demo CSV Builder (CICIDS2017 test traffic)
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Builds demo/demo_cicids_test.csv: real CICIDS2017 test-set traffic (never
seen in training) arranged so one upload to the dashboard shows the whole
chain - detection, explanation, recommendation, a real firewall action on a
TEST-NET address, "already blocked", human review, and a refused real
address.

Each 10-row block is one model window (the backend cuts uploads into
non-overlapping 10-row windows). A block is taken only if:
  - all 10 rows are consecutive flows from one capture day,
  - all 10 rows carry the block's class (except a class whose flows never fill
    a window - Bot - where the window with the most such flows is used),
  - the model predicts that class, above the policy threshold where the
    block is meant to trigger an automatic action.

Rows are recovered from the scaled test windows with scaler_v2.pkl, and the
script then re-runs the backend's own path (pandas -> scaler -> model) on the
written CSV to confirm every window gives the planned result.

Usage (repository root, CPU is fine, about a minute):
    python model/build_demo_csv.py
Writes demo/demo_cicids_test.csv and demo/demo_cicids_test_expected.txt.
"""

import argparse
import os
import pickle
import sys
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "model"))
from class_action_mapping import CLASS_ACTION_MAP, get_action  # noqa: E402
from rebuild_chronological_split import FEATURE_COLS  # noqa: E402

SEQ = 10
# (class, windows, source IP, what the demo shows)
PLAN = [
    ("BENIGN", 5, "192.0.2.10", "normal traffic: no action"),
    ("PortScan", 3, "192.0.2.66", "automatic block_ip; repeats show 'already blocked'"),
    ("BENIGN", 3, "192.0.2.10", "normal traffic: no action"),
    ("DDoS", 3, "198.51.100.20", "automatic block_ip; repeats show 'already blocked'"),
    ("DoS Hulk", 2, "203.0.113.7", "automatic rate_limit: removed after 120 s"),
    ("DoS slowloris", 1, "203.0.113.9", "automatic drop_connection: removed after 60 s"),
    ("Bot", 1, "192.0.2.88", "held for human review (Bot never acts automatically)"),
    ("PortScan", 1, "8.8.8.8", "refused: real address outside the demo scope"),
    ("BENIGN", 3, "192.0.2.10", "normal traffic: no action"),
]


def contiguous(X, start, n_windows):
    """Windows start .. start+(n_windows-1)*SEQ cover one unbroken run of rows (same day)."""
    last = start + (n_windows - 1) * SEQ
    if start < SEQ - 1 or last >= len(X):
        return False
    for j in range(start - (SEQ - 1), last):
        if not np.array_equal(X[j][1:], X[j + 1][:-1]):
            return False
    return True


def row_labels(y, w):
    """True labels of the 10 rows of window w (row k is the last row of window k-9)."""
    return y[w - (SEQ - 1): w + 1]


def main():
    parser = argparse.ArgumentParser(description="Build the dashboard demo CSV from CICIDS2017 test windows")
    parser.add_argument("--sequences-dir", default=str(REPO / "datasets" / "verify_run_ruthwik"))
    parser.add_argument("--out-dir", default=str(REPO / "demo"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    from tensorflow import keras

    X = np.load(Path(args.sequences_dir) / "X_test_seq.npy", mmap_mode="r")
    y = np.load(Path(args.sequences_dir) / "y_test_seq.npy")
    with open(REPO / "model" / "artifacts" / "scaler_v2.pkl", "rb") as f:
        scaler = pickle.load(f)
    import json
    with open(REPO / "model" / "artifacts" / "label_mapping_v2.json") as f:
        name_to_id = json.load(f)
    id_to_name = {v: k for k, v in name_to_id.items()}
    model = keras.models.load_model(REPO / "model" / "artifacts" / "cnn_lstm_best_v2.keras", compile=False)

    print("Scoring the test windows...", flush=True)
    probs = model.predict(X, batch_size=4096, verbose=0)
    pred, conf = probs.argmax(1), probs.max(1)

    rng = np.random.default_rng(args.seed)
    used = set()
    blocks = []
    for cls, n, ip, note in PLAN:
        c = name_to_id[cls]
        policy = CLASS_ACTION_MAP[cls]
        auto = policy["action"] != "no_action" and not policy.get("never_auto_fire")
        min_conf = policy["threshold"] if auto else 0.0

        def ok(w):
            return (SEQ - 1 <= w < len(y) and w not in used and pred[w] == c
                    and conf[w] >= min_conf and (row_labels(y, w) == c).all())

        w = next((int(w) for w in rng.permutation(np.flatnonzero(pred == c))
                  if all(ok(w + i * SEQ) for i in range(n)) and contiguous(X, w, n)), None)
        if w is None and n == 1:
            # Some classes (Bot) never fill a whole window: their flows are scattered
            # among benign flows. Fall back to a window the evaluation labels as this
            # class (its last row) and the model predicts as it, with the most rows of it.
            pool = [int(v) for v in np.flatnonzero((pred == c) & (y == c))
                    if v not in used and conf[v] >= min_conf and contiguous(X, int(v), 1)]
            if pool:
                w = max(pool, key=lambda v: int((row_labels(y, v) == c).sum()))
                note += f" - only {int((row_labels(y, w) == c).sum())} of its 10 flows are {cls}, the rest BENIGN"
        if w is None:
            sys.exit(f"No suitable block found for {cls} x{n}")
        wins = [w + i * SEQ for i in range(n)]
        used.update(range(w - SEQ, wins[-1] + SEQ))   # keep blocks apart
        blocks.append((cls, ip, note, wins))
        print(f"  {cls:<14} x{n}  test windows {wins}  confidence {[round(float(conf[v]), 3) for v in wins]}")

    rows = []
    for cls, ip, note, wins in blocks:
        for v in wins:
            raw = scaler.inverse_transform(pd.DataFrame(np.asarray(X[v], dtype=np.float64), columns=FEATURE_COLS))
            for r, lab in zip(raw, row_labels(y, v)):
                rows.append([*r, ip, id_to_name[int(lab)]])
    df = pd.DataFrame(rows, columns=FEATURE_COLS + ["Source IP", "Label"])
    for col in FEATURE_COLS:   # integer-valued columns written as integers, like the original files
        vals = df[col].to_numpy()
        if np.allclose(vals, np.round(vals), atol=1e-3):
            df[col] = np.round(vals).astype(np.int64)
        else:
            df[col] = np.round(vals, 6)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "demo_cicids_test.csv"
    df.to_csv(csv_path, index=False)

    # Verify on the written file, the way the backend reads it.
    back = pd.read_csv(csv_path)
    Xs = scaler.transform(back[FEATURE_COLS]).astype("float32").reshape(-1, SEQ, len(FEATURE_COLS))
    p2 = model.predict(Xs, verbose=0)
    lines = ["Demo CSV: " + csv_path.name,
             f"{len(back)} rows = {len(Xs)} windows of {SEQ} rows. Source: CICIDS2017 chronological test set",
             "(never seen in training). Label = each flow's true class, for the presenter; the model ignores it.", "",
             f"{'win':>3}  {'rows':<9}  {'true class':<14} {'predicted':<14} {'conf':>6}  {'source IP':<14} {'policy':<17} expected"]
    i, failures = 0, 0
    for cls, ip, note, wins in blocks:
        for _ in wins:
            k = int(p2[i].argmax()); name = id_to_name[k]; cf = float(p2[i].max())
            act = get_action(name, cf)
            planned = name == cls and (act["status"] == "auto_action") == (
                CLASS_ACTION_MAP[cls]["action"] != "no_action" and not CLASS_ACTION_MAP[cls].get("never_auto_fire"))
            failures += not planned
            lines.append(f"{i:>3}  {i*SEQ+2:>4}-{i*SEQ+11:<4}  {cls:<14} {name:<14} {cf:>6.3f}  {ip:<14} "
                         f"{act['status']:<17} {note}{'' if planned else '   <-- NOT AS PLANNED'}")
            i += 1
    lines += ["", "rows = line numbers in the CSV (line 1 is the header).",
              "Firewall actions need the backend running as administrator with",
              "IDS_PREVENTION_EXECUTION_ENABLED=1; otherwise every action stays 'recommended'.",
              "", "ALL WINDOWS AS PLANNED" if not failures else f"{failures} WINDOW(S) NOT AS PLANNED"]
    (out_dir / "demo_cicids_test_expected.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
