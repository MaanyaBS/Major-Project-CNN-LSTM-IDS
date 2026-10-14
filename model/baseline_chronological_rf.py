"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Random Forest Baseline on the Chronological Split
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
The earlier full-dataset baselines (baseline_full_dataset.py) used a
random 80/20 split, so they cannot be compared with the CNN-LSTM, which
is tested on a chronological split. This script trains the same random
forest (100 trees, seed 42) on exactly the CNN-LSTM's split, built by the
same code (rebuild_chronological_split.py), and scores it two ways:

    all test rows      every test flow, one prediction per flow
    window-aligned     the last flow of each CNN-LSTM test window, i.e.
                       the same 530,951 examples with the same labels the
                       CNN-LSTM is scored on (checked against y_test_seq.npy)

With --sequences-dir it also runs the CNN-LSTM on X_test_seq.npy, so both
models are compared per class on identical examples in one report.

Writes to --output-dir:
    chronological_random_forest_results.txt
    chronological_random_forest_results.json

Usage (Colab; about 30-45 minutes on the free CPU, mostly the forest):

    python model/baseline_chronological_rf.py \\
        --source /content/drive/MyDrive/Major_Project_Dataset/dataset/merged/cicids2017_cleaned_with_day.csv \\
        --label-mapping /content/drive/MyDrive/Major_Project_Dataset/output/label_mapping.csv \\
        --sequences-dir /content/drive/MyDrive/Major_Project_Dataset/verify_run_ruthwik \\
        --output-dir /content/drive/MyDrive/Major_Project_Dataset/verify_run_ruthwik/baseline_rf
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(MODEL_DIR)
sys.path.insert(0, MODEL_DIR)

from rebuild_chronological_split import (FEATURE_COLS, chronological_split,  # noqa: E402
                                         load_day_tagged, load_label_mapping)

SEQ_LEN = 10


