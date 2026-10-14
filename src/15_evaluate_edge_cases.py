import os
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

MODEL_PATH = r"model\artifacts\cnn_lstm_best_v2.keras"
DATA_DIR = r"dataset\week6_edge_cases"
MAPPING_FILE = r"output\label_mapping.csv"
OUTPUT_DIR = r"model\results"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("WEEK 6 - EDGE-CASE CNN-LSTM EVALUATION")
print("=" * 70)

# Load data
X_edge = np.load(os.path.join(DATA_DIR, "X_edge.npy"))
y_edge = np.load(os.path.join(DATA_DIR, "y_edge.npy"))

mapping_df = pd.read_csv(MAPPING_FILE)
int_to_label = dict(zip(mapping_df["Encoded"], mapping_df["Attack"]))

class_names = [
    int_to_label[i] for i in sorted(int_to_label)
]

print("\nData:")
print("X_edge shape :", X_edge.shape)
print("y_edge shape :", y_edge.shape)

print("\nLoading trained model...")
model = load_model(MODEL_PATH)

print("Model loaded successfully.")

# Predict
print("\nRunning predictions...")
y_prob = model.predict(X_edge, verbose=1)
y_pred = np.argmax(y_prob, axis=1)

# Metrics
accuracy = accuracy_score(y_edge, y_pred)
f1_weighted = f1_score(
    y_edge, y_pred,
    average="weighted",
    zero_division=0
)
f1_macro = f1_score(
    y_edge, y_pred,
    average="macro",
    zero_division=0
)

report = classification_report(
    y_edge,
    y_pred,
    labels=sorted(int_to_label.keys()),
    target_names=class_names,
    zero_division=0
)

cm = confusion_matrix(
    y_edge,
    y_pred,
    labels=sorted(int_to_label.keys())
)

print("\n" + "=" * 70)
print("EDGE-CASE RESULTS")
print("=" * 70)

print(f"Accuracy         : {accuracy:.6f}")
print(f"F1-score (wt.)   : {f1_weighted:.6f}")
print(f"F1-score (macro) : {f1_macro:.6f}")

print("\nClassification Report:")
print(report)

print("\nConfusion Matrix:")
print(cm)

# Save results
output_path = os.path.join(
    OUTPUT_DIR,
    "week6_edge_case_results.txt"
)

with open(output_path, "w", encoding="utf-8") as f:
    f.write("=" * 70 + "\n")
    f.write("WEEK 6 - EDGE-CASE CNN-LSTM EVALUATION\n")
    f.write("=" * 70 + "\n\n")

    f.write(f"Edge-case samples: {len(y_edge)}\n")
    f.write(f"Accuracy         : {accuracy:.6f}\n")
    f.write(f"F1-score (wt.)   : {f1_weighted:.6f}\n")
    f.write(f"F1-score (macro) : {f1_macro:.6f}\n\n")

    f.write("Classification Report:\n")
    f.write(report)
    f.write("\nConfusion Matrix:\n")
    f.write(np.array2string(cm))
    f.write("\n")

print("\nResults saved to:")
print(output_path)

print("\nWeek 6 edge-case evaluation completed successfully!")
print("=" * 70)
