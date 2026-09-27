"""
Tests for the window/sampling logic in train_cnn_lstm_mu_iot.py.

Run:  python model/test_mu_iot_windows.py

No TensorFlow and no real data needed - these cover the parts that would
silently corrupt results if wrong (windows crossing a block/split/gap,
wrong labels, timestamp features slipping in, broken caps or weights).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_cnn_lstm_mu_iot import (build_windows, class_weight_vector,  # noqa: E402
                                   sample_per_class, validate_package)

SEQ = 5


def make_pkg(segments, n_feat=4):
    """segments: list of (n_rows, block_id, split, category_id, first_row_id)."""
    meta = {k: [] for k in ["row_id", "capture_session", "block_id", "split", "category_id"]}
    for n, block, split, cat, start in segments:
        meta["row_id"] += range(start, start + n)
        meta["capture_session"] += [f"S{block}"] * n
        meta["block_id"] += [block] * n
        meta["split"] += [split] * n
        meta["category_id"] += [cat] * n
    meta = {k: np.array(v) for k, v in meta.items()}
    X = np.random.default_rng(0).normal(size=(len(meta["row_id"]), n_feat)).astype(np.float32)
    return {"X": X, "meta": meta, "features": [f"F{i}" for i in range(n_feat)],
            "name_to_id": {"a": 0, "b": 1}, "id_to_name": {0: "a", 1: "b"}}


# Each boundary is stopped by exactly one rule, so removing any single
# rule from build_windows makes the crossing test fail.
SEGMENTS = [
    (12, 0, 0, 0, 0),    # A
    (10, 1, 0, 0, 12),   # A|B: only block_id changes (same split, consecutive row_id)
    (8, 2, 1, 1, 22),    # B|C: block and split change
    (6, 2, 2, 1, 30),    # C|D: only split changes (same block, consecutive row_id)
    (7, 2, 2, 1, 50),    # D|E: only row_id jumps (same block, same split)
    (3, 3, 2, 1, 57),    # shorter than a window: must produce nothing
]


def test_windows_never_cross_block_split_or_gap():
    pkg = make_pkg(SEGMENTS)
    windows, _ = build_windows(pkg, SEQ)
    m = pkg["meta"]
    for s in windows["starts"]:
        rows = slice(s, s + SEQ)
        assert len(set(m["block_id"][rows])) == 1, f"window at {s} crosses a block"
        assert len(set(m["split"][rows])) == 1, f"window at {s} crosses a split"
        assert (np.diff(m["row_id"][rows]) == 1).all(), f"window at {s} crosses a row_id gap"


def test_window_count_per_block():
    pkg = make_pkg(SEGMENTS)
    windows, _ = build_windows(pkg, SEQ)
    expected = sum(max(0, seg[0] - SEQ + 1) for seg in SEGMENTS)
    assert len(windows["starts"]) == expected, f"{len(windows['starts'])} windows, expected {expected}"


def test_label_is_last_row_and_mixed_windows_reported():
    pkg = make_pkg([(4, 0, 0, 0, 0), (4, 0, 0, 1, 4)])  # one block whose class changes midway
    windows, diag = build_windows(pkg, SEQ)
    cat = pkg["meta"]["category_id"]
    assert (windows["labels"] == cat[windows["starts"] + SEQ - 1]).all(), "label is not the last row's class"
    assert diag["mixed_label_windows"] > 0, "a class change inside a window was not reported"


def test_row_id_gap_inside_block_breaks_windows_unless_disabled():
    pkg = make_pkg([(6, 0, 0, 0, 0), (6, 0, 0, 0, 50)])  # same block, gap in row_id
    with_check, _ = build_windows(pkg, SEQ, check_row_id=True)
    without_check, _ = build_windows(pkg, SEQ, check_row_id=False)
    assert len(with_check["starts"]) == 2 * (6 - SEQ + 1), "window crossed a row_id gap"
    assert len(without_check["starts"]) == 12 - SEQ + 1, "--no-row-id-check did not relax the rule"


def test_timestamp_features_rejected():
    for leaked in ("FPT", "LPT"):
        pkg = make_pkg([(10, 0, 0, 0, 0), (10, 1, 0, 1, 10)])
        pkg["features"][0] = leaked
        try:
            validate_package(pkg)
        except ValueError as e:
            assert leaked in str(e)
        else:
            raise AssertionError(f"{leaked} was accepted as a model input")


def test_clean_package_passes_validation():
    validate_package(make_pkg([(10, 0, 0, 0, 0), (10, 1, 0, 1, 10)]))


def test_sample_per_class_caps_big_keeps_small_and_is_deterministic():
    view = {"starts": np.arange(110), "labels": np.array([0] * 100 + [1] * 10)}
    a = sample_per_class(view, 30, np.random.default_rng(1), shuffle=True)
    b = sample_per_class(view, 30, np.random.default_rng(1), shuffle=True)
    assert (a["labels"] == 0).sum() == 30, "big class not capped"
    assert (a["labels"] == 1).sum() == 10, "small class not kept in full"
    assert (a["starts"] == b["starts"]).all(), "same seed gave a different sample"
    assert len(sample_per_class(view, 0, np.random.default_rng(1), shuffle=False)["starts"]) == 110, "cap 0 should keep all"


def test_class_weights_favour_rare_classes_and_respect_cap():
    view = {"starts": np.arange(1010), "labels": np.array([0] * 1000 + [1] * 10)}
    weights, _ = class_weight_vector(view, cap=0, n_classes=2, weight_cap=100.0)
    assert weights[1] > weights[0], "rare class did not get the larger weight"
    capped, _ = class_weight_vector(view, cap=0, n_classes=2, weight_cap=2.0)
    assert capped.max() <= 2.0, "weight cap exceeded"


if __name__ == "__main__":
    tests = [fn for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
