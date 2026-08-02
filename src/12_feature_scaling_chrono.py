"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 12 - Chronological Feature Scaling
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler

TRAIN_FOLDER = r"D:\Major_Project\dataset\training_chrono"
MODEL_FOLDER = r"D:\Major_Project\models"

os.makedirs(MODEL_FOLDER, exist_ok=True)

print("=" * 80)
print("CHRONOLOGICAL FEATURE SCALING")
print("=" * 80)

print("\nLoading Chronological Training Data...")

X_train = pd.read_csv(os.path.join(TRAIN_FOLDER, "X_train_chrono.csv"))
X_test = pd.read_csv(os.path.join(TRAIN_FOLDER, "X_test_chrono.csv"))

print("Training Shape :", X_train.shape)
print("Testing Shape  :", X_test.shape)

print("\nFitting StandardScaler on TRAIN ONLY...")

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("\nSaving scaled datasets...")

pd.DataFrame(
    X_train_scaled,
    columns=X_train.columns
).to_csv(
    os.path.join(TRAIN_FOLDER, "X_train_chrono_scaled.csv"),
    index=False
)

pd.DataFrame(
    X_test_scaled,
    columns=X_test.columns
).to_csv(
    os.path.join(TRAIN_FOLDER, "X_test_chrono_scaled.csv"),
    index=False
)

joblib.dump(
    scaler,
    os.path.join(MODEL_FOLDER, "scaler_chrono.pkl")
)

print("\nFiles Created:")
print("-----------------------------------------")
print(os.path.join(TRAIN_FOLDER, "X_train_chrono_scaled.csv"))
print(os.path.join(TRAIN_FOLDER, "X_test_chrono_scaled.csv"))
print(os.path.join(MODEL_FOLDER, "scaler_chrono.pkl"))

print("\nCompleted Successfully!")