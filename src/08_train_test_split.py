"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 08 - Train Test Split
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd
from sklearn.model_selection import train_test_split

INPUT_FILE = r"D:\Major_Project\dataset\processed\cicids2017_top20.csv"

OUTPUT_FOLDER = r"D:\Major_Project\dataset\training"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("=" * 80)
print("TRAIN TEST SPLIT")
print("=" * 80)

print("\nLoading dataset...")

df = pd.read_csv(INPUT_FILE)

print("Dataset Shape :", df.shape)

# --------------------------------------------------------
# Separate Features and Labels
# --------------------------------------------------------

X = df.drop("Label", axis=1)
y = df["Label"]

# --------------------------------------------------------
# Train-Test Split
# --------------------------------------------------------

print("\nSplitting dataset (80% Train, 20% Test)...")

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y,
    shuffle=True
)

# --------------------------------------------------------
# Save Files
# --------------------------------------------------------

print("\nSaving datasets...")

X_train.to_csv(
    os.path.join(OUTPUT_FOLDER, "X_train.csv"),
    index=False
)

X_test.to_csv(
    os.path.join(OUTPUT_FOLDER, "X_test.csv"),
    index=False
)

y_train.to_csv(
    os.path.join(OUTPUT_FOLDER, "y_train.csv"),
    index=False,
    header=["Label"]
)

y_test.to_csv(
    os.path.join(OUTPUT_FOLDER, "y_test.csv"),
    index=False,
    header=["Label"]
)

print("\nTrain Shape :", X_train.shape)
print("Test Shape  :", X_test.shape)

print("\ny_train :", y_train.shape)
print("y_test  :", y_test.shape)

print("\nCompleted Successfully!")