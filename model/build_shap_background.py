"""
Builds the SHAP background from REAL training windows.

GradientExplainer compares each explained window against a background
distribution. If that background is synthetic noise, every attribution reads as
"how far this window is from noise" instead of "how far this window is from
normal traffic". This script samples a small, class-balanced set of genuine
training windows and writes them to backend/shap_background.npy (~80 KB), which
is small enough to commit and version alongside the model.

Why class-balanced: the training set is ~98% BENIGN. A uniform random sample of
100 windows would be almost entirely BENIGN, so the reference population would
essentially lack attack traffic and attack-window explanations would be
meaningless. A few windows per class keeps every class represented.

Writes scaled windows, i.e. the same post-StandardScaler space the model is fed,
which is what the explainer's background must be.

Usage
-----
    python model/build_shap_background.py \
        --sequences-dir datasets/verify_run_ruthwik \
        --out backend/shap_background.npy

Requires X_train_seq.npy and y_train_seq.npy from rebuild_chronological_split.py.
Those arrays are not in git (datasets/ is gitignored), so run this where the
dataset pipeline has been run - locally after rebuilding, or in Colab - and
commit the resulting .npy.
"""

import argparse
import json
import os
import sys

import numpy as np

DEFAULT_OUT = os.path.join("backend", "shap_background.npy")


def sample_background(X, y, total=100, per_class_cap=4, seed=42):
    """
    Picks `per_class_cap` windows per class (or fewer if a class has fewer),
    then tops up to `total` from the classes with the most remaining windows.

    Deterministic: same inputs and seed give the same background file.
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y).reshape(-1)

    classes = np.unique(y)
    chosen = []

    for c in classes:
        idx = np.flatnonzero(y == c)
        if idx.size == 0:
            continue
        take = min(per_class_cap, idx.size)
        chosen.extend(rng.choice(idx, size=take, replace=False).tolist())

    chosen = sorted(set(chosen))

    # Top up to the requested total, spreading across classes rather than
    # draining the largest one first.
    if len(chosen) < total:
        remaining = np.setdiff1d(np.arange(y.size), np.asarray(chosen, dtype=int))
        per_class_remaining = {
            int(c): remaining[y[remaining] == c] for c in np.unique(y[remaining])
        }
        # Round-robin over classes, weighted by class size. Pure round-robin
        # would treat a 3-row class the same as a 500k-row one and hand most of
        # the top-up to BENIGN, which is exactly the imbalance the per-class
        # cap exists to avoid.
        pool = []
        cursors = {c: 0 for c in per_class_remaining}
        progressed = True
        while progressed:
            progressed = False
            for c in sorted(per_class_remaining):
                arr = per_class_remaining[c]
                # Take a slice proportional to this class's share of the
                # remaining pool, so the top-up preserves the (capped)
                # distribution instead of reverting to the raw one.
                take = max(1, round(len(arr) / max(1, remaining.size) * len(per_class_remaining)))
                for _ in range(min(take, arr.size - cursors[c])):
                    pool.append(int(arr[cursors[c]]))
                    cursors[c] += 1
                    progressed = True
        for idx in pool:
            if len(chosen) >= total:
                break
            chosen.append(idx)

    chosen = sorted(set(chosen))[:total]
    return X[chosen].astype("float32"), chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sequences-dir",
        default="datasets/verify_run_ruthwik",
        help="Folder holding X_train_seq.npy and y_train_seq.npy (default: %(default)s)",
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output .npy path (default: %(default)s)")
    parser.add_argument("--total", type=int, default=100, help="Total background windows (default: %(default)s)")
    parser.add_argument("--per-class-cap", type=int, default=4, help="Windows per class before topping up (default: %(default)s)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    X_path = os.path.join(args.sequences_dir, "X_train_seq.npy")
    y_path = os.path.join(args.sequences_dir, "y_train_seq.npy")

    for p in (X_path, y_path):
        if not os.path.exists(p):
            sys.exit(
                f"Missing {p}\n"
                "Regenerate the windowed arrays first:\n"
                "  python model/rebuild_chronological_split.py --input <cleaned csv> --output-dir "
                f"{args.sequences_dir}\n"
                "or run this script in the environment that already has the dataset."
            )

    X = np.load(X_path)
    y = np.load(y_path)
    print(f"Loaded {X.shape[0]:,} training windows of shape {X.shape[1:]} from {args.sequences_dir}")

    background, indices = sample_background(
        X, y, total=args.total, per_class_cap=args.per_class_cap, seed=args.seed
    )

    # Class names for the manifest, if the label mapping is next to the arrays.
    label_map_path = os.path.join("model", "artifacts", "label_mapping_v2.json")
    id_to_name = None
    if os.path.exists(label_map_path):
        with open(label_map_path) as f:
            id_to_name = {v: k for k, v in json.load(f).items()}

    counts = {}
    for i in indices:
        name = id_to_name.get(int(np.asarray(y).reshape(-1)[i]), str(int(np.asarray(y).reshape(-1)[i])))
        counts[name] = counts.get(name, 0) + 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    np.save(args.out, background)

    size_kb = os.path.getsize(args.out) / 1024
    print(f"\nWrote {args.out}  shape={background.shape}  {size_kb:.1f} KB")
    print(f"Classes represented: {len(counts)}")
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {name}")

    if len(counts) < 2:
        print(
            "\nWARNING: fewer than 2 classes in the background. Attack-window "
            "explanations will not be meaningful."
        )


if __name__ == "__main__":
    main()