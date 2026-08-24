import os
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support
)

MODEL_PATH = r"model\artifacts\cnn_lstm_best_v2.keras"
X_PATH = r"dataset\week6_edge_cases\X_edge.npy"
Y_PATH = r"dataset\week6_edge_cases\y_edge.npy"
MAPPING_PATH = r"output\label_mapping.csv"

REPORT_PATH = r"model\results\week7_edge_case_validation_report.txt"
CLASS_CSV = r"output\week7_edge_case_class_validation.csv"
CM_CSV = r"output\week7_edge_case_confusion_matrix.csv"

print("=" * 70)
print("WEEK 7 - CNN-LSTM PREDICTION VALIDATION")
print("=" * 70)

# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

X = np.load(X_PATH)
y_true = np.load(Y_PATH)

mapping = pd.read_csv(MAPPING_PATH)
id_to_label = dict(zip(mapping["Encoded"], mapping["Attack"]))
class_ids = mapping["Encoded"].astype(int).tolist()
class_names = [id_to_label[i] for i in class_ids]

print("\nData:")
print("X shape :", X.shape)
print("y shape :", y_true.shape)

# ------------------------------------------------------------
# Load model
# ------------------------------------------------------------

print("\nLoading trained CNN-LSTM model...")
model = load_model(MODEL_PATH)
print("Model loaded successfully.")

# ------------------------------------------------------------
# Predictions
# ------------------------------------------------------------

print("\nGenerating predictions...")
y_prob = model.predict(X, verbose=1)
y_pred = np.argmax(y_prob, axis=1)

# ------------------------------------------------------------
# Confusion matrix
# ------------------------------------------------------------

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=class_ids
)

# ------------------------------------------------------------
# Per-class statistics
# ------------------------------------------------------------

precision, recall, f1, support = precision_recall_fscore_support(
    y_true,
    y_pred,
    labels=class_ids,
    zero_division=0
)

rows = []

total = len(y_true)

for idx, class_id in enumerate(class_ids):

    tp = int(cm[idx, idx])

    fn = int(cm[idx, :].sum() - tp)

    fp = int(cm[:, idx].sum() - tp)

    tn = int(total - tp - fn - fp)

    detection_rate = (
        tp / (tp + fn)
        if (tp + fn) > 0
        else 0.0
    )

    rows.append({
        "Class_ID": class_id,
        "Class": id_to_label[class_id],
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "Precision": precision[idx],
        "Recall": recall[idx],
        "F1": f1[idx],
        "Support": int(support[idx]),
        "Detection_Rate": detection_rate
    })

results_df = pd.DataFrame(rows)

# ------------------------------------------------------------
# Overall metrics
# ------------------------------------------------------------

accuracy = np.mean(y_true == y_pred)

weighted_f1 = (
    np.average(f1, weights=support)
    if support.sum() > 0
    else 0.0
)

macro_f1 = np.mean(f1)

# ------------------------------------------------------------
# Attack -> BENIGN analysis
# ------------------------------------------------------------

benign_id = id_to_label.keys()

# BENIGN is expected to be encoded as 0.
benign_index = class_ids.index(0)

attack_to_benign = []

for idx, class_id in enumerate(class_ids):

    if class_id == 0:
        continue

    false_benign = int(cm[idx, benign_index])

    attack_support = int(support[idx])

    rate = (
        false_benign / attack_support
        if attack_support > 0
        else 0.0
    )

    attack_to_benign.append({
        "Attack": id_to_label[class_id],
        "Samples": attack_support,
        "Predicted_as_BENIGN": false_benign,
        "BENIGN_Misclassification_Rate": rate
    })

benign_errors_df = pd.DataFrame(attack_to_benign)

benign_errors_df = benign_errors_df.sort_values(
    "BENIGN_Misclassification_Rate",
    ascending=False
)

# ------------------------------------------------------------
# Save CSV reports
# ------------------------------------------------------------

os.makedirs("output", exist_ok=True)
os.makedirs("model/results", exist_ok=True)

results_df.to_csv(CLASS_CSV, index=False)

cm_df = pd.DataFrame(
    cm,
    index=class_names,
    columns=class_names
)

cm_df.to_csv(CM_CSV)

# ------------------------------------------------------------
# Full text report
# ------------------------------------------------------------

report = classification_report(
    y_true,
    y_pred,
    labels=class_ids,
    target_names=class_names,
    zero_division=0
)

with open(REPORT_PATH, "w", encoding="utf-8") as f:

    f.write("=" * 70 + "\n")
    f.write("WEEK 7 - CNN-LSTM PREDICTION VALIDATION\n")
    f.write("=" * 70 + "\n\n")

    f.write(f"Test samples: {total}\n")
    f.write(f"Accuracy: {accuracy:.6f}\n")
    f.write(f"Weighted F1: {weighted_f1:.6f}\n")
    f.write(f"Macro F1: {macro_f1:.6f}\n\n")

    f.write("=" * 70 + "\n")
    f.write("CLASSIFICATION REPORT\n")
    f.write("=" * 70 + "\n")
    f.write(report)
    f.write("\n\n")

    f.write("=" * 70 + "\n")
    f.write("PER-CLASS CONFUSION STATISTICS\n")
    f.write("=" * 70 + "\n")

    f.write(
        results_df.to_string(index=False)
    )

    f.write("\n\n")
    f.write("=" * 70 + "\n")
    f.write("ATTACKS MISCLASSIFIED AS BENIGN\n")
    f.write("=" * 70 + "\n")

    f.write(
        benign_errors_df.to_string(index=False)
    )

    f.write("\n\n")
    f.write("=" * 70 + "\n")
    f.write("WEEK 7 VALIDATION COMPLETED\n")
    f.write("=" * 70 + "\n")

print("\n" + "=" * 70)
print("WEEK 7 RESULTS")
print("=" * 70)

print(f"Accuracy    : {accuracy:.6f}")
print(f"Weighted F1 : {weighted_f1:.6f}")
print(f"Macro F1    : {macro_f1:.6f}")

print("\nTop attacks misclassified as BENIGN:")
print(
    benign_errors_df.head(10).to_string(index=False)
)

print("\nSaved:")
print(REPORT_PATH)
print(CLASS_CSV)
print(CM_CSV)

print("\nWeek 7 validation completed successfully!")
print("=" * 70)
