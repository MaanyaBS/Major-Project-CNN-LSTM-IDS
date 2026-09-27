"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : MU-IoT CNN-LSTM Training & Evaluation (run in Colab)
Author  : Person B (Model Development)
==========================================================
Trains and evaluates the CNN-LSTM on the MU-IoT package prepared by the
data side:

    mu_iot_features_38_float32.npy   (N, 38) scaled features
    mu_iot_meta.npz                  row_id, capture_session, block_id,
                                     split, category_id  (one entry per row)
    feature_list_38.json             feature names, in column order
    label_mapping.json               category name -> id

Windows are SEQ_LEN consecutive rows that never cross a block, a split,
or a gap in row_id. Each epoch trains on a fresh capped sample per class
(big classes are capped, small classes are used in full). After every
epoch a checkpoint and a state file are written to --out-dir, so a Colab
disconnect loses at most the current epoch: rerun with --resume.

Results are reported separately for:
    test_within   later rows of the sessions used in training (optimistic)
    test_heldout  whole sessions never seen in training (generalization)
"""

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone

import numpy as np

SPLITS = {"train": 0, "val": 1, "test_within": 2, "test_heldout": 3}
FEATURES_FILE = "mu_iot_features_38_float32.npy"
META_FILE = "mu_iot_meta.npz"
FEATURE_LIST_FILE = "feature_list_38.json"
LABEL_MAP_FILE = "label_mapping.json"
PACKAGE_FILES = [FEATURES_FILE, META_FILE, FEATURE_LIST_FILE, LABEL_MAP_FILE]
META_KEYS = ["row_id", "capture_session", "block_id", "split", "category_id"]


# ----------------------------------------------------------------------
# Data staging and loading
# ----------------------------------------------------------------------

def stage_data(data_dir, local_dir):
    """Copy the package from Drive to local disk; reading it off Drive is very slow."""
    os.makedirs(local_dir, exist_ok=True)
    for name in PACKAGE_FILES:
        src = os.path.join(data_dir, name)
        dst = os.path.join(local_dir, name)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Missing package file: {src}")
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            continue
        print(f"[+] Copying {name} ({os.path.getsize(src) / 1e6:.1f} MB) to local disk...")
        shutil.copy2(src, dst)
    return local_dir


def load_label_map(path):
    with open(path) as f:
        raw = json.load(f)
    first_key = next(iter(raw))
    if str(first_key).isdigit():
        name_to_id = {name: int(idx) for idx, name in raw.items()}
    else:
        name_to_id = {name: int(idx) for name, idx in raw.items()}
    id_to_name = {v: k for k, v in name_to_id.items()}
    return name_to_id, id_to_name


def load_package(local_dir):
    X = np.load(os.path.join(local_dir, FEATURES_FILE), mmap_mode="r")
    meta_npz = np.load(os.path.join(local_dir, META_FILE), allow_pickle=True)
    missing = [k for k in META_KEYS if k not in meta_npz.files]
    if missing:
        raise ValueError(f"{META_FILE} is missing keys: {missing}")
    meta = {k: meta_npz[k] for k in META_KEYS}
    with open(os.path.join(local_dir, FEATURE_LIST_FILE)) as f:
        feature_list = json.load(f)
    name_to_id, id_to_name = load_label_map(os.path.join(local_dir, LABEL_MAP_FILE))
    return {"X": X, "meta": meta, "features": feature_list,
            "name_to_id": name_to_id, "id_to_name": id_to_name}


def validate_package(pkg):
    X, meta = pkg["X"], pkg["meta"]
    if X.ndim != 2:
        raise ValueError(f"Feature array must be 2D, got shape {X.shape}")
    if X.dtype != np.float32:
        raise ValueError(f"Feature array must be float32, got {X.dtype}")
    n = X.shape[0]
    for k in META_KEYS:
        if len(meta[k]) != n:
            raise ValueError(f"meta['{k}'] has {len(meta[k])} entries, features have {n} rows")
    if len(pkg["features"]) != X.shape[1]:
        raise ValueError(f"feature_list has {len(pkg['features'])} names, array has {X.shape[1]} columns")
    for leaked in ("FPT", "LPT"):
        if leaked in pkg["features"]:
            raise ValueError(f"'{leaked}' is a timestamp and must not be a model input")

    bad_splits = set(np.unique(meta["split"]).tolist()) - set(SPLITS.values())
    if bad_splits:
        raise ValueError(f"Unknown split codes: {bad_splits}")
    bad_ids = set(np.unique(meta["category_id"]).tolist()) - set(pkg["id_to_name"])
    if bad_ids:
        raise ValueError(f"category_id values missing from label_mapping.json: {bad_ids}")

    for i in range(0, n, 1_000_000):
        if not np.isfinite(X[i:i + 1_000_000]).all():
            raise ValueError(f"NaN/Inf found in feature rows {i}..{i + 1_000_000}")

    train_classes = set(np.unique(meta["category_id"][meta["split"] == SPLITS["train"]]).tolist())
    absent = set(pkg["id_to_name"]) - train_classes
    if absent:
        names = [pkg["id_to_name"][c] for c in sorted(absent)]
        print(f"[!] WARNING: classes with no training rows: {names}")


# ----------------------------------------------------------------------
# Window construction
# ----------------------------------------------------------------------

def build_windows(pkg, seq_len, check_row_id=True):
    """
    Returns every valid window start, its label (category of the last row),
    its split and its capture session. A window is valid only if all its
    rows share one block, one split, and (optionally) consecutive row_ids.
    """
    meta = pkg["meta"]
    n = len(meta["split"])
    block, split, row_id, cat = meta["block_id"], meta["split"], meta["row_id"], meta["category_id"]

    base_breaks = (block[1:] != block[:-1]) | (split[1:] != split[:-1])
    breaks = base_breaks | (row_id[1:] != row_id[:-1] + 1) if check_row_id else base_breaks
    run_id = np.concatenate([[0], np.cumsum(breaks)])
    cat_run = np.concatenate([[0], np.cumsum(cat[1:] != cat[:-1])])

    starts = np.arange(n - seq_len + 1)
    ends = starts + seq_len - 1
    valid = run_id[starts] == run_id[ends]

    diagnostics = {
        "rows": int(n),
        "runs_block_split_only": int(base_breaks.sum()) + 1,
        "runs_with_row_id_check": int(breaks.sum()) + 1,
        "mixed_label_windows": int((valid & (cat_run[starts] != cat_run[ends])).sum()),
    }
    starts, ends = starts[valid], ends[valid]
    return {
        "starts": starts.astype(np.int64),
        "labels": cat[ends].astype(np.int64),
        "split": split[starts].astype(np.int64),
        "session": meta["capture_session"][ends],
    }, diagnostics


def split_view(windows, split_name):
    mask = windows["split"] == SPLITS[split_name]
    return {k: v[mask] for k, v in windows.items()}


def sample_per_class(view, cap, rng, shuffle):
    """Up to `cap` windows per class (cap <= 0 means all)."""
    chosen = []
    for c in np.unique(view["labels"]):
        idx = np.flatnonzero(view["labels"] == c)
        if 0 < cap < len(idx):
            idx = rng.choice(idx, cap, replace=False)
        chosen.append(idx)
    sel = np.concatenate(chosen) if chosen else np.array([], dtype=np.int64)
    sel = rng.permutation(sel) if shuffle else np.sort(sel)
    return {k: v[sel] for k, v in view.items()}


def class_weight_vector(train_view, cap, n_classes, weight_cap):
    """Square root of balanced weights, computed on the capped per-epoch counts, then capped."""
    counts = np.zeros(n_classes, dtype=np.float64)
    for c in range(n_classes):
        n_c = int((train_view["labels"] == c).sum())
        counts[c] = min(n_c, cap) if cap > 0 else n_c
    present = counts > 0
    weights = np.ones(n_classes, dtype=np.float32)
    total, k = counts[present].sum(), present.sum()
    weights[present] = np.minimum(np.sqrt(total / (k * counts[present])), weight_cap)
    return weights, counts


# ----------------------------------------------------------------------
# tf.data pipeline and model
# ----------------------------------------------------------------------

def make_dataset(X, starts, labels, weight_vec, seq_len, batch_size, with_targets):
    import tensorflow as tf

    n_feat = X.shape[1]
    offsets = np.arange(seq_len)

    def gen():
        for i in range(0, len(starts), batch_size):
            xb = np.asarray(X[starts[i:i + batch_size, None] + offsets[None, :]], dtype=np.float32)
            if with_targets:
                yb = labels[i:i + batch_size]
                yield xb, yb.astype(np.int32), weight_vec[yb].astype(np.float32)
            else:
                yield xb

    x_spec = tf.TensorSpec((None, seq_len, n_feat), tf.float32)
    if with_targets:
        sig = (x_spec, tf.TensorSpec((None,), tf.int32), tf.TensorSpec((None,), tf.float32))
    else:
        sig = x_spec
    return tf.data.Dataset.from_generator(gen, output_signature=sig).prefetch(tf.data.AUTOTUNE)


def build_model(seq_len, n_features, n_classes):
    """Same CNN-LSTM as the CICIDS2017 model, resized for MU-IoT."""
    from tensorflow import keras
    from tensorflow.keras import layers

    model = keras.Sequential([
        keras.Input(shape=(seq_len, n_features)),
        layers.Conv1D(64, 3, activation="relu"),
        layers.BatchNormalization(),
        layers.MaxPooling1D(2),
        layers.Conv1D(128, 3, activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.MaxPooling1D(2),
        layers.LSTM(64),
        layers.Dense(64, activation="relu"),
        layers.Dense(n_classes, activation="softmax", dtype="float32"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def predict_probs(model, X, starts, seq_len, batch_size):
    ds = make_dataset(X, starts, None, None, seq_len, batch_size, with_targets=False)
    steps = int(np.ceil(len(starts) / batch_size))
    return model.predict(ds, steps=steps, verbose=0)


def val_scores(y_true, probs):
    from sklearn.metrics import f1_score

    p = np.clip(probs[np.arange(len(y_true)), y_true], 1e-7, 1.0)
    y_pred = probs.argmax(axis=1)
    return {
        "val_loss": float(-np.log(p).mean()),
        "val_accuracy": float((y_pred == y_true).mean()),
        "val_macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


# ----------------------------------------------------------------------
# Checkpoint / resume helpers
# ----------------------------------------------------------------------

def atomic_json(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def atomic_model_save(model, path):
    tmp = path[:-len(".keras")] + ".tmp.keras"
    model.save(tmp)
    os.replace(tmp, path)


# ----------------------------------------------------------------------
# Training
# ----------------------------------------------------------------------

def train(args, pkg, windows, out_dir, n_classes):
    from tensorflow import keras

    X = pkg["X"]
    ckpt_dir = os.path.join(out_dir, "checkpoints")
    os.makedirs(ckpt_dir, exist_ok=True)
    last_path = os.path.join(ckpt_dir, "last.keras")
    best_path = os.path.join(ckpt_dir, "best.keras")
    state_path = os.path.join(ckpt_dir, "state.json")

    if os.path.exists(state_path) and not args.resume:
        raise SystemExit(
            f"[!] A run already exists in {ckpt_dir}. Use --resume to continue it, "
            f"or point --out-dir somewhere else."
        )

    train_view = split_view(windows, "train")
    val_view = split_view(windows, "val")
    val_fixed = sample_per_class(val_view, args.val_cap_per_class,
                                 np.random.default_rng(args.seed), shuffle=False)
    weight_vec, epoch_counts = class_weight_vector(train_view, args.cap_per_class,
                                                   n_classes, args.weight_cap)

    print("\n[+] Per-epoch training windows (capped) and class weights:")
    for c in range(n_classes):
        print(f"    {pkg['id_to_name'][c]:<18} windows/epoch={int(epoch_counts[c]):>9,}  weight={weight_vec[c]:.3f}")
    print(f"    fixed validation slice: {len(val_fixed['starts']):,} windows")

    if args.resume and os.path.exists(state_path):
        with open(state_path) as f:
            state = json.load(f)
        if state["stopped_early"] or state["completed_epochs"] >= args.epochs:
            reason = "early stopping" if state["stopped_early"] else f"all {args.epochs} epochs done"
            print(f"[+] Nothing left to train ({reason}) - going straight to evaluation.")
            return best_path
        model = keras.models.load_model(last_path)
        print(f"[+] Resuming after epoch {state['completed_epochs']} "
              f"(best {args.monitor} so far: {state['best_metric']:.4f} at epoch {state['best_epoch']})")
    else:
        model = build_model(args.seq_len, X.shape[1], n_classes)
        state = {"completed_epochs": 0, "best_metric": None, "best_epoch": None,
                 "bad_epochs": 0, "stopped_early": False,
                 "history": {"loss": [], "val_loss": [], "val_accuracy": [],
                             "val_macro_f1": [], "epoch_seconds": [], "windows": []}}
        model.summary()

    higher_is_better = args.monitor == "val_macro_f1"

    for epoch in range(state["completed_epochs"], args.epochs):
        rng = np.random.default_rng(args.seed + 1000 + epoch)
        epoch_view = sample_per_class(train_view, args.cap_per_class, rng, shuffle=True)
        ds = make_dataset(X, epoch_view["starts"], epoch_view["labels"], weight_vec,
                          args.seq_len, args.batch_size, with_targets=True)
        steps = int(np.ceil(len(epoch_view["starts"]) / args.batch_size))

        print(f"\n=== Epoch {epoch + 1}/{args.epochs}  ({len(epoch_view['starts']):,} windows) ===")
        t0 = time.time()
        fit_hist = model.fit(ds, epochs=1, steps_per_epoch=steps, shuffle=False, verbose=1)
        probs = predict_probs(model, X, val_fixed["starts"], args.seq_len, args.batch_size)
        scores = val_scores(val_fixed["labels"], probs)
        seconds = time.time() - t0

        h = state["history"]
        h["loss"].append(float(fit_hist.history["loss"][-1]))
        h["val_loss"].append(scores["val_loss"])
        h["val_accuracy"].append(scores["val_accuracy"])
        h["val_macro_f1"].append(scores["val_macro_f1"])
        h["epoch_seconds"].append(seconds)
        h["windows"].append(int(len(epoch_view["starts"])))
        print(f"[+] loss={h['loss'][-1]:.4f}  val_loss={scores['val_loss']:.4f}  "
              f"val_acc={scores['val_accuracy']:.4f}  val_macro_f1={scores['val_macro_f1']:.4f}  "
              f"({seconds / 60:.1f} min)")

        current = scores[args.monitor]
        improved = (state["best_metric"] is None or
                    (current > state["best_metric"] if higher_is_better else current < state["best_metric"]))
        if improved:
            state["best_metric"], state["best_epoch"], state["bad_epochs"] = current, epoch + 1, 0
            atomic_model_save(model, best_path)
            print(f"[+] New best {args.monitor}: {current:.4f} - saved best.keras")
        else:
            state["bad_epochs"] += 1

        state["completed_epochs"] = epoch + 1
        state["stopped_early"] = state["bad_epochs"] >= args.patience
        atomic_model_save(model, last_path)
        atomic_json(state, state_path)
        atomic_json(state["history"], os.path.join(out_dir, "training_history.json"))

        if state["stopped_early"]:
            print(f"[+] Early stopping: no improvement in {args.patience} epochs.")
            break

    h = state["history"]
    if h["epoch_seconds"]:
        per_1k = h["epoch_seconds"][-1] / max(h["windows"][-1], 1) * 1000
        print(f"\n[+] Speed: {per_1k:.2f} s per 1,000 windows "
              f"(~{per_1k * 1500 / 60:.0f} min per 1.5M-window epoch)")
    print(f"[+] Best epoch: {state['best_epoch']} ({args.monitor}={state['best_metric']:.4f})")
    return best_path


# ----------------------------------------------------------------------
# Evaluation and reports
# ----------------------------------------------------------------------

def evaluate_track(model, pkg, view, track, args, n_classes, normal_id, results_dir):
    from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                                 f1_score, precision_recall_fscore_support)

    id_to_name = pkg["id_to_name"]
    probs = predict_probs(model, pkg["X"], view["starts"], args.seq_len, args.batch_size)
    y_true, y_pred = view["labels"], probs.argmax(axis=1)
    present = sorted(np.unique(y_true).tolist())
    names = [id_to_name[c] for c in present]
    all_ids = list(range(n_classes))

    metrics = {
        "track": track,
        "windows": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=present, average="weighted", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)),
        "macro_over_classes": names,
    }
    if normal_id is not None and normal_id in present:
        is_normal = y_true == normal_id
        metrics["normal_false_alarm_rate"] = float((y_pred[is_normal] != normal_id).mean())
    if normal_id is not None and (y_true != normal_id).any():
        is_attack = y_true != normal_id
        metrics["attack_called_normal_rate"] = float((y_pred[is_attack] == normal_id).mean())

    prec, rec, f1, sup = precision_recall_fscore_support(y_true, y_pred, labels=present, zero_division=0)
    metrics["per_class"] = {
        id_to_name[c]: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
        for c, p, r, f, s in zip(present, prec, rec, f1, sup)
    }
    metrics["per_session_accuracy"] = {}
    for sess in np.unique(view["session"]):
        m = view["session"] == sess
        metrics["per_session_accuracy"][str(sess)] = {
            "class": id_to_name[int(np.bincount(y_true[m]).argmax())],
            "windows": int(m.sum()),
            "accuracy": float((y_pred[m] == y_true[m]).mean()),
        }

    cm = confusion_matrix(y_true, y_pred, labels=all_ids)
    report = classification_report(y_true, y_pred, labels=present, target_names=names, zero_division=0)

    lines = [
        "=" * 78,
        f"CNN-LSTM MU-IoT - {track.upper()} EVALUATION",
        "=" * 78,
        f"Generated : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Windows   : {len(y_true):,}  (sequence length {args.seq_len}, {pkg['X'].shape[1]} features)",
        f"Classes   : {', '.join(names)}",
        "=" * 78,
        "",
        "OVERALL METRICS (macro/weighted F1 over the classes present in this track)",
        "-" * 78,
        f"Accuracy          : {metrics['accuracy']:.4f}",
        f"Weighted F1-score : {metrics['weighted_f1']:.4f}",
        f"Macro F1-score    : {metrics['macro_f1']:.4f}",
    ]
    if "normal_false_alarm_rate" in metrics:
        lines.append(f"Normal traffic flagged as attack (false alarms): {metrics['normal_false_alarm_rate']:.4f}")
    if "attack_called_normal_rate" in metrics:
        lines.append(f"Attacks classified as normal (missed attacks)  : {metrics['attack_called_normal_rate']:.4f}")
    lines += ["", "PER-CLASS CLASSIFICATION REPORT", "-" * 78, report,
              "PER-SESSION ACCURACY", "-" * 78]
    for sess, info in metrics["per_session_accuracy"].items():
        lines.append(f"{sess:<22} {info['class']:<18} windows={info['windows']:>9,}  accuracy={info['accuracy']:.4f}")
    lines += ["", "CONFUSION MATRIX (rows = true, columns = predicted, all classes)", "-" * 78]
    col_names = [id_to_name[c] for c in all_ids]
    lines.append("true\\pred".ljust(20) + "".join(f"{n[:10]:>12}" for n in col_names))
    for i, row in enumerate(cm):
        lines.append(col_names[i][:18].ljust(20) + "".join(f"{v:>12,}" for v in row))
    lines.append("=" * 78)

    with open(os.path.join(results_dir, f"mu_iot_{track}_results.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[:lines.index("PER-CLASS CLASSIFICATION REPORT")]))
    return metrics


def evaluate(args, pkg, windows, out_dir, n_classes, model_path):
    from tensorflow import keras

    if not os.path.exists(model_path):
        raise SystemExit(f"[!] No model found at {model_path}")
    model = keras.models.load_model(model_path)
    results_dir = os.path.join(out_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    normal_id = next((i for n, i in pkg["name_to_id"].items() if n.lower() == "normal"), None)
    rng = np.random.default_rng(args.seed + 7)
    all_metrics = {}
    for track in ("test_within", "test_heldout"):
        view = split_view(windows, track)
        if len(view["starts"]) == 0:
            print(f"[!] No windows in {track} - skipped.")
            continue
        view = sample_per_class(view, args.eval_cap_per_class, rng, shuffle=False)
        all_metrics[track] = evaluate_track(model, pkg, view, track, args, n_classes, normal_id, results_dir)

    atomic_json(all_metrics, os.path.join(results_dir, "mu_iot_metrics.json"))
    print(f"\n[+] Reports written to {results_dir}")
    return all_metrics


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Train and evaluate the CNN-LSTM on the MU-IoT package")
    p.add_argument("--data-dir", required=True, help="Folder with the MU-IoT package (e.g. on Drive)")
    p.add_argument("--out-dir", required=True, help="Folder for checkpoints and results (put this on Drive)")
    p.add_argument("--local-dir", default="/content/mu_iot_data", help="Local copy of the package")
    p.add_argument("--seq-len", type=int, default=20)
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--batch-size", type=int, default=512)
    p.add_argument("--cap-per-class", type=int, default=300_000, help="Training windows per class per epoch (0 = all)")
    p.add_argument("--val-cap-per-class", type=int, default=20_000, help="Fixed validation windows per class")
    p.add_argument("--eval-cap-per-class", type=int, default=0, help="Test windows per class (0 = all)")
    p.add_argument("--weight-cap", type=float, default=10.0)
    p.add_argument("--patience", type=int, default=5)
    p.add_argument("--monitor", choices=["val_loss", "val_macro_f1"], default="val_loss")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--resume", action="store_true", help="Continue an interrupted run in --out-dir")
    p.add_argument("--eval-only", action="store_true", help="Skip training, evaluate best.keras")
    p.add_argument("--pilot", action="store_true", help="Tiny caps and 2 epochs, to test the pipeline")
    p.add_argument("--no-row-id-check", action="store_true", help="Do not require consecutive row_ids in a window")
    p.add_argument("--no-mixed-precision", action="store_true")
    return p.parse_args()


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=os.path.dirname(os.path.abspath(__file__)),
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def main():
    args = parse_args()
    out_dir = os.path.join(args.out_dir, "pilot") if args.pilot else args.out_dir
    if args.pilot:
        args.cap_per_class = min(args.cap_per_class, 2000) if args.cap_per_class > 0 else 2000
        args.val_cap_per_class = min(args.val_cap_per_class, 500)
        args.eval_cap_per_class = 2000
        args.epochs = min(args.epochs, 2)
    os.makedirs(out_dir, exist_ok=True)

    import tensorflow as tf
    import keras
    import sklearn

    tf.random.set_seed(args.seed)
    gpus = tf.config.list_physical_devices("GPU")
    print(f"[+] TensorFlow {tf.__version__} | GPUs: {[g.name for g in gpus] or 'none (CPU only)'}")
    if gpus and not args.no_mixed_precision:
        keras.mixed_precision.set_global_policy("mixed_float16")
        print("[+] Mixed precision: on")

    local_dir = stage_data(args.data_dir, args.local_dir)
    pkg = load_package(local_dir)
    validate_package(pkg)
    n_classes = len(pkg["id_to_name"])
    if sorted(pkg["id_to_name"]) != list(range(n_classes)):
        raise ValueError("label_mapping.json ids must be 0..K-1")

    windows, diag = build_windows(pkg, args.seq_len, check_row_id=not args.no_row_id_check)
    print(f"\n[+] Rows: {diag['rows']:,} | contiguous runs: {diag['runs_with_row_id_check']:,} "
          f"(block/split only: {diag['runs_block_split_only']:,})")
    if diag["runs_with_row_id_check"] > 2 * diag["runs_block_split_only"]:
        print("[!] WARNING: row_id gaps split many blocks - check that row_id is consecutive inside blocks.")
    if diag["mixed_label_windows"]:
        print(f"[!] WARNING: {diag['mixed_label_windows']:,} windows contain more than one class.")

    print("\n[+] Windows per split and class:")
    header = "    " + "class".ljust(18) + "".join(f"{s:>14}" for s in SPLITS)
    print(header)
    for c in range(n_classes):
        counts = [int(((windows["split"] == code) & (windows["labels"] == c)).sum()) for code in SPLITS.values()]
        print("    " + pkg["id_to_name"][c].ljust(18) + "".join(f"{v:>14,}" for v in counts))

    config_path = os.path.join(out_dir, "run_config.json")
    if not os.path.exists(config_path):
        atomic_json({
            "args": vars(args), "git_commit": git_commit(),
            "created": datetime.now(timezone.utc).isoformat(),
            "versions": {"tensorflow": tf.__version__, "keras": keras.__version__,
                         "numpy": np.__version__, "sklearn": sklearn.__version__},
            "features": pkg["features"], "label_mapping": pkg["name_to_id"],
            "n_rows": diag["rows"], "window_diagnostics": diag,
        }, config_path)

    best_path = os.path.join(out_dir, "checkpoints", "best.keras")
    if not args.eval_only:
        best_path = train(args, pkg, windows, out_dir, n_classes)
    evaluate(args, pkg, windows, out_dir, n_classes, best_path)


if __name__ == "__main__":
    main()
