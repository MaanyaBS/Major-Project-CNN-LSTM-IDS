"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 06A - Correlation Heatmap
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

INPUT_FILE = r"D:\Major_Project\dataset\encoded\cicids2017_encoded.csv"
FEATURE_FILE = r"D:\Major_Project\output\feature_importance.csv"
OUTPUT_FOLDER = r"D:\Major_Project\output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("=" * 80)
print("CORRELATION HEATMAP")
print("=" * 80)

print("\nLoading feature importance...")

importance = pd.read_csv(FEATURE_FILE)

# Top 20 features
top_features = importance.head(20)["Feature"].tolist()

print("Loading sample dataset...")

# Sample 50,000 rows (enough for visualization)
df = pd.read_csv(INPUT_FILE).sample(n=50000, random_state=42)

corr = df[top_features].corr()

plt.figure(figsize=(14, 12))

plt.imshow(corr, interpolation='nearest')

plt.colorbar()

plt.xticks(range(len(top_features)), top_features, rotation=90)
plt.yticks(range(len(top_features)), top_features)

plt.title("Correlation Heatmap (Top 20 Features)")

plt.tight_layout()

output_file = os.path.join(
    OUTPUT_FOLDER,
    "correlation_heatmap.png"
)

plt.savefig(output_file, dpi=300)

plt.close()

print("\nCorrelation Heatmap Saved Successfully!")

print(output_file)