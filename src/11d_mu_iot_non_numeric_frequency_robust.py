from pathlib import Path
from collections import Counter
import csv

ROOT = Path(r"D:\Major_Project\dataset\mu_iot\CSV")

TARGET_COLUMNS = ["SIP", "DIP", "HTTPRM_M", "RTSP_MM"]

counters = {col: Counter() for col in TARGET_COLUMNS}
non_empty_counts = {col: 0 for col in TARGET_COLUMNS}

files_processed = 0
files_failed = []

print("=" * 80)
print("MU-IoT ROBUST NON-NUMERIC VALUE INSPECTION")
print("=" * 80)

csv_files = sorted(ROOT.rglob("*.csv"))

print(f"\nCSV files found: {len(csv_files)}")

for idx, file_path in enumerate(csv_files, start=1):

    print(f"\n[{idx}/{len(csv_files)}] {file_path.name}")

    try:
        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="replace",
            newline=""
        ) as f:

            reader = csv.reader(f)

            header = next(reader)

            # Remove BOM if present
            header = [
                col.strip().lstrip("\ufeff")
                for col in header
            ]

            column_index = {}

            for col in TARGET_COLUMNS:
                if col in header:
                    column_index[col] = header.index(col)

            missing = [
                col for col in TARGET_COLUMNS
                if col not in column_index
            ]

            if missing:
                print(f"  Missing target columns: {missing}")

            expected_columns = len(header)
            row_count = 0

            for row in reader:

                row_count += 1

                # Ignore structurally malformed rows
                if len(row) != expected_columns:
                    continue

                for col, col_idx in column_index.items():

                    value = row[col_idx].strip()

                    if value != "":
                        counters[col][value] += 1
                        non_empty_counts[col] += 1

            files_processed += 1

            print(f"  Rows read: {row_count}")

    except Exception as e:

        files_failed.append(
            (str(file_path), str(e))
        )

        print(f"  ERROR: {e}")


print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)

print(f"\nFiles successfully processed: {files_processed}")
print(f"Files failed: {len(files_failed)}")

for col in TARGET_COLUMNS:

    print("\n" + "-" * 80)
    print(f"{col}")
    print("-" * 80)

    print(f"Non-empty values: {non_empty_counts[col]}")
    print(f"Distinct values: {len(counters[col])}")

    print("\nTop 30 values:")

    for value, count in counters[col].most_common(30):
        print(f"  {repr(value):40} {count:,}")


if files_failed:

    print("\n" + "=" * 80)
    print("FAILED FILES")
    print("=" * 80)

    for file_path, error in files_failed:
        print(f"\n{file_path}")
        print(f"  {error}")