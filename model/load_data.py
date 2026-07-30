"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Data Loading & Cleaning (Chunk-based)
Author  : Maanya & Team
==========================================================
Loads cicids2017_cleaned.csv in chunks, keeping only
well-formed rows (69 columns) and removing inf/NaN values.
"""

import os
import sys
import numpy as np
import pandas as pd

# Windows console: avoid UnicodeEncodeError on special characters
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "datasets", "merged", "cicids2017_cleaned.csv"
)


def load_cleaned_data(csv_path=CSV_PATH, chunksize=100_000):
    """
    Load and clean the merged CICIDS2017 dataset.

    Steps:
        1. Read CSV in chunks to keep memory usage low.
        2. Keep only rows whose length matches the header (69 columns).
        3. Strip leading/trailing whitespace from column names.
        4. Replace inf / -inf with NaN, then drop rows containing NaN.
        5. Print final shape and label distribution.

    Returns:
        pd.DataFrame – cleaned DataFrame ready for modelling.
    """

    print("=" * 70)
    print("LOADING & CLEANING DATASET")
    print("=" * 70)
    print(f"Source : {csv_path}\n")

    # --- Pass 1: read header to know expected column count ---------------
    header_df = pd.read_csv(csv_path, nrows=0)
    expected_cols = len(header_df.columns)              # should be 69
    col_names = [c.strip() for c in header_df.columns]  # cleaned names
    print(f"Expected columns : {expected_cols}")

    # --- Pass 2: chunked read, filter, clean -----------------------------
    good_chunks = []
    total_read = 0
    malformed_dropped = 0

    reader = pd.read_csv(
        csv_path,
        chunksize=chunksize,
        header=0,
        on_bad_lines="skip",       # skip lines the parser cannot handle
        low_memory=False,
    )

    for i, chunk in enumerate(reader):
        total_read += len(chunk)

        # Keep only rows with exactly the right number of columns.
        # After pandas parsing, all rows have the same number of cols
        # *if* on_bad_lines="skip" is set, but some rows may have had
        # their last column (Label) parsed as NaN because the raw CSV
        # line was short.  We detect those by checking if Label is NaN.
        chunk.columns = [c.strip() for c in chunk.columns]

        # Rows where Label ended up NaN are the 68-column malformed rows
        before = len(chunk)
        chunk = chunk.dropna(subset=["Label"])
        malformed_dropped += (before - len(chunk))

        # Sanitise Label: cast to string, then replace unicode replacement char
        chunk["Label"] = chunk["Label"].astype(str).str.replace("\ufffd", "-", regex=False)

        # Replace infinities with NaN, then drop
        chunk.replace([np.inf, -np.inf], np.nan, inplace=True)
        chunk.dropna(inplace=True)

        good_chunks.append(chunk)

        if (i + 1) % 5 == 0:
            print(f"  ... processed {total_read:,} rows so far")

    df = pd.concat(good_chunks, ignore_index=True)

    print(f"\nTotal rows read        : {total_read:,}")
    print(f"Malformed rows dropped : {malformed_dropped:,}")
    print(f"Final cleaned shape    : {df.shape}")
    print(f"\nLabel distribution:")
    print(df["Label"].value_counts().to_string())
    print("=" * 70)

    return df


# --- Allow running as a standalone sanity-check script -------------------
if __name__ == "__main__":
    df = load_cleaned_data()
    print(f"\nDtypes:\n{df.dtypes}")