def repo_path(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def window_end_rows(test_df, seq_len=SEQ_LEN):
    """Positions in test_df of the last row of each CNN-LSTM test window, in window order."""
    ends = [group.index[seq_len - 1:] for _, group in test_df.groupby('source_day', sort=False)
            if len(group) >= seq_len]
    return np.concatenate(ends)


def scores(y_true, y_pred, labels, names):
    from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

    _, _, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    # Averages over the classes present in y_true or y_pred (scikit-learn's default), as
    # evaluate_model.py does for the CNN-LSTM's reported 58.57% macro F1.
    return {
        "examples": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "per_class_f1": {n: float(f) for n, f in zip(names, f1)},
        "support": {n: int(s) for n, s in zip(names, support)},
    }


def format_report(results, args, rf_seconds, n_train):
    names = list(results["rf_all_rows"]["per_class_f1"])
    columns = [("rf_all_rows", "RF, all test rows"), ("rf_window_aligned", "RF, window-aligned")]
    if "cnn_lstm" in results:
        columns.append(("cnn_lstm", "CNN-LSTM, windows"))
    lines = [
        "=" * 78, "RANDOM FOREST ON THE CHRONOLOGICAL SPLIT (the CNN-LSTM's split)", "=" * 78,
        f"Generated  : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Source     : {args.source}",
        "Split      : rebuild_chronological_split.chronological_split (first 80% of each",
        "             (day, class) group trains, the rest tests), same code as the CNN-LSTM",
        f"Model      : RandomForestClassifier(n_estimators={args.n_estimators}, random_state=42);",
        f"             baseline_full_dataset.py used 100; {len(FEATURE_COLS)} features, unscaled",
        f"Training   : {n_train:,} rows in {rf_seconds:.0f} s",
    ]
    if results.get("alignment_check"):
        lines.append(f"Alignment  : {results['alignment_check']}")
    lines += ["", f"{'':<34}" + "".join(f"{title:>22}" for _, title in columns)]
    for key, label in (("examples", "examples"), ("accuracy", "accuracy"),
                       ("weighted_f1", "weighted F1"), ("macro_f1", "macro F1")):
        fmt = "{:>22,}" if key == "examples" else "{:>22.4f}"
        lines.append(f"  {label:<32}" + "".join(fmt.format(results[k][key]) for k, _ in columns))
    lines += ["", "PER-CLASS F1 (window-aligned: same examples, same labels for RF and CNN-LSTM)",
              f"  {'class':<32}{'support':>10}" + "".join(f"{title:>22}" for _, title in columns)]
    for n in names:
        sup = results["rf_window_aligned"]["support"][n]
        cells = [f"{results[k]['per_class_f1'][n]:>22.4f}" if results[k]["support"][n] else f"{'-':>22}"
                 for k, _ in columns]
        lines.append(f"  {n:<32}{sup:>10,}" + "".join(cells))
    lines += ["",
              "'-' = no test examples of that class in that column. Support is for the window-aligned",
              "examples; the all-rows column has a few more rows per class.",
              "'RF, all test rows' scores every test flow; 'window-aligned' scores only the last",
              "flow of each CNN-LSTM test window, so it differs from 'all rows' only by the few",
              "rows at the start of each day that no window ends on.",
              "For the earlier random-split numbers see full_dataset_random_forest_results.txt.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Random forest baseline on the CNN-LSTM's chronological split")
    parser.add_argument("--source", required=True, help="cicids2017_cleaned_with_day.csv")
    parser.add_argument("--label-mapping", required=True, help="label_mapping.csv (Attack -> Encoded)")
    parser.add_argument("--sequences-dir", help="Folder with X_test_seq.npy / y_test_seq.npy (recommended)")
    parser.add_argument("--model", default="model/artifacts/cnn_lstm_best_v2.keras")
    parser.add_argument("--output-dir", default="model/results")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=2048)
    args = parser.parse_args()

    from sklearn.ensemble import RandomForestClassifier

    print("[+] Loading and splitting...", flush=True)
    train_df, test_df = chronological_split(load_day_tagged(args.source))
    label_to_int = load_label_mapping(args.label_mapping)
    names = [n for n, _ in sorted(label_to_int.items(), key=lambda kv: kv[1])]
    labels = sorted(label_to_int.values())

    y_train = train_df['Label'].map(label_to_int)
    y_test = test_df['Label'].map(label_to_int)
    if y_train.isna().any() or y_test.isna().any():
        raise SystemExit(f"Unmapped labels: train={int(y_train.isna().sum())}, test={int(y_test.isna().sum())}")
    y_train, y_test = y_train.to_numpy(np.int64), y_test.to_numpy(np.int64)
    X_train = train_df[FEATURE_COLS].to_numpy(np.float32)
    X_test = test_df[FEATURE_COLS].to_numpy(np.float32)
    for name, X in (("train", X_train), ("test", X_test)):
        bad = int((~np.isfinite(X)).any(axis=1).sum())
        if bad:
            raise SystemExit(f"{bad:,} {name} rows hold NaN or infinite values; the CNN-LSTM split had none")
    print(f"[+] Train rows {len(X_train):,}, test rows {len(X_test):,}", flush=True)

    ends = window_end_rows(test_df)
    results = {}
    if args.sequences_dir:
        y_seq = np.load(os.path.join(args.sequences_dir, "y_test_seq.npy")).astype(np.int64)
        if len(y_seq) != len(ends) or not np.array_equal(y_seq, y_test[ends]):
            raise SystemExit(f"Split mismatch: {len(ends):,} window ends vs {len(y_seq):,} windows in y_test_seq.npy, "
                             "or their labels differ. This would not be the CNN-LSTM's split.")
        results["alignment_check"] = (f"passed - the {len(ends):,} window-end labels equal y_test_seq.npy "
                                      "exactly, so this is the CNN-LSTM's split")
        print(f"[+] {results['alignment_check']}", flush=True)

    print(f"[+] Training the random forest ({args.n_estimators} trees)...", flush=True)
    t0 = time.time()
    rf = RandomForestClassifier(n_estimators=args.n_estimators, n_jobs=-1, random_state=42)
    rf.fit(X_train, y_train)
    rf_seconds = time.time() - t0
    print(f"[+] Trained in {rf_seconds:.0f} s", flush=True)

    pred = rf.predict(X_test)
    results["rf_all_rows"] = scores(y_test, pred, labels, names)
    results["rf_window_aligned"] = scores(y_test[ends], pred[ends], labels, names)

    if args.sequences_dir:
        from tensorflow import keras

        model = keras.models.load_model(repo_path(args.model), compile=False)
        X_seq = np.load(os.path.join(args.sequences_dir, "X_test_seq.npy"))
        cnn_pred = model.predict(X_seq, batch_size=args.batch_size, verbose=0).argmax(axis=1)
        results["cnn_lstm"] = scores(y_seq, cnn_pred, labels, names)

    report = format_report(results, args, rf_seconds, len(X_train))
    out_dir = repo_path(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "chronological_random_forest_results.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(out_dir, "chronological_random_forest_results.json"), "w", encoding="utf-8") as f:
        json.dump({"train_rows": len(X_train), "rf_seconds": rf_seconds, **results}, f, indent=2)
    print(report)
    print(f"[+] Wrote chronological_random_forest_results.txt and .json to {out_dir}")


if __name__ == "__main__":
    main()
