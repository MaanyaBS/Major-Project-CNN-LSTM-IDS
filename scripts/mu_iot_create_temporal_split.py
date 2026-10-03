import pandas as pd
import numpy as np

# ============================================================
# PATHS
# ============================================================

DATA_PATH = r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv"

OUTPUT_PATH = (
    r"D:\Major_Project\dataset\processed\mu_iot"
    r"\mu_iot_temporal_split_assignment.csv"
)

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15


# ============================================================
# LOAD REQUIRED COLUMNS
# ============================================================

print("=" * 70)
print("MU-IoT TEMPORAL SPLIT CREATION")
print("=" * 70)

print("\nLoading category and capture_session...")

df = pd.read_csv(
    DATA_PATH,
    usecols=["category", "capture_session"]
)

df.insert(
    0,
    "row_id",
    np.arange(len(df), dtype=np.int64)
)

print(f"Total rows: {len(df):,}")
print(f"Sessions: {df['capture_session'].nunique()}")
print(f"Categories: {df['category'].nunique()}")


# ============================================================
# CREATE TEMPORAL SPLIT
# ============================================================

split = np.empty(
    len(df),
    dtype=object
)

print("\nCreating chronological 70/15/15 split...")


for session_name, group in df.groupby(
    "capture_session",
    sort=False
):

    indices = group.index.to_numpy()

    n = len(indices)

    train_end = int(n * TRAIN_RATIO)

    val_end = train_end + int(n * VAL_RATIO)

    split[indices[:train_end]] = "train"

    split[indices[train_end:val_end]] = "validation"

    split[indices[val_end:]] = "test"


df["split"] = split


# ============================================================
# VERIFY
# ============================================================

print("\nChecking split assignment...")

if df["split"].isna().any():
    raise ValueError(
        "Some rows do not have a split assignment."
    )

counts = df["split"].value_counts()

print("\nOverall split counts:")

print(counts)


# ============================================================
# CLASS × SPLIT
# ============================================================

print("\nClass × split counts:")

class_split = pd.crosstab(
    df["category"],
    df["split"]
)

print(class_split)


# ============================================================
# SESSION × SPLIT
# ============================================================

print("\nChecking sessions...")

session_split = pd.crosstab(
    df["capture_session"],
    df["split"]
)

print(
    f"Sessions: {len(session_split):,}"
)


# ============================================================
# CHECK TEMPORAL ORDER
# ============================================================

print("\nChecking chronological ordering...")

violations = 0

order = {
    "train": 0,
    "validation": 1,
    "test": 2
}

for session_name, group in df.groupby(
    "capture_session",
    sort=False
):

    values = group["split"].map(order).to_numpy()

    if np.any(np.diff(values) < 0):
        violations += 1


print(
    f"Sessions with chronological violations: {violations}"
)

if violations != 0:
    raise ValueError(
        "Temporal ordering violation detected."
    )


# ============================================================
# SAVE
# ============================================================

df[
    ["row_id", "category", "capture_session", "split"]
].to_csv(
    OUTPUT_PATH,
    index=False
)

print("\nSaved:")
print(OUTPUT_PATH)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("TEMPORAL SPLIT COMPLETE")
print("=" * 70)

for split_name in ["train", "validation", "test"]:

    n = (df["split"] == split_name).sum()

    print(
        f"{split_name:12s}: "
        f"{n:,} rows "
        f"({n / len(df) * 100:.2f}%)"
    )

print("=" * 70)