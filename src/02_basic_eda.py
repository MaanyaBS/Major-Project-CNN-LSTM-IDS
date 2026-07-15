"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 02 - Basic EDA
Author  : Maanya & Team
==========================================================
"""

import os
import gc
import numpy as np
import pandas as pd

DATASET_PATH = r"D:\Major_Project\dataset"
OUTPUT_PATH = r"D:\Major_Project\output"

os.makedirs(OUTPUT_PATH, exist_ok=True)

csv_files = sorted(
    [f for f in os.listdir(DATASET_PATH) if f.lower().endswith(".csv")]
)

summary = []

print("=" * 80)
print("BASIC EDA")
print("=" * 80)

for file in csv_files:

    print(f"\nProcessing: {file}")

    file_path = os.path.join(DATASET_PATH, file)

    try:

        rows = 0
        columns = 0
        missing = 0
        duplicates = 0
        infinite = 0

        for chunk in pd.read_csv(file_path, chunksize=50000):

            rows += len(chunk)

            columns = len(chunk.columns)

            missing += chunk.isnull().sum().sum()

            duplicates += chunk.duplicated().sum()

            numeric = chunk.select_dtypes(include=[np.number])

            infinite += np.isinf(numeric).sum().sum()

        summary.append({
            "File": file,
            "Rows": rows,
            "Columns": columns,
            "Missing Values": int(missing),
            "Duplicate Rows": int(duplicates),
            "Infinite Values": int(infinite)
        })

        print(f"Rows        : {rows:,}")
        print(f"Columns     : {columns}")
        print(f"Missing     : {missing}")
        print(f"Duplicates  : {duplicates}")
        print(f"Infinities  : {infinite}")

        gc.collect()

    except Exception as e:

        print(f"Error processing {file}")
        print(e)

summary_df = pd.DataFrame(summary)

summary_df.to_csv(
    os.path.join(OUTPUT_PATH, "dataset_summary.csv"),
    index=False
)

print("\nEDA Completed Successfully!")