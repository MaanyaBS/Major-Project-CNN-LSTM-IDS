from pathlib import Path
import pandas as pd
import re

ROOT = Path(r"D:\Major_Project\dataset\mu_iot\CSV")
OUTPUT = Path(r"D:\Major_Project\output\mu_iot\mu_iot_boundary_decisions.csv")

CHUNK_SIZE = 200_000

# Based on the observed continuous numbered-file boundaries:
# Maximum observed continuous gap = 0.490653 seconds.
CONTINUOUS_GAP_THRESHOLD = 1.0


def get_boundary(filepath):
    first_fpt = None
    last_fpt = None
    categories = set()
    labels = set()

    for chunk in pd.read_csv(
        filepath,
        usecols=["FPT", "category", "label"],
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        fpt = pd.to_numeric(chunk["FPT"], errors="coerce").dropna()

        if not fpt.empty:
            if first_fpt is None:
                first_fpt = float(fpt.iloc[0])

            last_fpt = float(fpt.iloc[-1])

        categories.update(
            chunk["category"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

        labels.update(
            chunk["label"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

    return first_fpt, last_fpt, categories, labels


def group_key(filename):
    """
    Groups files that clearly belong to the same numbered sequence.

    Examples:
        bonesi_udp_0.csv -> bonesi_udp
        bonesi_udp_1.csv -> bonesi_udp
        hping3_udp_10.csv -> hping3_udp

    Non-numbered files remain their own group.
    """

    stem = Path(filename).stem

    match = re.match(r"^(.*)_(\d+)$", stem)

    if match:
        return match.group(1)

    # Handle special naming patterns:
    # Botnet_HTTP_Flood.csv / Botnet_HTTP_Flood1.csv
    # XSS_Injection.csv / XSS_Injection1.csv
    # Scan_Recon1.csv / Scan_Recon2.csv

    match = re.match(r"^(.*?)(\d+)$", stem)

    if match:
        return match.group(1)

    return stem


# ---------------------------------------------------------
# Find all CSV files
# ---------------------------------------------------------

files = sorted(ROOT.rglob("*.csv"))

print(f"Found {len(files)} CSV files.")

# ---------------------------------------------------------
# Collect boundaries
# ---------------------------------------------------------

records = []

for i, filepath in enumerate(files, start=1):

    print(f"[{i}/{len(files)}] Processing {filepath.name}")

    first_fpt, last_fpt, categories, labels = get_boundary(filepath)

    records.append(
        {
            "filepath": str(filepath),
            "filename": filepath.name,
            "relative_path": str(filepath.relative_to(ROOT)),
            "group": group_key(filepath.name),
            "first_fpt": first_fpt,
            "last_fpt": last_fpt,
            "categories": "|".join(sorted(categories)),
            "labels": "|".join(sorted(labels)),
        }
    )


df = pd.DataFrame(records)

# ---------------------------------------------------------
# Sort within each group by first timestamp
# ---------------------------------------------------------

df = df.sort_values(
    ["group", "first_fpt"],
    na_position="last"
).reset_index(drop=True)

# ---------------------------------------------------------
# Determine relationship with next file
# ---------------------------------------------------------

results = []

for group, group_df in df.groupby("group", sort=False):

    group_df = group_df.reset_index(drop=True)

    for i, row in group_df.iterrows():

        if i == len(group_df) - 1:

            results.append(
                {
                    "group": group,
                    "filename": row["filename"],
                    "relative_path": row["relative_path"],
                    "next_filename": "",
                    "next_relative_path": "",
                    "first_fpt": row["first_fpt"],
                    "last_fpt": row["last_fpt"],
                    "next_first_fpt": None,
                    "gap_seconds": None,
                    "category_match": None,
                    "label_match": None,
                    "decision": "NO_SUCCESSOR",
                }
            )

            continue

        next_row = group_df.iloc[i + 1]

        gap = next_row["first_fpt"] - row["last_fpt"]

        category_match = row["categories"] == next_row["categories"]
        label_match = row["labels"] == next_row["labels"]

        if (
            gap >= 0
            and gap <= CONTINUOUS_GAP_THRESHOLD
            and category_match
            and label_match
        ):
            decision = "CONTINUOUS"

        else:
            decision = "SEPARATE_SESSION"

        results.append(
            {
                "group": group,
                "filename": row["filename"],
                "relative_path": row["relative_path"],
                "next_filename": next_row["filename"],
                "next_relative_path": next_row["relative_path"],
                "first_fpt": row["first_fpt"],
                "last_fpt": row["last_fpt"],
                "next_first_fpt": next_row["first_fpt"],
                "gap_seconds": gap,
                "category_match": category_match,
                "label_match": label_match,
                "decision": decision,
            }
        )


result_df = pd.DataFrame(results)

# ---------------------------------------------------------
# Save report
# ---------------------------------------------------------

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

result_df.to_csv(OUTPUT, index=False)

print()
print("=" * 70)
print("BOUNDARY INVESTIGATION COMPLETE")
print("=" * 70)
print(f"Files analyzed : {len(files)}")
print(f"Output         : {OUTPUT}")
print()

print("Decision counts:")
print(result_df["decision"].value_counts())

print()
print("Boundary report:")
print(result_df[
    [
        "group",
        "filename",
        "next_filename",
        "gap_seconds",
        "category_match",
        "label_match",
        "decision",
    ]
].to_string(index=False))