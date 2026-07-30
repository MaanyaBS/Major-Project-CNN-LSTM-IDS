"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 06C - Feature Selection Report
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd

FEATURE_FILE = r"D:\Major_Project\output\feature_importance.csv"
OUTPUT_FOLDER = r"D:\Major_Project\output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("=" * 80)
print("FEATURE SELECTION REPORT")
print("=" * 80)

# Load feature importance
importance = pd.read_csv(FEATURE_FILE)

# Select top 20
top20 = importance.head(20)

# Save report
report_file = os.path.join(
    OUTPUT_FOLDER,
    "selected_features.csv"
)

top20.to_csv(report_file, index=False)

print("\nTop 20 Selected Features:\n")
print(top20)

print("\nReport Saved Successfully!")
print(report_file)