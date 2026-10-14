from pathlib import Path
import pandas as pd
import numpy as np
from collections import Counter

ROOT = Path(r"D:\Major_Project\dataset\mu_iot\CSV")
OUTPUT_DIR = Path(r"D:\Major_Project\output\mu_iot")

CHUNK_SIZE = 200_000

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

csv_files = sorted(ROOT.rglob("*.csv"))

print("=" * 70)
print("MU-IoT SCHEMA AUDIT")
print("=" * 70)
print(f"Files found: {len(csv_files)}")

# ---------------------------------------------------------
# First file: determine complete schema
# ---------------------------------------------------------

first_file = csv_files[0]

sample = pd.read_csv(
    first_file,
    nrows=5,
    low_memory=False
)

columns = sample.columns.tolist()

print()
print(f"Columns found: {len(columns)}")
print()
print("Columns:")
for i, col in enumerate(columns, start=1):
    print(f"{i:3d}. {col}")

# ---------------------------------------------------------
# Audit accumulators
# ---------------------------------------------------------

column_types = {}
missing_counts = Counter()
infinite_counts = Counter()
unique_counts = Counter()
constant_values = {}

category_values = Counter()
label_values = Counter()
type_values = Counter()

numeric_columns = set()
nonnumeric_columns = set()

total_rows = 0

# ---------------------------------------------------------
# Process every file in chunks
# ---------------------------------------------------------

for file_index, filepath in enumerate(csv_files, start=1):

    print()
    print(
        f"[{file_index}/{len(csv_files)}] "
        f"{filepath.name}"
    )

    file_rows = 0

    for chunk in pd.read_csv(
        filepath,
        chunksize=CHUNK_SIZE,
        low_memory=False
    ):

        total_rows += len(chunk)
        file_rows += len(chunk)

        # -----------------------------
        # Missing values
        # -----------------------------

        missing = chunk.isna().sum()

        for col, count in missing.items():
            if count:
                missing_counts[col] += int(count)

        # -----------------------------
        # Numeric / non-numeric columns
        # -----------------------------

        for col in chunk.columns:

            series = chunk[col]

            if pd.api.types.is_numeric_dtype(series):

                numeric_columns.add(col)

                inf_count = int(
                    np.isinf(series).sum()
                )

                if inf_count:
                    infinite_counts[col] += inf_count

            else:
                nonnumeric_columns.add(col)

        # -----------------------------
        # Target values
        # -----------------------------

        if "category" in chunk.columns:
            values = (
                chunk["category"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            category_values.update(values.value_counts().to_dict())

        if "label" in chunk.columns:
            values = (
                chunk["label"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            label_values.update(values.value_counts().to_dict())

        if "type" in chunk.columns:
            values = (
                chunk["type"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            type_values.update(values.value_counts().to_dict())

    print(f"    Rows: {file_rows:,}")

# ---------------------------------------------------------
# Constant-column check
# ---------------------------------------------------------

print()
print("=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)

print(f"Total rows scanned: {total_rows:,}")
print(f"Total columns: {len(columns)}")

# Re-read each column with chunks to identify unique values.
# Only a small amount of information is retained.

column_unique_sets = {
    col: set()
    for col in columns
}

for file_index, filepath in enumerate(csv_files, start=1):

    for chunk in pd.read_csv(
        filepath,
        chunksize=CHUNK_SIZE,
        low_memory=False
    ):

        for col in columns:

            values = chunk[col].dropna()

            if len(column_unique_sets[col]) <= 100:

                column_unique_sets[col].update(
                    values.astype(str).unique()
                )

for col in columns:

    unique_counts[col] = len(column_unique_sets[col])

    if unique_counts[col] <= 1:
        constant_values[col] = list(
            column_unique_sets[col]
        )

# ---------------------------------------------------------
# Print missing values
# ---------------------------------------------------------

print()
print("MISSING VALUES")

missing_rows = [
    (col, count)
    for col, count in missing_counts.items()
    if count > 0
]

missing_rows.sort(
    key=lambda x: x[1],
    reverse=True
)

if missing_rows:
    for col, count in missing_rows:
        print(f"{col}: {count:,}")
else:
    print("No missing values found.")

# ---------------------------------------------------------
# Infinite values
# ---------------------------------------------------------

print()
print("INFINITE VALUES")

if infinite_counts:
    for col, count in infinite_counts.most_common():
        print(f"{col}: {count:,}")
else:
    print("No infinite values found.")

# ---------------------------------------------------------
# Non-numeric columns
# ---------------------------------------------------------

print()
print("NON-NUMERIC COLUMNS")

for col in columns:

    if col in nonnumeric_columns:
        print(col)

# ---------------------------------------------------------
# Constant columns
# ---------------------------------------------------------

print()
print("CONSTANT / NEAR-EMPTY COLUMNS")

if constant_values:

    for col, values in constant_values.items():
        print(
            f"{col}: "
            f"{values}"
        )

else:
    print("No constant columns found.")

# ---------------------------------------------------------
# Target distributions
# ---------------------------------------------------------

print()
print("CATEGORY VALUES")

for value, count in category_values.most_common():
    print(f"{value}: {count:,}")

print()
print("LABEL VALUES")

for value, count in label_values.most_common():
    print(f"{value}: {count:,}")

print()
print("TYPE VALUES")

for value, count in type_values.most_common():
    print(f"{value}: {count:,}")

# ---------------------------------------------------------
# Save summary
# ---------------------------------------------------------

summary = []

for col in columns:

    summary.append(
        {
            "column": col,
            "unique_values_observed": unique_counts[col],
            "missing_count": missing_counts.get(col, 0),
            "infinite_count": infinite_counts.get(col, 0),
            "is_numeric": col in numeric_columns,
            "is_constant": col in constant_values,
        }
    )

summary_df = pd.DataFrame(summary)

output_file = OUTPUT_DIR / "mu_iot_schema_audit.csv"

summary_df.to_csv(
    output_file,
    index=False
)

print()
print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print(f"Output: {output_file}")