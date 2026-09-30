"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Prevention Policy Evaluation on the Test Sets
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Measures what the prevention policy would actually do: every test
window's predicted class and confidence go through
class_action_mapping.get_action(), and the decision is compared with the
window's true label. Answers, per dataset (and per MU-IoT test track):

    benign traffic     how much would trigger an automatic action
                       (false automatic actions) or be sent to review
    attack traffic     how much is handled automatically, sent to
                       review, or missed (called benign)
    automatic actions  how many hit the predicted attack, a different
                       attack, or benign traffic

The policy is only measured here, never tuned on these results.

Usage (paths default to the repo layout):

    python model/evaluate_prevention_policy.py --dataset cicids2017
    python model/evaluate_prevention_policy.py --dataset mu_iot \\
        --data-dir /content/drive/MyDrive/Major_Project/handoff_v3        (Colab)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(MODEL_DIR)
sys.path.insert(0, MODEL_DIR)

from class_action_mapping import POLICIES, get_action  # noqa: E402
from prevention_executor import ACTION_DURATIONS  # noqa: E402

DEFAULTS = {
    "cicids2017": {"model": "model/artifacts/cnn_lstm_best_v2.keras",
                   "label_mapping": "model/artifacts/label_mapping_v2.json",
                   "benign": "BENIGN"},
    "mu_iot": {"model": "model/artifacts/mu_iot/best.keras",
               "label_mapping": "model/artifacts/mu_iot/label_mapping.json",
               "benign": "normal"},
}
MU_IOT_SEQ_LEN = 20
STATUSES = ("auto_action", "held_for_review", "no_action_needed")


