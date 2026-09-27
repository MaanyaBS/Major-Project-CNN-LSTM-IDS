from pathlib import Path
from collections import Counter
import pandas as pd

DATA_DIR = Path(r"D:\Major_Project\dataset\mu_iot\CSV")

TARGET_COLUMNS = ["SIP", "DIP", "HTTPRM_M", "RTSP_MM"]

counters = {col: Counter() for col in TARGET_COLUMNS}

print("=" * 70)
print("MU-IoT NON-NUMERIC FREQUENCY INSPECTION")
print("=" * 70)

files = sorted(DATA_DIR.rglob("*.csv"))

print(f"Files found: {len(files)}")

for i, filepath in enumerate(files, 1):

    print(f"[{i}/{len(files)}] {filepath.name}")

    try:
        df = pd.read_csv(filepath, usecols=lambda c: c in TARGET_COLUMNS)

        for col in TARGET_COLUMNS:
            if col in df.columns:
                values = (
                    df[col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                )

                values = values[values != ""]

                counters[col].update(values)

    except Exception as e:
        print(f"  ERROR: {e}")

print()
print("=" * 70)
print("NON-NUMERIC VALUE FREQUENCIES")
print("=" * 70)

for col in TARGET_COLUMNS:

    print()
    print(col)
    print("-" * 50)

    total = sum(counters[col].values())

    print(f"Non-missing/non-empty values: {total}")
    print(f"Distinct values: {len(counters[col])}")

    for value, count in counters[col].most_common():
        print(f"{value!r}: {count:,}")

print()
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)