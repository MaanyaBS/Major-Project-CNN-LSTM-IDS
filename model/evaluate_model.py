"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : CICIDS2017 CNN-LSTM v2 Evaluation
Author  : Maanya B S, Ruthwik Sai Ganesh , Varshini D N
==========================================================
Evaluates the trained CICIDS2017 model (model/artifacts/cnn_lstm_best_v2.keras)
on the full chronological test set built by model/rebuild_chronological_split.py
and writes:

    model/results/cnn_lstm_v2_full_test_results.txt   metrics, per-class report,
                                                      confusion matrix
    model/results/cnn_lstm_v2_confusion_matrix.png    row-normalised heatmap

Usage (paths default to the repo layout, so it runs from any directory):

    python model/evaluate_model.py
    python model/evaluate_model.py --sequences-dir <folder with X_test_seq.npy, y_test_seq.npy>
"""

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def repo_path(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def display_path(path):
    return os.path.relpath(path, REPO).replace(os.sep, "/")


def load_class_names(label_mapping_path):
    with open(label_mapping_path) as f:
        label_to_int = json.load(f)
    id_to_name = {v: k for k, v in label_to_int.items()}
    return [id_to_name[i] for i in sorted(id_to_name)]


def evaluate(model_path, X_test, y_test, class_names, batch_size):
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from tensorflow import keras

    model = keras.models.load_model(model_path)
    preds = np.argmax(model.predict(X_test, batch_size=batch_size, verbose=1), axis=1)
    ids = list(range(len(class_names)))
    return {
        "accuracy": accuracy_score(y_test, preds),
        "weighted_f1": f1_score(y_test, preds, average="weighted", zero_division=0),
        "macro_f1": f1_score(y_test, preds, average="macro", zero_division=0),
        "report": classification_report(y_test, preds, labels=ids, target_names=class_names,
                                         zero_division=0),
        "confusion": confusion_matrix(y_test, preds, labels=ids),
    }


def format_report(res, class_names, args, n_test, test_shape):
    acc, wf1, mf1 = res["accuracy"], res["weighted_f1"], res["macro_f1"]
    lines = [
        "=" * 78,
        "CNN-LSTM v2 — FULL TEST SET EVALUATION RESULTS",
        "=" * 78,
        f"Generated : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Model     : {display_path(args.model)}",
        "Scaler    : model/artifacts/scaler_v2.pkl (applied when the test sequences were built)",
        "Test set  : model/rebuild_chronological_split.py output, full chronological",
        "            day+label stratified 80/20 split (CICIDS2017)",
        f"Test size : {n_test:,} sequences, shape {test_shape}",
        "=" * 78,
        "",
        "OVERALL METRICS",
        "-" * 78,
        f"Accuracy          : {acc:.4f}  ({acc * 100:.2f}%)",
        f"Weighted F1-score : {wf1:.4f}  ({wf1 * 100:.2f}%)",
        f"Macro F1-score    : {mf1:.4f}  ({mf1 * 100:.2f}%)",
        "",
        "Note: the large gap between weighted F1 and macro F1 is expected and",
        "documented — weighted F1 is dominated by BENIGN and large attack classes;",
        "macro F1 weights every class equally and exposes real weaknesses on rare,",
        "behavior-driven attack types (Bot, Web Attack - Brute Force/XSS). See",
        "model/MODEL_INTERFACE.md Section 6 (Known Limitations) for full detail.",
        "",
        "=" * 78,
        "PER-CLASS CLASSIFICATION REPORT",
        "-" * 78,
        res["report"],
        "=" * 78,
        "CONFUSION MATRIX",
        "-" * 78,
        "true\\pred".ljust(28) + "".join(f"{n[:10]:>12}" for n in class_names),
    ]
    for i, row in enumerate(res["confusion"]):
        lines.append(class_names[i][:26].ljust(28) + "".join(f"{v:>12,}" for v in row))
    lines.append("=" * 78)
    return "\n".join(lines)


def plot_confusion(cm, class_names, path):
    """Row-normalised, so each row shows where that class's samples went (its recall on the diagonal)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    row_totals = cm.sum(axis=1, keepdims=True)
    shares = np.divide(cm, row_totals, out=np.zeros(cm.shape, dtype=float), where=row_totals > 0)
    labels = [f"{n} (n={int(t):,})" for n, t in zip(class_names, row_totals.ravel())]

    fig, ax = plt.subplots(figsize=(15, 12))
    im = ax.imshow(shares, cmap="Blues", vmin=0, vmax=1)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Share of the true class")
    ax.set_xticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(class_names)))
    ax.set_yticklabels(labels, fontsize=9)
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            if shares[i, j] >= 0.005:
                ax.text(j, i, f"{shares[i, j]:.0%}", ha="center", va="center", fontsize=7,
                        color="white" if shares[i, j] > 0.5 else "black")
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class (test samples)")
    ax.set_title("CNN-LSTM v2 on CICIDS2017 — confusion matrix, row-normalised")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Evaluate the CICIDS2017 CNN-LSTM v2 model on the full test set")
    parser.add_argument("--model", default="model/artifacts/cnn_lstm_best_v2.keras")
    parser.add_argument("--label-mapping", default="model/artifacts/label_mapping_v2.json")
    parser.add_argument("--sequences-dir", default="datasets/verify_run_ruthwik",
                        help="Folder with X_test_seq.npy and y_test_seq.npy (not in git - rebuild with "
                             "model/rebuild_chronological_split.py or download from Drive)")
    parser.add_argument("--output-dir", default="model/results")
    parser.add_argument("--batch-size", type=int, default=2048)
    args = parser.parse_args()
    args.model = repo_path(args.model)
    args.label_mapping = repo_path(args.label_mapping)
    args.sequences_dir = repo_path(args.sequences_dir)
    args.output_dir = repo_path(args.output_dir)

    class_names = load_class_names(args.label_mapping)
    X_test = np.load(os.path.join(args.sequences_dir, "X_test_seq.npy"))
    y_test = np.load(os.path.join(args.sequences_dir, "y_test_seq.npy"))
    print(f"[+] Test set: {X_test.shape}, {len(class_names)} classes")

    res = evaluate(args.model, X_test, y_test, class_names, args.batch_size)
    report = format_report(res, class_names, args, len(y_test), X_test.shape)

    os.makedirs(args.output_dir, exist_ok=True)
    report_path = os.path.join(args.output_dir, "cnn_lstm_v2_full_test_results.txt")
    plot_path = os.path.join(args.output_dir, "cnn_lstm_v2_confusion_matrix.png")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    plot_confusion(res["confusion"], class_names, plot_path)

    print(report)
    print(f"\n[+] Saved {display_path(report_path)} and {display_path(plot_path)}")


if __name__ == "__main__":
    main()