def repo_path(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def display_path(path):
    try:
        rel = os.path.relpath(path, REPO)
    except ValueError:  # different drive on Windows
        return path
    return path if rel.startswith("..") else rel.replace(os.sep, "/")


def load_class_names(path):
    with open(path) as f:
        label_to_int = json.load(f)
    id_to_name = {v: k for k, v in label_to_int.items()}
    return [id_to_name[i] for i in sorted(id_to_name)]


def decide(probs, class_names, dataset):
    """Run every prediction through get_action(); returns predicted ids and status codes."""
    pred = probs.argmax(axis=1)
    conf = probs.max(axis=1).astype(np.float64)
    status = np.empty(len(pred), dtype=np.int8)
    code = {s: i for i, s in enumerate(STATUSES)}
    for i, (p, c) in enumerate(zip(pred, conf)):
        status[i] = code[get_action(class_names[p], float(c), dataset)["status"]]
    return pred, status


def summarize(y_true, pred, status, class_names, benign_id, dataset):
    auto, review, none = (status == 0), (status == 1), (status == 2)
    benign = y_true == benign_id
    attack = ~benign

    def split(mask):
        n = int(mask.sum())
        return {"windows": n, "auto_action": int((mask & auto).sum()),
                "held_for_review": int((mask & review).sum()), "no_action": int((mask & none).sum())}

    per_true = {class_names[c]: split(y_true == c) for c in np.unique(y_true)}
    per_pred = {}
    for c in np.unique(pred[auto]):
        m = auto & (pred == c)
        name = class_names[c]
        per_pred[name] = {
            "action": POLICIES[dataset][name]["action"],
            "threshold": POLICIES[dataset][name]["threshold"],
            "auto_action": int(m.sum()),
            "on_predicted_attack": int((m & (y_true == c)).sum()),
            "on_other_attack": int((m & attack & (y_true != c)).sum()),
            "on_benign": int((m & benign).sum()),
        }
    executable = np.array([POLICIES[dataset][class_names[c]]["action"] in ACTION_DURATIONS for c in pred])
    return {
        "windows": int(len(y_true)),
        "accuracy": float((pred == y_true).mean()),
        "benign": split(benign),
        "attack": split(attack),
        "benign_auto_executable": int((benign & auto & executable).sum()),
        "auto_decisions": {
            "total": int(auto.sum()),
            "on_predicted_attack": int((auto & (pred == y_true)).sum()),
            "on_other_attack": int((auto & attack & (pred != y_true)).sum()),
            "on_benign": int((auto & benign).sum()),
        },
        "per_true_class": per_true,
        "auto_by_predicted_class": per_pred,
    }


def pct(part, whole):
    return f"{part:>10,} ({100.0 * part / whole:6.2f}%)" if whole else f"{part:>10,}        -"


def format_track(title, s, benign_name):
    b, a, d = s["benign"], s["attack"], s["auto_decisions"]
    lines = [
        "-" * 78, title, "-" * 78,
        f"Windows : {s['windows']:,}   (model accuracy on them: {s['accuracy']:.4f})",
        "",
    ]
    if b["windows"]:
        lines += [
            f"{benign_name.upper()} TRAFFIC ({b['windows']:,} windows)",
            f"  no action                  {pct(b['no_action'], b['windows'])}",
            f"  sent to review             {pct(b['held_for_review'], b['windows'])}   false alerts a person dismisses",
            f"  automatic action           {pct(b['auto_action'], b['windows'])}   false automatic actions",
            f"    of which a real firewall action {s['benign_auto_executable']:>6,}",
            "",
        ]
    else:
        lines += [f"{benign_name.upper()} TRAFFIC: none in this track", ""]
    lines += [
        f"ATTACK TRAFFIC ({a['windows']:,} windows)",
        f"  automatic action           {pct(a['auto_action'], a['windows'])}",
        f"  sent to review             {pct(a['held_for_review'], a['windows'])}",
        f"  no action (called {benign_name})".ljust(29) + f"{pct(a['no_action'], a['windows'])}   missed",
        "",
        f"AUTOMATIC ACTIONS ({d['total']:,} decisions)",
        f"  on the predicted attack    {pct(d['on_predicted_attack'], d['total'])}",
        f"  on a different attack      {pct(d['on_other_attack'], d['total'])}   attacker still acted on; action type may differ",
        f"  on {benign_name} traffic".ljust(29) + f"{pct(d['on_benign'], d['total'])}   collateral",
        "",
        "PER TRUE CLASS                       windows        auto      review   no action",
    ]
    for name, t in s["per_true_class"].items():
        n = t["windows"]
        lines.append(f"  {name[:30]:<30}{n:>13,}{100 * t['auto_action'] / n:>11.2f}%"
                     f"{100 * t['held_for_review'] / n:>11.2f}%{100 * t['no_action'] / n:>11.2f}%")
    lines += ["", "AUTOMATIC ACTIONS BY PREDICTED CLASS",
              f"  {'class':<27}{'action':<16}{'thresh':>7}{'auto':>10}{'correct':>10}{'other atk':>11}{benign_name[:9]:>10}"]
    for name, p in s["auto_by_predicted_class"].items():
        lines.append(f"  {name[:26]:<27}{p['action']:<16}{p['threshold']:>7.2f}{p['auto_action']:>10,}"
                     f"{p['on_predicted_attack']:>10,}{p['on_other_attack']:>11,}{p['on_benign']:>10,}")
    return lines + [""]


def run_cicids(args, model, class_names):
    seq_dir = repo_path(args.sequences_dir)
    X = np.load(os.path.join(seq_dir, "X_test_seq.npy"))
    y = np.load(os.path.join(seq_dir, "y_test_seq.npy")).astype(np.int64)
    probs = model.predict(X, batch_size=args.batch_size, verbose=0)
    return {"test": (y, probs)}, f"all test windows from {display_path(seq_dir)}"


def run_mu_iot(args, model, class_names):
    from train_cnn_lstm_mu_iot import (build_windows, load_package, predict_probs, split_view,
                                       stage_data, validate_package)
    if not args.data_dir:
        raise SystemExit("--data-dir is required for --dataset mu_iot (the package stays on Drive)")
    pkg = load_package(stage_data(args.data_dir, args.local_dir))
    validate_package(pkg)
    if [pkg["id_to_name"][i] for i in sorted(pkg["id_to_name"])] != class_names:
        raise SystemExit("Package label mapping differs from the model's label mapping")
    windows, _ = build_windows(pkg, MU_IOT_SEQ_LEN)
    tracks = {}
    for track in ("test_within", "test_heldout"):
        view = split_view(windows, track)
        if len(view["starts"]):
            probs = predict_probs(model, pkg["X"], view["starts"], MU_IOT_SEQ_LEN, args.batch_size)
            tracks[track] = (view["labels"], probs)
    return tracks, f"all test windows from {args.data_dir}"


def main():
    parser = argparse.ArgumentParser(description="Measure the prevention policy's decisions on the test sets")
    parser.add_argument("--dataset", choices=sorted(DEFAULTS), required=True)
    parser.add_argument("--model")
    parser.add_argument("--label-mapping")
    parser.add_argument("--sequences-dir", default="datasets/verify_run_ruthwik", help="CICIDS2017 test windows")
    parser.add_argument("--data-dir", help="MU-IoT package folder (on Drive in Colab)")
    parser.add_argument("--local-dir", default="/content/mu_iot_data", help="Local copy of the MU-IoT package")
    parser.add_argument("--output-dir", default="model/results")
    parser.add_argument("--batch-size", type=int, default=2048)
    args = parser.parse_args()

    from tensorflow import keras

    cfg = DEFAULTS[args.dataset]
    model_path = repo_path(args.model or cfg["model"])
    class_names = load_class_names(repo_path(args.label_mapping or cfg["label_mapping"]))
    if set(class_names) != set(POLICIES[args.dataset]):
        raise SystemExit("Model classes and policy classes differ - run model/test_prevention.py")
    model = keras.models.load_model(model_path, compile=False)

    runner = run_cicids if args.dataset == "cicids2017" else run_mu_iot
    tracks, source = runner(args, model, class_names)
    benign_id = class_names.index(cfg["benign"])

    results = {}
    lines = [
        "=" * 78,
        f"PREVENTION POLICY ON THE TEST SET - {args.dataset.upper()}",
        "=" * 78,
        f"Generated : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Model     : {display_path(model_path)}",
        f"Windows   : {source}",
        f"Policy    : class_action_mapping.get_action(dataset=\"{args.dataset}\")",
        "",
        "Every window's predicted class and confidence go through the policy; the",
        "decision is then compared with the window's true label. Measured only,",
        "never used to tune the thresholds.",
        "",
    ]
    for track, (y, probs) in tracks.items():
        pred, status = decide(probs, class_names, args.dataset)
        results[track] = summarize(y, pred, status, class_names, benign_id, args.dataset)
        lines += format_track(track.upper(), results[track], cfg["benign"])
        print(f"[+] {track}: {len(y):,} windows")

    out_dir = repo_path(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    txt_path = os.path.join(out_dir, f"prevention_policy_{args.dataset}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(os.path.join(out_dir, f"prevention_policy_{args.dataset}.json"), "w", encoding="utf-8") as f:
        json.dump({"dataset": args.dataset, "model": display_path(model_path), "tracks": results}, f, indent=2)
    print("\n".join(lines))
    print(f"Wrote {display_path(txt_path)} and the matching .json")


if __name__ == "__main__":
    main()
