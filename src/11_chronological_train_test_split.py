"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 11 - Chronological Train Test Split
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd

# --------------------------------------------------------
# Paths
# --------------------------------------------------------

INPUT_FILE = r"D:\Major_Project\dataset\merged\cicids2017_cleaned_with_day.csv"

OUTPUT_FOLDER = r"D:\Major_Project\dataset\training_chrono"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --------------------------------------------------------
# Selected Top-20 Features
# --------------------------------------------------------

FEATURES = [
    "Destination Port",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
    "Fwd Packet Length Mean",
    "Bwd Packet Length Max",
    "Bwd Packet Length Mean",
    "Bwd Packet Length Std",
    "Flow IAT Max",
    "Fwd IAT Std",
    "Max Packet Length",
    "Packet Length Mean",
    "Packet Length Std",
    "Packet Length Variance",
    "Average Packet Size",
    "Avg Fwd Segment Size",
    "Avg Bwd Segment Size",
    "Subflow Fwd Packets",
    "Subflow Fwd Bytes",
    "Subflow Bwd Bytes"
]

print("=" * 80)
print("CHRONOLOGICAL TRAIN TEST SPLIT")
print("=" * 80)

print("\nLoading Dataset...")

df = pd.read_csv(INPUT_FILE)

print("Dataset Shape :", df.shape)

# --------------------------------------------------------
# Split each source_day separately
# --------------------------------------------------------

train_parts = []
test_parts = []

print("\nSplitting each source_day sequentially...\n")

for day in df["source_day"].unique():

    group = df[df["source_day"] == day].copy()

    split_index = int(len(group) * 0.80)

    train_group = group.iloc[:split_index]
    test_group = group.iloc[split_index:]

    train_parts.append(train_group)
    test_parts.append(test_group)

    print(f"{day}")
    print(f"  Total : {len(group)}")
    print(f"  Train : {len(train_group)}")
    print(f"  Test  : {len(test_group)}")

# --------------------------------------------------------
# Combine all groups
# --------------------------------------------------------

train_df = pd.concat(train_parts, ignore_index=True)
test_df = pd.concat(test_parts, ignore_index=True)

print("\nOverall Split")
print("Train :", train_df.shape)
print("Test  :", test_df.shape)

# --------------------------------------------------------
# Separate Features and Labels
# --------------------------------------------------------

X_train = train_df[FEATURES].copy()
X_test = test_df[FEATURES].copy()

# Keep source_day separately for future sequence creation
train_source = train_df[["source_day"]]
test_source = test_df[["source_day"]]

y_train = train_df["Label"]
y_test = test_df["Label"]

# --------------------------------------------------------
# Save Files
# --------------------------------------------------------

print("\nSaving datasets...")

X_train.to_csv(
    os.path.join(OUTPUT_FOLDER, "X_train_chrono.csv"),
    index=False
)

X_test.to_csv(
    os.path.join(OUTPUT_FOLDER, "X_test_chrono.csv"),
    index=False
)

y_train.to_csv(
    os.path.join(OUTPUT_FOLDER, "y_train_chrono.csv"),
    index=False
)

y_test.to_csv(
    os.path.join(OUTPUT_FOLDER, "y_test_chrono.csv"),
    index=False
)

train_source.to_csv(
    os.path.join(OUTPUT_FOLDER, "train_source_day.csv"),
    index=False
)

test_source.to_csv(
    os.path.join(OUTPUT_FOLDER, "test_source_day.csv"),
    index=False
)

print("\nSaved Files")
print("--------------------------------------------")
print("X_train_chrono.csv")
print("X_test_chrono.csv")
print("y_train_chrono.csv")
print("y_test_chrono.csv")
print("train_source_day.csv")
print("test_source_day.csv")

print("\nCompleted Successfully!")