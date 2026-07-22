"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 06 - Feature Selection
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

INPUT_FILE = r"D:\Major_Project\dataset\encoded\cicids2017_encoded.csv"
OUTPUT_FOLDER = r"D:\Major_Project\output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("=" * 80)
print("FEATURE SELECTION")
print("=" * 80)

print("\nLoading dataset...")

# Load data
df = pd.read_csv(INPUT_FILE)

print(f"Dataset Shape : {df.shape}")

# Split features and labels
X = df.drop("Label", axis=1)
y = df["Label"]

# Sample dataset for faster processing
print("\nSampling 100000 rows...")
sample = df.sample(n=100000, random_state=42)

X_sample = sample.drop("Label", axis=1)
y_sample = sample["Label"]

print("\nTraining Random Forest...")

rf = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)

rf.fit(X_sample, y_sample)

importance = pd.DataFrame({
    "Feature": X_sample.columns,
    "Importance": rf.feature_importances_
})

importance = importance.sort_values(
    by="Importance",
    ascending=False
)

output_file = os.path.join(
    OUTPUT_FOLDER,
    "feature_importance.csv"
)

importance.to_csv(output_file, index=False)

print("\nTop 20 Features\n")
print(importance.head(20))

print("\nSaved to:")
print(output_file)

print("\nFeature Selection Completed Successfully!")