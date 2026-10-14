import os
import numpy as np
import pandas as pd

INPUT_DIR = r"dataset\week5_sequences"
OUTPUT_DIR = r"dataset\week6_edge_cases"
MAPPING_FILE = r"output\label_mapping.csv"

# Rare / weak classes to include in the edge-case set.
# Infiltration is intentionally excluded because Week 5 produced
# zero test sequences for it.
TARGET_CLASSES = [
    "Heartbleed",
    "Bot",
    "Web Attack - Sql Injection",
    "Web Attack - XSS",
    "Web Attack - Brute Force",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("WEEK 6 - EDGE-CASE TEST SET CREATION")
print("=" * 70)

print("\nLoading Week 5 test sequences...")

X_test = np.load(os.path.join(INPUT_DIR, "X_test_seq.npy"))
y_test = np.load(os.path.join(INPUT_DIR, "y_test_seq.npy"))

mapping_df = pd.read_csv(MAPPING_FILE)
label_to_int = dict(zip(mapping_df["Attack"], mapping_df["Encoded"]))
int_to_label = dict(zip(mapping_df["Encoded"], mapping_df["Attack"]))

print("X_test shape :", X_test.shape)
print("y_test shape :", y_test.shape)

target_ids = []

for class_name in TARGET_CLASSES:
    if class_name not in label_to_int:
        raise ValueError(f"Class not found in label mapping: {class_name}")
    target_ids.append(label_to_int[class_name])

target_ids = np.array(target_ids)

mask = np.isin(y_test, target_ids)

X_edge = X_test[mask]
y_edge = y_test[mask]

print("\nEdge-case classes:")
print("=" * 70)

counts = pd.Series(y_edge).value_counts().sort_index()

for class_id in target_ids:
    class_name = int_to_label[class_id]
    count = int(counts.get(class_id, 0))
    print(f"{class_id:2d}  {class_name:35s} {count:8d}")

print("\nEdge-case dataset shape:")
print("X_edge :", X_edge.shape)
print("y_edge :", y_edge.shape)

print("\nSanity checks:")
print("NaN :", np.isnan(X_edge).sum())
print("Inf :", np.isinf(X_edge).sum())

if len(X_edge) != len(y_edge):
    raise ValueError("X/y length mismatch!")

if np.isnan(X_edge).any() or np.isinf(X_edge).any():
    raise ValueError("NaN or Inf detected!")

np.save(os.path.join(OUTPUT_DIR, "X_edge.npy"), X_edge)
np.save(os.path.join(OUTPUT_DIR, "y_edge.npy"), y_edge)

print("\nSaved:")
print(os.path.join(OUTPUT_DIR, "X_edge.npy"))
print(os.path.join(OUTPUT_DIR, "y_edge.npy"))

print("\nNote:")
print("Infiltration is not included because its Week 5 test")
print("sequence count was 0 due to the known window-boundary issue.")

print("\nWeek 6 edge-case dataset created successfully!")
print("=" * 70)
