"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Random Forest vs CNN-LSTM on MU-IoT (run in Colab)
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Tests the project's argument for a sequence model on MU-IoT: that single
flow records are ambiguous where 20-flow windows are not. A random forest
(100 trees, seed 42, as in the CICIDS2017 baseline) is trained on every
single training row, then scored on the last row of each CNN-LSTM test
window: the same examples and labels the CNN-LSTM is scored on. The
CNN-LSTM is re-scored in the same run, on both test tracks:

    test_within    later traffic from recordings used in training
    test_heldout   four whole recordings never seen in training

and on two subsets of each: all windows, and only windows whose exact
20-row sequence never appears in training (the headline subset in
model/results/mu_iot/mu_iot_unseen_only_rescore.txt).

Checks written into the report: the CNN-LSTM must reproduce its committed
scores (mu_iot_metrics.json), and the unseen-only window counts must match
the committed re-score.

Writes to --output-dir:
    mu_iot_random_forest_results.txt
    mu_iot_random_forest_results.json

Usage (Colab; about 20-30 minutes, mostly the forest):

    python model/baseline_mu_iot_rf.py \\
        --data-dir /content/drive/MyDrive/Major_Project/handoff_v3 \\
        --output-dir /content/drive/MyDrive/Major_Project_Dataset/mu_iot/runs/results
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import numpy as np

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(MODEL_DIR)
sys.path.insert(0, MODEL_DIR)

from train_cnn_lstm_mu_iot import (SPLITS, build_windows, load_package,  # noqa: E402
                                   predict_probs, split_view, stage_data, validate_package)

SEQ_LEN = 20
TRACKS = ("test_within", "test_heldout")
COMMITTED_METRICS = "model/results/mu_iot/mu_iot_metrics.json"
COMMITTED_RESCORE = "model/results/mu_iot/mu_iot_unseen_only_rescore.txt"


