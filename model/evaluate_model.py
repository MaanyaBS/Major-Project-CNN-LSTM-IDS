"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Model Evaluation & Results Export
Author  : Maanya & Team
==========================================================
Evaluates a trained Keras model, prints metrics, saves a
classification report and confusion-matrix heatmap to disk.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")                       # non-interactive backend
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)


def evaluate_model(model, X_test, y_test, class_names,
                   output_dir="model/results"):
    """
    Evaluate a trained Keras model and persist results.

    Outputs
    -------
    - Console  : accuracy, weighted F1, macro F1
    - Text file: full classification report + metrics
                 → <output_dir>/cnn_lstm_results.txt
    - PNG file : confusion-matrix heatmap
                 → <output_dir>/cnn_lstm_confusion_matrix.png

    Parameters
    ----------
    model       : tf.keras.Model – trained model with .predict()
    X_test      : np.ndarray     – test features (3-D for CNN-LSTM)
    y_test      : np.ndarray     – true integer-encoded labels
    class_names : list[str]      – human-readable class names
    output_dir  : str            – directory for saved artefacts
    """

    os.makedirs(output_dir, exist_ok=True)

    # ---- Predict ----
    y_prob = model.predict(X_test)
    y_pred = np.argmax(y_prob, axis=1)

    # ---- Metrics ----
    acc        = accuracy_score(y_test, y_pred)
    f1_wt      = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    f1_macro   = f1_score(y_test, y_pred, average="macro",    zero_division=0)
    report     = classification_report(
        y_test, y_pred,
        target_names=class_names,
        zero_division=0,
    )
    cm = confusion_matrix(y_test, y_pred)

    # ---- Console summary ----
    print("=" * 70)
    print("CNN-LSTM EVALUATION RESULTS")
    print("=" * 70)
    print(f"Accuracy         : {acc:.6f}")
    print(f"F1-score (wt.)   : {f1_wt:.6f}")
    print(f"F1-score (macro) : {f1_macro:.6f}")
    print(f"\nClassification Report:\n{report}")
    print(f"Confusion Matrix:\n{cm}")
    print("=" * 70)

    # ---- Save text report ----
    results_text = (
        "=" * 70 + "\n"
        "CNN-LSTM EVALUATION RESULTS\n"
        "=" * 70 + "\n\n"
        f"Accuracy         : {acc:.6f}\n"
        f"Precision (wt.)  : —  (see per-class report below)\n"
        f"Recall    (wt.)  : —  (see per-class report below)\n"
        f"F1-score  (wt.)  : {f1_wt:.6f}\n"
        f"F1-score  (macro): {f1_macro:.6f}\n\n"
        f"Classification Report:\n{report}\n\n"
        f"Confusion Matrix:\n{cm}\n"
        "=" * 70 + "\n"
    )

    txt_path = os.path.join(output_dir, "cnn_lstm_results.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(results_text)
    print(f"\nResults saved to : {txt_path}")

    # ---- Save confusion-matrix heatmap (matplotlib only) ----
    fig, ax = plt.subplots(figsize=(max(8, len(class_names)),
                                    max(6, len(class_names) * 0.8)))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.set_title("CNN-LSTM Confusion Matrix", fontsize=14, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    tick_marks = np.arange(len(class_names))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(class_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(class_names, fontsize=8)

    # Annotate each cell
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], "d"),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontsize=7)

    ax.set_ylabel("True Label")
    ax.set_xlabel("Predicted Label")
    fig.tight_layout()

    png_path = os.path.join(output_dir, "cnn_lstm_confusion_matrix.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    print(f"Heatmap saved to : {png_path}")


# ------------------------------------------------------------------
# Smoke test: end-to-end with dummy data
# ------------------------------------------------------------------
if __name__ == "__main__":

    # Ensure project root is on sys.path
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from model.cnn_lstm_architecture import build_cnn_lstm_model
    from model.sequence_reshaping import create_sequences

    # ---- Dummy data ----
    np.random.seed(42)
    dummy_data   = np.random.rand(1000, 20).astype("float32")
    dummy_labels = np.random.randint(0, 15, size=(1000,))

    # ---- Reshape into sequences ----
    sequence_length = 10
    X, y = create_sequences(dummy_data, dummy_labels, sequence_length)
    print(f"Sequences: X={X.shape}, y={y.shape}")

    # ---- Train / test split (no shuffle — sequential data) ----
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    print(f"Train: {X_train.shape}  |  Test: {X_test.shape}")

    # ---- Build & quick-train ----
    class_names = ['BENIGN', 'Bot', 'DDoS', 'DoS GoldenEye', 'DoS Hulk',
                   'DoS Slowhttptest', 'DoS slowloris', 'FTP-Patator',
                   'Heartbleed', 'Infiltration', 'PortScan', 'SSH-Patator',
                   'Web Attack - Brute Force', 'Web Attack - Sql Injection',
                   'Web Attack - XSS']
    model = build_cnn_lstm_model(
        input_shape=(sequence_length, 20),
        num_classes=len(class_names),
    )

    model.fit(X_train, y_train, epochs=2, batch_size=32,
              validation_split=0.1, verbose=1)

    # ---- Evaluate ----
    evaluate_model(model, X_test, y_test, class_names,
                   output_dir="model/results")

    print("\nEvaluation module test completed successfully.")
