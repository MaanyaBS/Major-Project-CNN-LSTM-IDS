"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 07 - Class Distribution
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

INPUT_FILE = r"D:\Major_Project\dataset\processed\cicids2017_top20.csv"
OUTPUT_FOLDER = r"D:\Major_Project\output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("=" * 80)
print("CLASS DISTRIBUTION")
print("=" * 80)

print("\nLoading dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Dataset Shape : {df.shape}")

distribution = df["Label"].value_counts().sort_index()

print("\nClass Distribution:\n")
print(distribution)

distribution.to_csv(
    os.path.join(OUTPUT_FOLDER, "class_distribution.csv"),
    header=["Count"]
)

plt.figure(figsize=(10,6))

distribution.plot(kind="bar")

plt.title("Class Distribution")
plt.xlabel("Encoded Label")
plt.ylabel("Number of Samples")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_FOLDER, "class_distribution.png"),
    dpi=300
)

plt.close()

print("\nSaved Successfully!")
print(os.path.join(OUTPUT_FOLDER, "class_distribution.csv"))
print(os.path.join(OUTPUT_FOLDER, "class_distribution.png"))