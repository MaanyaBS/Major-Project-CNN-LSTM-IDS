"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : MU-IoT SHAP Analysis of the Main Errors (run in Colab)
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Explains the three error patterns found in the MU-IoT evaluation
(model/results/mu_iot/FINDINGS.md) with SHAP values:

    spyware    normal traffic predicted Spyware (the main false alarm)
    hping3     held-out hping3 UDP flood (MU_SESSION_031, DDoS) predicted Scan
    vulnscan   held-out vulnerability scan (MU_SESSION_021, Scan)
               predicted Password_Hacking

Each error group is compared with correctly classified windows of the
classes involved. If an error is driven by the same features, in the same
direction, as true detections of the predicted class, the model is
applying what it learned to traffic that genuinely looks like that class.

SHAP values are computed by expected gradients, the estimator behind
shap.GradientExplainer (which the dashboard uses), run in large batches.
The background is real training windows, balanced across classes. Two
checks are written into the report: additivity (each window's SHAP values
sum to its output minus the background mean) and, when the shap package
is installed, agreement with shap.GradientExplainer on the same windows.

Writes to --output-dir:
    mu_iot_shap_report.txt       findings, per question
    mu_iot_shap_values.json      per-group mean SHAP and values per feature
    mu_iot_shap_<question>.png   bar chart per question

Usage (Colab, GPU runtime recommended; CPU works but takes ~20 min):

    python model/explain_mu_iot.py \\
        --data-dir /content/drive/MyDrive/Major_Project/handoff_v3 \\
        --output-dir /content/drive/MyDrive/Major_Project_Dataset/mu_iot/runs/results
