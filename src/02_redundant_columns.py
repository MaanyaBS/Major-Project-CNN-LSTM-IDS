"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 02 - Redundant Column Analysis
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd
import numpy as np

RAW_PATH = r"D:\Major_Project\dataset\raw"
OUTPUT_PATH = r"D:\Major_Project\output"

os.makedirs(OUTPUT_PATH, exist_ok=True)

csv_files = sorted(
    [f for f in os.listdir(RAW_PATH) if f.lower().endswith(".csv")]
)

report = []

print("=" * 80)
print("REDUNDANT COLUMN ANALYSIS")
print("=" * 80)

for file in csv_files:

    print(f"\nProcessing: {file}")

    file_path = os.path.join(RAW_PATH, file)

    try:
        # Read only first 5000 rows
        df = pd.read_csv(file_path, nrows=5000, low_memory=False)

        # Remove leading/trailing spaces from column names
        df.columns = df.columns.str.strip()

        for column in df.columns:

            # Skip Label column (Target variable)
            if column.lower() == "label":
                continue

            column_lower = column.lower()

            # --------------------------------------------------
            # Metadata Columns
            # --------------------------------------------------
            metadata_keywords = [
                "flow id",
                "source ip",
                "destination ip",
                "timestamp",
                "src ip",
                "dst ip"
            ]

            if any(keyword in column_lower for keyword in metadata_keywords):

                report.append({
                    "File": file,
                    "Column": column,
                    "Reason": "Metadata column (not useful for ML)"
                })

                continue

            # --------------------------------------------------
            # Constant Columns
            # --------------------------------------------------
            if df[column].nunique(dropna=False) == 1:

                report.append({
                    "File": file,
                    "Column": column,
                    "Reason": "Constant value"
                })

                continue

            # --------------------------------------------------
            # All Zero Numeric Columns
            # --------------------------------------------------
            if pd.api.types.is_numeric_dtype(df[column]):

                if (df[column].fillna(0) == 0).all():

                    report.append({
                        "File": file,
                        "Column": column,
                        "Reason": "All zero values"
                    })

    except Exception as e:
        print(f"Error processing {file}: {e}")

# Save report
report_df = pd.DataFrame(report)

report_file = os.path.join(
    OUTPUT_PATH,
    "redundant_columns_report.csv"
)

report_df.to_csv(report_file, index=False)

print("\n" + "=" * 80)
print("REDUNDANT COLUMN ANALYSIS COMPLETED")
print("=" * 80)
print(f"Report saved at:\n{report_file}")
print(f"\nTotal redundant columns identified: {len(report_df)}")