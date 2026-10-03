from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Major_Project\dataset\mu_iot\CSV")

TARGET_COLUMNS = [
    "SIP",
    "DIP",
    "HTTPRM_M",
    "RTSP_MM",
]

CHUNK_SIZE = 200_000

observed = {
    col: set()
    for col in TARGET_COLUMNS
}

print("=" * 70)
print("MU-IoT NON-NUMERIC VALUE INSPECTION")
print("=" * 70)

files = sorted(ROOT.rglob("*.csv"))

for file_index, filepath in enumerate(files, start=1):

    print(f"[{file_index}/{len(files)}] {filepath.name}")

    for chunk in pd.read_csv(
        filepath,
        usecols=TARGET_COLUMNS,
        chunksize=CHUNK_SIZE,
        low_memory=False
    ):

        for col in TARGET_COLUMNS:

            values = (
                chunk[col]
                .dropna()
                .astype(str)
                .str.strip()
            )

            # Keep only first 1000 distinct values
            # per column so memory remains small.
            if len(observed[col]) < 1000:
                observed[col].update(
                    values.unique()[:1000]
                )

print()
print("=" * 70)
print("OBSERVED VALUES")
print("=" * 70)

for col in TARGET_COLUMNS:

    print()
    print(f"{col}")
    print("-" * 50)
    print(f"Distinct values retained: {len(observed[col])}")

    values = sorted(observed[col])

    for value in values[:50]:
        print(repr(value))

    if len(values) > 50:
        print("... additional values omitted ...")