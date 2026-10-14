import pandas as pd

INPUT = r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv"
CHUNK_SIZE = 100_000

missing = None
total_rows = 0
category_counts = {}
session_counts = {}

print("=" * 80)
print("MU-IoT CLEANED DATASET VALIDATION")
print("=" * 80)

for i, chunk in enumerate(
    pd.read_csv(INPUT, chunksize=CHUNK_SIZE, low_memory=False),
    start=1
):
    total_rows += len(chunk)

    # Missing values
    chunk_missing = chunk.isna().sum()

    if missing is None:
        missing = chunk_missing
    else:
        missing = missing.add(chunk_missing, fill_value=0)

    # Category counts
    for value, count in chunk["category"].value_counts().items():
        category_counts[value] = category_counts.get(value, 0) + int(count)

    # Session counts
    for value, count in chunk["capture_session"].value_counts().items():
        session_counts[value] = session_counts.get(value, 0) + int(count)

    print(f"Processed chunk {i}: {total_rows:,} rows")

print("\n" + "=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)

print(f"\nTotal rows: {total_rows:,}")
print(f"Total columns: {len(missing)}")

print("\nClass distribution:")
for category, count in sorted(
    category_counts.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(f"  {category:<20} {count:,}")

print(f"\nNumber of capture sessions: {len(session_counts)}")

print("\nMissing values:")
missing = missing[missing > 0].sort_values(ascending=False)

if len(missing) == 0:
    print("  NONE")
else:
    for column, count in missing.items():
        print(f"  {column:<20} {int(count):,}")

print("\nString/object columns:")
df_sample = pd.read_csv(INPUT, nrows=5, low_memory=False)

for column in df_sample.columns:
    if df_sample[column].dtype == "object":
        print(f"  {column}")

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)