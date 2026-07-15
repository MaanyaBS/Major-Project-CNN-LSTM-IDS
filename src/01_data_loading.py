"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Dataset : CICIDS2017
Module  : 01 - Data Loading & Basic Information
Author  : Maanya & Team
==========================================================
"""

import os
import gc
import pandas as pd

DATASET_PATH = r"D:\Major_Project\dataset"

csv_files = sorted(
    [f for f in os.listdir(DATASET_PATH) if f.endswith(".csv")]
)

print("=" * 80)
print("CICIDS2017 DATASET INFORMATION")
print("=" * 80)

for file in csv_files:

    print("\n" + "=" * 80)
    print(f"Processing: {file}")
    print("=" * 80)

    file_path = os.path.join(DATASET_PATH, file)

    try:
        df = pd.read_csv(file_path, low_memory=False)

        print(f"Shape: {df.shape}")

        print("\nFirst 5 rows:")
        print(df.head())

        print("\nColumn Names:")
        print(df.columns.tolist())

        print("\nMissing Values:")
        print(df.isnull().sum().sum())

        print("\nClass Distribution:")
        print(df[" Label"].value_counts())

    except Exception as e:
        print(f"Error while reading {file}")
        print(e)

    finally:
        if 'df' in locals():
            del df
        gc.collect()

print("\nAll files processed successfully.")