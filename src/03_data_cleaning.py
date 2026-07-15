"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 03 - Data Cleaning (Chunk Processing)
Author  : Maanya & Team
==========================================================
"""

import os
import numpy as np
import pandas as pd

RAW_PATH = r"D:\Major_Project\dataset\raw"
CLEANED_PATH = r"D:\Major_Project\dataset\cleaned"
OUTPUT_PATH = r"D:\Major_Project\output"

os.makedirs(CLEANED_PATH, exist_ok=True)
os.makedirs(OUTPUT_PATH, exist_ok=True)

summary = []

csv_files = sorted(
    [f for f in os.listdir(RAW_PATH) if f.lower().endswith(".csv")]
)

print("=" * 80)
print("DATA CLEANING")
print("=" * 80)

for file in csv_files:

    print(f"\nProcessing: {file}")

    file_path = os.path.join(RAW_PATH, file)

    cleaned_chunks = []

    original_rows = 0
    missing_removed = 0
    duplicate_removed = 0

    first_chunk = True
    constant_columns = []

    for chunk in pd.read_csv(file_path, chunksize=50000):

        original_rows += len(chunk)

        # Replace infinities
        chunk.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Count missing values
        missing_removed += chunk.isnull().sum().sum()

        # Remove missing rows
        chunk.dropna(inplace=True)

        # Count duplicates
        duplicate_removed += chunk.duplicated().sum()

        # Remove duplicates
        chunk.drop_duplicates(inplace=True)

        # Find constant columns only once
        if first_chunk:
            constant_columns = [
                col for col in chunk.columns
                if chunk[col].nunique() == 1
            ]
            first_chunk = False

        chunk.drop(columns=constant_columns, inplace=True)

        cleaned_chunks.append(chunk)

    cleaned_df = pd.concat(cleaned_chunks, ignore_index=True)

    output_file = os.path.join(CLEANED_PATH, file)
    cleaned_df.to_csv(output_file, index=False)

    summary.append({
        "File": file,
        "Original Rows": original_rows,
        "Cleaned Rows": len(cleaned_df),
        "Missing Values Removed": int(missing_removed),
        "Duplicate Rows Removed": int(duplicate_removed),
        "Constant Columns Removed": len(constant_columns)
    })

    print(f"Original Rows : {original_rows:,}")
    print(f"Cleaned Rows  : {len(cleaned_df):,}")

summary_df = pd.DataFrame(summary)

summary_df.to_csv(
    os.path.join(OUTPUT_PATH, "cleaning_report.csv"),
    index=False
)

print("\nCleaning Completed Successfully!")