"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 08A - Train Validation Test Split
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
print("TRAIN / VALIDATION / TEST SPLIT")
print("=" * 80)

print("\nLoading dataset...")

df = pd.read_csv(INPUT_FILE)

print("Dataset Shape :", df.shape)

X = df.drop("Label", axis=1)
y = df["Label"]

# 80% train+validation, 20% test
X_trainval, X_test, y_trainval, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# From the 80%, split into 70% train and 10% validation
X_train, X_val, y_train, y_val = train_test_split(
    X_trainval,
    y_trainval,
    test_size=0.125,   # 10% of total data
    random_state=42,
    stratify=y_trainval
)

print("\nSaving datasets...")

X_train.to_csv(os.path.join(OUTPUT_FOLDER, "X_train.csv"), index=False)
X_val.to_csv(os.path.join(OUTPUT_FOLDER, "X_val.csv"), index=False)
X_test.to_csv(os.path.join(OUTPUT_FOLDER, "X_test.csv"), index=False)

y_train.to_csv(os.path.join(OUTPUT_FOLDER, "y_train.csv"), index=False)
y_val.to_csv(os.path.join(OUTPUT_FOLDER, "y_val.csv"), index=False)
y_test.to_csv(os.path.join(OUTPUT_FOLDER, "y_test.csv"), index=False)

print("\nTrain Shape      :", X_train.shape)
print("Validation Shape :", X_val.shape)
print("Test Shape       :", X_test.shape)

print("\nCompleted Successfully!")