"""

import argparse
import json
import os
import pickle
import sys
import time
from datetime import datetime, timezone

import numpy as np

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(MODEL_DIR)
sys.path.insert(0, MODEL_DIR)

from train_cnn_lstm_mu_iot import (build_windows, load_package, predict_probs,  # noqa: E402
                                   sample_per_class, split_view, stage_data, validate_package)

SEQ_LEN = 20
TOP_FEATURES = 10

# question -> output explained, and groups as (label, track, true class, predicted class, session)
QUESTIONS = {
    "spyware": {
        "title": "Why is normal traffic flagged as Spyware?",
        "explain": "Spyware",
        "groups": [
            ("false alarm: normal -> Spyware", "test_within", "normal", "Spyware", None),
            ("detection: Spyware -> Spyware", "test_within", "Spyware", "Spyware", None),
            ("correct: normal -> normal", "test_within", "normal", "normal", None),
        ],
    },
    "hping3": {
        "title": "Why is the held-out hping3 UDP flood called Scan?",
        "explain": "Scan",
        "groups": [
            ("error: hping3 flood (DDoS) -> Scan", "test_heldout", "DDoS", "Scan", "MU_SESSION_031"),
            ("detection: Scan -> Scan", "test_within", "Scan", "Scan", None),
            ("detection: DDoS -> DDoS", "test_within", "DDoS", "DDoS", None),
        ],
    },
    "vulnscan": {
        "title": "Why is the held-out vulnerability scan called Password_Hacking?",
        "explain": "Password_Hacking",
        "groups": [
            ("error: vulnerability scan (Scan) -> Password_Hacking", "test_heldout", "Scan",
             "Password_Hacking", "MU_SESSION_021"),
            ("detection: Password_Hacking -> Password_Hacking", "test_within", "Password_Hacking",
             "Password_Hacking", None),
            ("detection: Scan -> Scan", "test_within", "Scan", "Scan", None),
        ],
    },
}


def repo_path(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def gather(X, starts):
    """Window rows from the (rows, features) array: returns (n, SEQ_LEN, features)."""
    return np.asarray(X[starts[:, None] + np.arange(SEQ_LEN)[None, :]], dtype=np.float32)


class ExpectedGradients:
    """
    SHAP values for one model output by expected gradients:
    phi(x) = mean over samples of grad f_k(b + a(x - b)) * (x - b),
    with b a random background window and a ~ Uniform(0, 1).
    Same estimator as shap.GradientExplainer, batched over many windows.
    """

    def __init__(self, model, background, nsamples, seed, max_points=16384):
        import tensorflow as tf

        self.tf, self.bg, self.nsamples, self.max_points = tf, background, nsamples, max_points
        self.rng = np.random.default_rng(seed)
        self.base = model.predict(background, verbose=0).mean(axis=0)  # E[f] per output

        @tf.function(input_signature=[tf.TensorSpec([None, *background.shape[1:]], tf.float32),
                                      tf.TensorSpec([], tf.int32)])
        def grads(points, k):
            with tf.GradientTape() as tape:
                tape.watch(points)
                out = tf.gather(model(points, training=False), k, axis=1)
            return tape.gradient(out, points)

        self._grads = grads

    def shap_values(self, X, k):
        per = max(1, self.max_points // self.nsamples)
        out = np.zeros(X.shape, dtype=np.float32)
        for s in range(0, len(X), per):
            xb = X[s:s + per]
            b = self.bg[self.rng.integers(len(self.bg), size=(len(xb), self.nsamples))]
            a = self.rng.random((len(xb), self.nsamples, 1, 1), dtype=np.float32)
            delta = xb[:, None] - b
            points = (b + a * delta).reshape(-1, *X.shape[1:])
            g = self._grads(self.tf.constant(points), self.tf.constant(k, self.tf.int32)).numpy()
            out[s:s + per] = (g.reshape(delta.shape) * delta).mean(axis=1)
        return out


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else float("nan")


def explain_group(explainer, model, scaler, Xg, k):
    sv = explainer.shap_values(Xg, k)                          # (n, 20, 38)
    per_window = sv.sum(axis=1)                                # (n, 38): summed over the 20 rows
    f = model.predict(Xg, verbose=0)[:, k]
    gap = f - explainer.base[k]
    total = per_window.sum(axis=1)
    raw = scaler.inverse_transform(Xg.reshape(-1, Xg.shape[2])).reshape(Xg.shape).mean(axis=1)
    return {
        "mean_output": float(f.mean()),
        "mean_shap": per_window.mean(axis=0).tolist(),
        "mean_abs_shap": np.abs(per_window).mean(axis=0).tolist(),
        "median_raw_value": np.median(raw, axis=0).tolist(),
        "mean_gap": float(gap.mean()),                              # output minus background mean
        "mean_shap_sum": float(total.mean()),                       # should match mean_gap
        "mean_abs_gap": float(np.abs(gap).mean()),
        "additivity_abs_error": float(np.abs(total - gap).mean()),  # |sum of SHAP - gap|, probability units
    }, sv


def shap_library_check(model, background, Xc, k, ours, nsamples):
    """Compare with shap.GradientExplainer on the same windows (skipped if shap is missing)."""
    try:
        import shap
    except ImportError:
        return {"skipped": "shap package not installed"}
    lib = shap.GradientExplainer(model, background, batch_size=200).shap_values(Xc, nsamples=nsamples, rseed=0)
    lib = (np.stack(lib, axis=-1) if isinstance(lib, list) else np.asarray(lib))[..., k]
    a, b = ours.sum(axis=1), lib.sum(axis=1)                   # (n, 38)
    return {"windows": len(Xc),
            "profile_correlation": float(np.corrcoef(a.mean(axis=0), b.mean(axis=0))[0, 1]),
            "per_window_feature_correlation": float(np.corrcoef(a.ravel(), b.ravel())[0, 1])}


def plot_question(path, title, explain, groups, features, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    present = [g for g in groups if results.get(g)]
    first = results[present[0]]
    order = np.argsort(-np.asarray(first["mean_abs_shap"]))[:12][::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    height = 0.8 / len(present)
    for i, g in enumerate(present):  # first group on top within each feature, matching the legend order
        vals = np.asarray(results[g]["mean_shap"])[order]
        ax.barh(np.arange(len(order)) + (len(present) - 1 - i) * height, vals, height=height, label=g)
    ax.set_yticks(np.arange(len(order)) + 0.4 - height / 2)
    ax.set_yticklabels([features[j] for j in order])
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel(f"mean SHAP value toward P({explain})  (summed over the {SEQ_LEN} rows)")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def format_question(qkey, q, features, results, totals, base):
    groups = [g[0] for g in q["groups"]]
    lines = ["-" * 78, f"{qkey.upper()}: {q['title']}", "-" * 78,
             f"Explained output: probability of {q['explain']} "
             f"(background mean {base:.3f}; SHAP values push a window above or below it)", "",
             f"  {'group':<52}{'windows':>14}{'mean P':>8}{'gap':>8}{'SHAP sum':>10}{'error':>8}"]
    for g in groups:
        r = results.get(g)
        if r is None:
            lines.append(f"  {g:<52}{'0 - none':>14}")
            continue
        lines.append(f"  {g:<52}{r['n']:>6} of {totals[g]:<7,}{r['mean_output']:>6.3f}"
                     f"{r['mean_gap']:>+8.3f}{r['mean_shap_sum']:>+10.3f}{r['additivity_abs_error']:>8.3f}")
    present = [g for g in groups if results.get(g)]
    if not present or present[0] != groups[0]:
        return lines + ["", "  The error group has no windows; nothing to explain.", ""]

    err = np.asarray(results[groups[0]]["mean_shap"])
    lines += ["", "  Similarity of the error's SHAP profile to each group (cosine; 1 = same features, same direction):"]
    for g in present[1:]:
        lines.append(f"    {g:<52}{cosine(err, np.asarray(results[g]['mean_shap'])):>7.3f}")

    order = np.argsort(-np.asarray(results[groups[0]]["mean_abs_shap"]))[:TOP_FEATURES]
    short = [f"G{i + 1}" for i in range(len(present))]
    lines += ["", "  " + "   ".join(f"{s} = {g}" for s, g in zip(short, present)), "",
              f"  Top {TOP_FEATURES} features of the error group (by mean |SHAP|):",
              f"  {'feature':<14}" + "".join(f"{'SHAP ' + s:>11}" for s in short)
              + "   " + "".join(f"{'value ' + s:>13}" for s in short)]
    for j in order:
        lines.append(f"  {features[j]:<14}" + "".join(f"{results[g]['mean_shap'][j]:>11.4f}" for g in present)
                     + "   " + "".join(f"{results[g]['median_raw_value'][j]:>13.4g}" for g in present))
    lines += ["  (SHAP: mean over windows, summed over the 20 rows; value: median of each window's mean raw value)", ""]
    return lines


def main():
    parser = argparse.ArgumentParser(description="SHAP analysis of the MU-IoT model's main errors")
    parser.add_argument("--data-dir", required=True, help="MU-IoT package folder (on Drive)")
    parser.add_argument("--local-dir", default="/content/mu_iot_data")
    parser.add_argument("--model", default="model/artifacts/mu_iot/best.keras")
    parser.add_argument("--scaler", default="model/artifacts/mu_iot/scaler_38.pkl")
    parser.add_argument("--output-dir", default="model/results/mu_iot")
    parser.add_argument("--per-group", type=int, default=200, help="Windows explained per group")
    parser.add_argument("--nsamples", type=int, default=500, help="Expected-gradients samples per window")
    parser.add_argument("--background-per-class", type=int, default=50)
    parser.add_argument("--shap-check-windows", type=int, default=10, help="0 skips the shap-library check")
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import tensorflow as tf
    from tensorflow import keras

    tf.get_logger().setLevel("ERROR")  # shap's own gradient function warns about retracing
    pkg = load_package(stage_data(args.data_dir, args.local_dir))
    validate_package(pkg)
    name_to_id, features = pkg["name_to_id"], pkg["features"]
    with open(repo_path("model/artifacts/mu_iot/label_mapping.json")) as f:
        if json.load(f) != name_to_id:
            raise SystemExit("Package label mapping differs from the model's label mapping")
    with open(repo_path("model/artifacts/mu_iot/feature_list_38.json")) as f:
        if json.load(f) != features:
            raise SystemExit("Package feature list differs from the model's feature list")
    with open(repo_path(args.scaler), "rb") as f:
        scaler = pickle.load(f)
    model = keras.models.load_model(repo_path(args.model), compile=False)
    windows, _ = build_windows(pkg, SEQ_LEN)
    rng = np.random.default_rng(args.seed)

    bg_view = sample_per_class(split_view(windows, "train"), args.background_per_class, rng, shuffle=False)
    background = gather(pkg["X"], bg_view["starts"])
    print(f"[+] Background: {len(background)} training windows ({args.background_per_class} per class)")

    views, preds = {}, {}
    for track in ("test_within", "test_heldout"):
        views[track] = split_view(windows, track)
        preds[track] = predict_probs(model, pkg["X"], views[track]["starts"], SEQ_LEN, args.batch_size).argmax(axis=1)
        print(f"[+] Predicted {len(preds[track]):,} {track} windows")

    explainer = ExpectedGradients(model, background, args.nsamples, args.seed)
    results, totals, check = {}, {}, None
    for qkey, q in QUESTIONS.items():
        k = name_to_id[q["explain"]]
        results[qkey], totals[qkey] = {}, {}
        for label, track, true_name, pred_name, session in q["groups"]:
            v = views[track]
            mask = (v["labels"] == name_to_id[true_name]) & (preds[track] == name_to_id[pred_name])
            if session:
                mask &= v["session"] == session
            idx = np.flatnonzero(mask)
            totals[qkey][label] = int(len(idx))
            if len(idx) == 0:
                results[qkey][label] = None
                print(f"[!] {qkey}: no windows for '{label}'")
                continue
            idx = np.sort(rng.choice(idx, min(args.per_group, len(idx)), replace=False))
            Xg = gather(pkg["X"], v["starts"][idx])
            t0 = time.time()
            r, sv = explain_group(explainer, model, scaler, Xg, k)
            r["n"] = int(len(idx))
            results[qkey][label] = r
            print(f"[+] {qkey}: '{label}' - {len(idx)} windows in {time.time() - t0:.0f} s, "
                  f"gap {r['mean_gap']:+.3f}, additivity error {r['additivity_abs_error']:.3f}")
            if check is None and args.shap_check_windows > 0:
                m = min(args.shap_check_windows, len(Xg))
                check = shap_library_check(model, background, Xg[:m], k, sv[:m], args.nsamples)
                check["group"] = f"{qkey}: {label}"
                print(f"[+] shap library check: {check}")

    out_dir = repo_path(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    lines = [
        "=" * 78, "MU-IoT CNN-LSTM - SHAP ANALYSIS OF THE MAIN ERRORS", "=" * 78,
        f"Generated  : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Model      : {args.model}",
        f"Method     : expected gradients (the shap.GradientExplainer estimator), {args.nsamples} samples per window",
        f"Background : {len(background)} real training windows, {args.background_per_class} per class",
        f"Windows    : up to {args.per_group} per group, chosen at random (seed {args.seed})",
    ]
    if check and "skipped" not in check:
        lines.append(f"Check      : vs shap.GradientExplainer on {check['windows']} windows ({check['group']}): "
                     f"feature-profile r = {check['profile_correlation']:.3f}, "
                     f"per-window r = {check['per_window_feature_correlation']:.3f}")
    elif check:
        lines.append(f"Check      : shap-library comparison {check['skipped']}")
    lines += ["Additivity : 'gap' = mean output minus the background mean; 'SHAP sum' = mean of each",
              "             window's summed SHAP values, which must match the gap (the group averages",
              "             the findings rest on). 'error' = mean |SHAP sum - gap| per window, the",
              "             sampling noise of single-window explanations. All in probability units.", ""]
    for qkey, q in QUESTIONS.items():
        groups = [g[0] for g in q["groups"]]
        lines += format_question(qkey, q, features, results[qkey], totals[qkey], explainer.base[name_to_id[q["explain"]]])
        if results[qkey].get(groups[0]):
            plot_question(os.path.join(out_dir, f"mu_iot_shap_{qkey}.png"), q["title"], q["explain"],
                          groups, features, results[qkey])

    with open(os.path.join(out_dir, "mu_iot_shap_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(os.path.join(out_dir, "mu_iot_shap_values.json"), "w", encoding="utf-8") as f:
        json.dump({"features": features, "background_mean_output": dict(zip(
                       [pkg["id_to_name"][i] for i in range(len(explainer.base))], explainer.base.tolist())),
                   "shap_library_check": check, "group_totals": totals, "results": results}, f, indent=2)
    print("\n".join(lines))
    print(f"[+] Wrote mu_iot_shap_report.txt, mu_iot_shap_values.json and charts to {out_dir}")


if __name__ == "__main__":
    main()
