"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 06B - Select Top Features
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd

INPUT_FILE = r"D:\Major_Project\dataset\encoded\cicids2017_encoded.csv"
FEATURE_FILE = r"D:\Major_Project\output\feature_importance.csv"

OUTPUT_FOLDER = r"D:\Major_Project\dataset\processed"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

OUTPUT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "cicids2017_top20.csv"
)

print("=" * 80)
print("SELECTING TOP 20 FEATURES")
print("=" * 80)

# Load top 20 feature names
importance = pd.read_csv(FEATURE_FILE)
top_features = importance.head(20)["Feature"].tolist()

# Add Label column
columns_to_keep = top_features + ["Label"]

print("\nLoading dataset...")
df = pd.read_csv(INPUT_FILE, usecols=columns_to_keep)

print(f"Original Shape : {df.shape}")

print("\nSaving reduced dataset...")

df.to_csv(OUTPUT_FILE, index=False)

print("\nSaved Successfully!")

print(f"\nReduced Dataset : {OUTPUT_FILE}")
print(f"Final Shape     : {df.shape}")