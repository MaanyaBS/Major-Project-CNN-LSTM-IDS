"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 04 - Merge Cleaned Datasets
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd

CLEANED_PATH = r"D:\Major_Project\dataset\cleaned"
MERGED_PATH = r"D:\Major_Project\dataset\merged"

os.makedirs(MERGED_PATH, exist_ok=True)

output_file = os.path.join(MERGED_PATH, "cicids2017_cleaned.csv")

csv_files = sorted(
    [f for f in os.listdir(CLEANED_PATH) if f.lower().endswith(".csv")]
)

print("=" * 80)
print("MERGING CLEANED DATASETS")
print("=" * 80)

first_file = True

for file in csv_files:

    print(f"Adding: {file}")

    file_path = os.path.join(CLEANED_PATH, file)

    df = pd.read_csv(file_path)

    df.to_csv(
        output_file,
        mode='w' if first_file else 'a',
        header=first_file,
        index=False
    )

    first_file = False

print("\nAll cleaned datasets merged successfully!")
print(f"Merged dataset saved at:\n{output_file}")