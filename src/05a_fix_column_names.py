import pandas as pd
import os

INPUT_FILE = r"D:\Major_Project\dataset\merged\cicids2017_cleaned.csv"
OUTPUT_FILE = r"D:\Major_Project\dataset\merged\cicids2017_cleaned_fixed.csv"

print("="*70)
print("FIXING COLUMN NAMES")
print("="*70)

first = True

for chunk in pd.read_csv(INPUT_FILE, chunksize=100000, low_memory=False):

    # Remove leading/trailing spaces from every column name
    chunk.columns = chunk.columns.str.strip()

    chunk.to_csv(
        OUTPUT_FILE,
        mode="w" if first else "a",
        index=False,
        header=first
    )

    first = False

print("\nDone!")
print(f"\nSaved to:\n{OUTPUT_FILE}")