def repo_path(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def row_hashes(X, chunk=500_000):
    """A 64-bit hash of every feature row (identical rows hash identically)."""
    import pandas as pd

    out = np.empty(len(X), dtype=np.uint64)
    for i in range(0, len(X), chunk):
        block = pd.DataFrame(np.asarray(X[i:i + chunk]))
        out[i:i + chunk] = pd.util.hash_pandas_object(block, index=False).to_numpy()
    return out


def window_hashes(rh, starts):
    """Combine the row hashes of each window in order (uint64 arithmetic wraps by design)."""
    acc = np.zeros(len(starts), dtype=np.uint64)
    prime = np.uint64(1_000_003)
    for j in range(SEQ_LEN):
        acc = acc * prime + rh[starts + j]
    return acc


def scores(y, pred, names, normal_id, sessions=None):
    """Averages over the classes present in y, as evaluate_track() in train_cnn_lstm_mu_iot.py does."""
    from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

    present = sorted(np.unique(y).tolist())
    _, _, f1, _ = precision_recall_fscore_support(y, pred, labels=present, zero_division=0)
    out = {
        "windows": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "weighted_f1": float(f1_score(y, pred, labels=present, average="weighted", zero_division=0)),
        "macro_f1": float(f1_score(y, pred, labels=present, average="macro", zero_division=0)),
        "per_class_f1": {names[c]: float(f) for c, f in zip(present, f1)},
    }
    if normal_id in present:
        out["normal_false_alarm_rate"] = float((pred[y == normal_id] != normal_id).mean())
    if (y != normal_id).any():
        out["attack_called_normal_rate"] = float((pred[y != normal_id] == normal_id).mean())
    if sessions is not None:
        out["per_session_accuracy"] = {str(s): float((pred[sessions == s] == y[sessions == s]).mean())
                                       for s in np.unique(sessions)}
    return out


def committed_checks(results):
    """Compare the CNN-LSTM's scores here with the committed MU-IoT results."""
    lines = []
    with open(repo_path(COMMITTED_METRICS)) as f:
        committed = json.load(f)
    with open(repo_path(COMMITTED_RESCORE)) as f:
        rescore = f.read()
    for track in TRACKS:
        if track not in results:
            continue
        mine, ref = results[track]["all"]["cnn_lstm"], committed[track]
        ok = abs(mine["accuracy"] - ref["accuracy"]) < 5e-4 and abs(mine["macro_f1"] - ref["macro_f1"]) < 5e-4
        lines.append(f"{track}: CNN-LSTM accuracy {mine['accuracy']:.4f} / macro F1 {mine['macro_f1']:.4f} vs committed "
                     f"{ref['accuracy']:.4f} / {ref['macro_f1']:.4f} - {'matches' if ok else 'DIFFERS'}")
        m = re.search(rf"{track}\s+all windows.*?\n\s+unseen only\s+n=\s*([\d,]+)", rescore)
        if m:
            n_ref = int(m.group(1).replace(",", ""))
            n_mine = results[track]["unseen"]["cnn_lstm"]["windows"]
            lines.append(f"{track}: unseen-only windows {n_mine:,} vs committed {n_ref:,} - "
                         f"{'matches' if n_mine == n_ref else 'DIFFERS'}")
    return lines


def format_report(results, checks, meta_info):
    rows = [("windows", "windows", "{:>10,}"), ("accuracy", "accuracy", "{:>10.4f}"),
            ("weighted_f1", "weighted F1", "{:>10.4f}"), ("macro_f1", "macro F1", "{:>10.4f}"),
            ("normal_false_alarm_rate", "normal flagged as attack", "{:>10.4f}"),
            ("attack_called_normal_rate", "attacks called normal", "{:>10.4f}")]
    lines = ["=" * 78, "RANDOM FOREST (single rows) vs CNN-LSTM (20-row windows) ON MU-IoT", "=" * 78,
             f"Generated : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             f"Package   : {meta_info['data_dir']}",
             f"Forest    : RandomForestClassifier(n_estimators={meta_info['n_estimators']}, random_state=42), "
             f"{meta_info['train_rows']:,} training rows, {meta_info['rf_seconds']:.0f} s",
             "Examples  : the forest classifies the last row of each CNN-LSTM test window, so both",
             "            models are scored on identical examples with identical labels", "",
             "CHECKS"] + [f"  {c}" for c in checks] + [""]
    titles = {"test_within": "later traffic from recordings used in training",
              "test_heldout": "four whole recordings never seen in training"}
    for track, r in results.items():
        lines += ["-" * 78, f"{track.upper()}: {titles[track]}", "-" * 78,
                  f"  {'':<28}{'all windows':^22}{'unseen-only windows':^24}",
                  f"  {'':<28}{'RF':>10}{'CNN-LSTM':>12}{'RF':>12}{'CNN-LSTM':>12}"]
        for key, label, fmt in rows:
            if key not in r["all"]["rf"]:
                continue
            vals = [r[sub][mdl][key] for sub in ("all", "unseen") for mdl in ("rf", "cnn_lstm")]
            lines.append(f"  {label:<28}" + fmt.format(vals[0]) + fmt.format(vals[1]).rjust(12)
                         + fmt.format(vals[2]).rjust(12) + fmt.format(vals[3]).rjust(12))
        lines += ["", f"  {'per-class F1 (all windows)':<28}{'RF':>10}{'CNN-LSTM':>12}"]
        for name, f_rf in r["all"]["rf"]["per_class_f1"].items():
            lines.append(f"  {name:<28}{f_rf:>10.4f}{r['all']['cnn_lstm']['per_class_f1'][name]:>12.4f}")
        if "per_session_accuracy" in r["all"]["rf"]:
            lines += ["", f"  {'per-recording accuracy':<28}{'RF':>10}{'CNN-LSTM':>12}   class"]
            for sess, acc_rf in r["all"]["rf"]["per_session_accuracy"].items():
                acc_cnn = r["all"]["cnn_lstm"]["per_session_accuracy"][sess]
                lines.append(f"  {sess:<28}{acc_rf:>10.4f}{acc_cnn:>12.4f}   {r['session_class'][sess]}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Random forest vs CNN-LSTM on MU-IoT, on identical examples")
    parser.add_argument("--data-dir", required=True, help="MU-IoT package folder (on Drive)")
    parser.add_argument("--local-dir", default="/content/mu_iot_data")
    parser.add_argument("--model", default="model/artifacts/mu_iot/best.keras")
    parser.add_argument("--output-dir", default="model/results/mu_iot")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=2048)
    args = parser.parse_args()

    from sklearn.ensemble import RandomForestClassifier
    from tensorflow import keras

    pkg = load_package(stage_data(args.data_dir, args.local_dir))
    validate_package(pkg)
    X, meta = pkg["X"], pkg["meta"]
    names = [pkg["id_to_name"][i] for i in sorted(pkg["id_to_name"])]
    normal_id = pkg["name_to_id"]["normal"]
    windows, _ = build_windows(pkg, SEQ_LEN)

    train_rows = np.flatnonzero(meta["split"] == SPLITS["train"])
    X_train = np.asarray(X[train_rows], dtype=np.float32)
    y_train = meta["category_id"][train_rows].astype(np.int64)
    print(f"[+] Training the random forest on {len(train_rows):,} rows ({args.n_estimators} trees)...", flush=True)
    t0 = time.time()
    rf = RandomForestClassifier(n_estimators=args.n_estimators, n_jobs=-1, random_state=42)
    rf.fit(X_train, y_train)
    rf_seconds = time.time() - t0
    print(f"[+] Trained in {rf_seconds:.0f} s", flush=True)
    del X_train

    print("[+] Hashing windows for the unseen-only subset...", flush=True)
    rh = row_hashes(X)
    train_hashes = np.unique(window_hashes(rh, split_view(windows, "train")["starts"]))

    model = keras.models.load_model(repo_path(args.model), compile=False)
    results = {}
    for track in TRACKS:
        view = split_view(windows, track)
        if len(view["starts"]) == 0:
            continue
        y, sessions = view["labels"], view["session"]
        ends = view["starts"] + SEQ_LEN - 1
        pred_rf = rf.predict(np.asarray(X[ends], dtype=np.float32))
        pred_cnn = predict_probs(model, X, view["starts"], SEQ_LEN, args.batch_size).argmax(axis=1)
        unseen = ~np.isin(window_hashes(rh, view["starts"]), train_hashes)
        sess = sessions if track == "test_heldout" else None
        results[track] = {
            "all": {"rf": scores(y, pred_rf, names, normal_id, sess),
                    "cnn_lstm": scores(y, pred_cnn, names, normal_id, sess)},
            "unseen": {"rf": scores(y[unseen], pred_rf[unseen], names, normal_id),
                       "cnn_lstm": scores(y[unseen], pred_cnn[unseen], names, normal_id)},
            "session_class": {str(s): names[int(np.bincount(y[sessions == s]).argmax())] for s in np.unique(sessions)},
        }
        print(f"[+] {track}: {len(y):,} windows, {int(unseen.sum()):,} unseen", flush=True)

    checks = committed_checks(results)
    meta_info = {"data_dir": args.data_dir, "n_estimators": args.n_estimators,
                 "train_rows": int(len(train_rows)), "rf_seconds": rf_seconds}
    report = format_report(results, checks, meta_info)
    out_dir = repo_path(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "mu_iot_random_forest_results.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(out_dir, "mu_iot_random_forest_results.json"), "w", encoding="utf-8") as f:
        json.dump({**meta_info, "checks": checks, "results": results}, f, indent=2)
    print(report)
    print(f"[+] Wrote mu_iot_random_forest_results.txt and .json to {out_dir}")


if __name__ == "__main__":
    main()
