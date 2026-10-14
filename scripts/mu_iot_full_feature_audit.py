import pandas as pd
import numpy as np
from pathlib import Path

INPUT = Path(r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv")
OUTPUT = Path(r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_full_feature_audit.csv")

CHUNK_SIZE = 250_000

print("=" * 90)
print("MU-IoT FULL FEATURE AUDIT")
print("=" * 90)
print(f"Input : {INPUT}")
print(f"Output: {OUTPUT}")
print()

# ---------------------------------------------------------------------
# First read: column names and dtypes
# ---------------------------------------------------------------------
header = pd.read_csv(INPUT, nrows=0)

columns = list(header.columns)

print(f"Total columns: {len(columns)}")
print()

# ---------------------------------------------------------------------
# Initialize statistics
# ---------------------------------------------------------------------
stats = {}

for col in columns:
    stats[col] = {
        "column": col,
        "dtype": None,
        "total_rows": 0,
        "missing": 0,
        "positive_inf": 0,
        "negative_inf": 0,
        "zero": 0,
        "nonzero": 0,
        "min": np.nan,
        "max": np.nan,
        "unique_sampled": set(),
    }

# ---------------------------------------------------------------------
# Process CSV in chunks
# ---------------------------------------------------------------------
chunk_no = 0

for chunk in pd.read_csv(INPUT, chunksize=CHUNK_SIZE, low_memory=False):

    chunk_no += 1

    if chunk_no % 10 == 0:
        print(
            f"Processed chunk {chunk_no} | "
            f"rows processed: {sum(x['total_rows'] for x in stats.values() if x['column'] == columns[0]):,}"
        )

    for col in columns:

        s = chunk[col]

        st = stats[col]

        if st["dtype"] is None:
            st["dtype"] = str(s.dtype)

        st["total_rows"] += len(s)

        # Missing
        missing = s.isna()
        st["missing"] += int(missing.sum())

        # Numeric statistics
        if pd.api.types.is_numeric_dtype(s):

            arr = s.to_numpy(dtype=np.float64, copy=False)

            pos_inf = np.isposinf(arr)
            neg_inf = np.isneginf(arr)

            st["positive_inf"] += int(pos_inf.sum())
            st["negative_inf"] += int(neg_inf.sum())

            finite = np.isfinite(arr)

            zero = finite & (arr == 0)
            nonzero = finite & (arr != 0)

            st["zero"] += int(zero.sum())
            st["nonzero"] += int(nonzero.sum())

            if finite.any():

                finite_values = arr[finite]

                local_min = float(np.min(finite_values))
                local_max = float(np.max(finite_values))

                if pd.isna(st["min"]) or local_min < st["min"]:
                    st["min"] = local_min

                if pd.isna(st["max"]) or local_max > st["max"]:
                    st["max"] = local_max

            # Keep exact unique values only when cardinality is small.
            # This is mainly useful for identifying constant/low-cardinality
            # features without storing millions of values.
            if len(st["unique_sampled"]) <= 1000:
                vals = s.dropna().unique()

                for v in vals:
                    if len(st["unique_sampled"]) >= 1001:
                        break

                    try:
                        if np.isfinite(v):
                            st["unique_sampled"].add(v)
                    except TypeError:
                        st["unique_sampled"].add(v)

        else:

            # Categorical/string columns
            vals = s.dropna().astype(str).unique()

            if len(st["unique_sampled"]) <= 1000:
                for v in vals:
                    if len(st["unique_sampled"]) >= 1001:
                        break
                    st["unique_sampled"].add(v)

# ---------------------------------------------------------------------
# Build final audit table
# ---------------------------------------------------------------------
rows = []

for col in columns:

    st = stats[col]

    total = st["total_rows"]

    missing_pct = (
        100.0 * st["missing"] / total
        if total else np.nan
    )

    zero_pct = (
        100.0 * st["zero"] / total
        if total else np.nan
    )

    nonzero_pct = (
        100.0 * st["nonzero"] / total
        if total else np.nan
    )

    inf_total = st["positive_inf"] + st["negative_inf"]

    rows.append({
        "column": col,
        "dtype": st["dtype"],
        "total_rows": total,
        "missing": st["missing"],
        "missing_pct": missing_pct,
        "positive_inf": st["positive_inf"],
        "negative_inf": st["negative_inf"],
        "inf_total": inf_total,
        "zero": st["zero"],
        "zero_pct": zero_pct,
        "nonzero": st["nonzero"],
        "nonzero_pct": nonzero_pct,
        "min": st["min"],
        "max": st["max"],
        "unique_values_observed": len(st["unique_sampled"]),
    })

audit = pd.DataFrame(rows)

audit["constant_in_full_dataset"] = (
    (audit["missing"] == 0) &
    (audit["inf_total"] == 0) &
    (audit["nonzero"] == 0)
)

audit["all_missing"] = audit["missing"] == audit["total_rows"]

audit = audit.sort_values(
    by=["constant_in_full_dataset", "zero_pct"],
    ascending=[False, False]
)

audit.to_csv(OUTPUT, index=False)

print()
print("=" * 90)
print("AUDIT COMPLETE")
print("=" * 90)

print(f"Rows processed: {audit['total_rows'].iloc[0]:,}")
print(f"Columns: {len(audit)}")
print(f"Saved: {OUTPUT}")

print()
print("Constant features:")
print(
    audit.loc[
        audit["constant_in_full_dataset"],
        ["column", "zero", "zero_pct", "min", "max"]
    ].to_string(index=False)
)

print()
print("Highest zero-percentage features:")
print(
    audit[
        ["column", "zero", "zero_pct", "nonzero", "nonzero_pct"]
    ]
    .sort_values("zero_pct", ascending=False)
    .head(25)
    .to_string(index=False)
)

print()
print("Missing-value features:")
missing_features = audit[audit["missing"] > 0]

if len(missing_features):
    print(
        missing_features[
            ["column", "missing", "missing_pct"]
        ].to_string(index=False)
    )
else:
    print("None")

print()
print("Infinity-containing features:")
inf_features = audit[audit["inf_total"] > 0]

if len(inf_features):
    print(
        inf_features[
            ["column", "positive_inf", "negative_inf", "inf_total"]
        ].to_string(index=False)
    )
else:
    print("None")