import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# MU-IoT BOUNDARY vs INTERNAL FPT GAP ANALYSIS
# ============================================================

BOUNDARY_FILE = Path(
    r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_boundary_investigation.csv"
)

INTERNAL_FILE = Path(
    r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_internal_fpt_gap_analysis.csv"
)

OUTPUT_FILE = Path(
    r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_boundary_vs_internal.csv"
)


# ============================================================
# START
# ============================================================

print("=" * 100)
print("MU-IoT BOUNDARY vs INTERNAL FPT GAP ANALYSIS")
print("=" * 100)


# ============================================================
# CHECK FILES
# ============================================================

if not BOUNDARY_FILE.exists():
    raise FileNotFoundError(
        f"\nBoundary file not found:\n{BOUNDARY_FILE}"
    )

if not INTERNAL_FILE.exists():
    raise FileNotFoundError(
        f"\nInternal analysis file not found:\n{INTERNAL_FILE}"
    )


# ============================================================
# LOAD FILES
# ============================================================

print("\nReading boundary analysis...")
boundary = pd.read_csv(BOUNDARY_FILE)

print("Reading internal analysis...")
internal = pd.read_csv(INTERNAL_FILE)


# ============================================================
# DISPLAY COLUMNS
# ============================================================

print("\nBoundary columns:")
print(boundary.columns.tolist())

print("\nInternal columns:")
print(internal.columns.tolist())


# ============================================================
# BASIC INFORMATION
# ============================================================

print("\nBoundary rows:", len(boundary))
print("Internal rows:", len(internal))


# ============================================================
# PREVIEW
# ============================================================

print("\nBoundary preview:")
print(boundary.head().to_string(index=False))

print("\nInternal preview:")
print(internal.head().to_string(index=False))


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

boundary.columns = boundary.columns.str.strip()
internal.columns = internal.columns.str.strip()


# ============================================================
# VERIFY REQUIRED BOUNDARY COLUMNS
# ============================================================

required_boundary_columns = [
    "current_file",
    "next_file",
    "fpt_gap",
]

for column in required_boundary_columns:

    if column not in boundary.columns:
        raise ValueError(
            f"\nRequired boundary column not found: {column}\n"
            f"Available columns:\n{boundary.columns.tolist()}"
        )


# ============================================================
# VERIFY REQUIRED INTERNAL COLUMNS
# ============================================================

required_internal_columns = [
    "file",
    "median_gap",
    "p90_gap",
    "p95_gap",
    "p99_gap",
    "p999_gap",
    "max_gap",
]

for column in required_internal_columns:

    if column not in internal.columns:
        raise ValueError(
            f"\nRequired internal column not found: {column}\n"
            f"Available columns:\n{internal.columns.tolist()}"
        )


# ============================================================
# IDENTIFIED COLUMNS
# ============================================================

boundary_current = "current_file"
boundary_next = "next_file"
boundary_gap = "fpt_gap"
internal_file = "file"


print("\nIdentified columns:")
print("Boundary current file :", boundary_current)
print("Boundary next file    :", boundary_next)
print("Boundary FPT gap      :", boundary_gap)
print("Internal file         :", internal_file)


# ============================================================
# CREATE FILE-NAME KEYS
# ============================================================

# Boundary contains full Windows paths such as:
#
# D:\Major_Project\dataset\mu_iot\CSV\ATTACK\DDoS\UDP\botnet_udp_3.csv
#
# Internal analysis contains only:
#
# botnet_udp_3.csv
#
# Therefore compare using only the filename.

boundary["__file_name"] = (
    boundary[boundary_current]
    .astype(str)
    .apply(lambda x: Path(x).name)
)

internal["__file_name"] = (
    internal[internal_file]
    .astype(str)
    .apply(lambda x: Path(x).name)
)


# ============================================================
# SHOW FILE-NAME MATCHING
# ============================================================

print("\nBoundary filename keys:")
print(
    boundary[
        [boundary_current, "__file_name"]
    ].to_string(index=False)
)

print("\nInternal filename keys:")
print(
    internal[
        [internal_file, "__file_name"]
    ].to_string(index=False)
)


# ============================================================
# SELECT INTERNAL STATISTICS
# ============================================================

internal_stats = internal[
    [
        "__file_name",
        "median_gap",
        "p90_gap",
        "p95_gap",
        "p99_gap",
        "p999_gap",
        "max_gap",
    ]
].copy()


# ============================================================
# RENAME INTERNAL STATISTICS
# ============================================================

internal_stats = internal_stats.rename(
    columns={
        "median_gap": "internal_median",
        "p90_gap": "internal_p90",
        "p95_gap": "internal_p95",
        "p99_gap": "internal_p99",
        "p999_gap": "internal_p999",
        "max_gap": "internal_max",
    }
)


# ============================================================
# MERGE
# ============================================================

print("\nMerging boundary information with internal statistics...")

result = boundary.merge(
    internal_stats,
    on="__file_name",
    how="left"
)


# ============================================================
# CHECK MATCHING
# ============================================================

unmatched = result["internal_p95"].isna().sum()

print("\nBoundary files without matching internal analysis:", unmatched)

if unmatched > 0:

    print("\nWARNING: The following boundary files could not be matched:")

    print(
        result.loc[
            result["internal_p95"].isna(),
            [boundary_current, "__file_name"]
        ].to_string(index=False)
    )


# ============================================================
# CONVERT TO NUMERIC
# ============================================================

result["boundary_fpt_gap"] = pd.to_numeric(
    result[boundary_gap],
    errors="coerce"
)

numeric_columns = [
    "internal_median",
    "internal_p90",
    "internal_p95",
    "internal_p99",
    "internal_p999",
    "internal_max",
]

for column in numeric_columns:

    result[column] = pd.to_numeric(
        result[column],
        errors="coerce"
    )


# ============================================================
# CALCULATE RATIOS
# ============================================================

result["gap_vs_median_ratio"] = (
    result["boundary_fpt_gap"]
    / result["internal_median"].replace(0, np.nan)
)

result["gap_vs_p95_ratio"] = (
    result["boundary_fpt_gap"]
    / result["internal_p95"].replace(0, np.nan)
)

result["gap_vs_p99_ratio"] = (
    result["boundary_fpt_gap"]
    / result["internal_p99"].replace(0, np.nan)
)

result["gap_vs_max_ratio"] = (
    result["boundary_fpt_gap"]
    / result["internal_max"].replace(0, np.nan)
)


# ============================================================
# COMPARE BOUNDARY WITH INTERNAL DISTRIBUTION
# ============================================================

result["boundary_exceeds_p95"] = (
    result["boundary_fpt_gap"]
    > result["internal_p95"]
)

result["boundary_exceeds_p99"] = (
    result["boundary_fpt_gap"]
    > result["internal_p99"]
)

result["boundary_exceeds_p999"] = (
    result["boundary_fpt_gap"]
    > result["internal_p999"]
)

result["boundary_exceeds_internal_max"] = (
    result["boundary_fpt_gap"]
    > result["internal_max"]
)


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_boundary(row):

    gap = row["boundary_fpt_gap"]
    p95 = row["internal_p95"]
    p99 = row["internal_p99"]
    p999 = row["internal_p999"]
    maximum = row["internal_max"]

    if (
        pd.isna(gap)
        or pd.isna(p95)
        or pd.isna(p99)
        or pd.isna(p999)
        or pd.isna(maximum)
    ):
        return "UNKNOWN"

    if gap > maximum:
        return "ABOVE_INTERNAL_MAX"

    elif gap > p999:
        return "ABOVE_INTERNAL_P999"

    elif gap > p99:
        return "ABOVE_INTERNAL_P99"

    elif gap > p95:
        return "ABOVE_INTERNAL_P95"

    else:
        return "WITHIN_INTERNAL_P95"


result["boundary_classification"] = result.apply(
    classify_boundary,
    axis=1
)


# ============================================================
# ADD INTERPRETATION
# ============================================================

def interpretation(row):

    classification = row["boundary_classification"]

    if classification == "ABOVE_INTERNAL_MAX":
        return (
            "Boundary gap is larger than every observed "
            "internal gap in the preceding file."
        )

    elif classification == "ABOVE_INTERNAL_P999":
        return (
            "Boundary gap is extremely unusual relative "
            "to internal traffic timing."
        )

    elif classification == "ABOVE_INTERNAL_P99":
        return (
            "Boundary gap exceeds the internal 99th percentile "
            "but is below the internal maximum."
        )

    elif classification == "ABOVE_INTERNAL_P95":
        return (
            "Boundary gap exceeds the internal 95th percentile "
            "but remains within the broader internal distribution."
        )

    elif classification == "WITHIN_INTERNAL_P95":
        return (
            "Boundary gap is within the normal range represented "
            "by the preceding file's internal timing."
        )

    else:
        return "Could not determine because internal statistics are unavailable."


result["interpretation"] = result.apply(
    interpretation,
    axis=1
)


# ============================================================
# REMOVE HELPER COLUMN
# ============================================================

result = result.drop(
    columns=["__file_name"]
)


# ============================================================
# SAVE RESULT
# ============================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 100)
print("SUMMARY")
print("=" * 100)

print("\nTotal boundaries analysed:", len(result))

print(
    "\nClassification counts:"
)

print(
    result[
        "boundary_classification"
    ]
    .value_counts(dropna=False)
    .to_string()
)


# ============================================================
# THRESHOLD COUNTS
# ============================================================

print(
    "\nBoundaries exceeding internal P95:",
    int(result["boundary_exceeds_p95"].sum())
)

print(
    "Boundaries exceeding internal P99:",
    int(result["boundary_exceeds_p99"].sum())
)

print(
    "Boundaries exceeding internal P99.9:",
    int(result["boundary_exceeds_p999"].sum())
)

print(
    "Boundaries exceeding internal maximum:",
    int(result["boundary_exceeds_internal_max"].sum())
)


# ============================================================
# DETAILED RESULTS
# ============================================================

print("\n")
print("=" * 100)
print("BOUNDARY COMPARISON RESULTS")
print("=" * 100)

display_columns = [
    "group",
    "current_file",
    "next_file",
    "boundary_fpt_gap",
    "internal_median",
    "internal_p95",
    "internal_p99",
    "internal_p999",
    "internal_max",
    "gap_vs_p95_ratio",
    "gap_vs_p99_ratio",
    "boundary_classification",
]

print(
    result[
        display_columns
    ].to_string(index=False)
)


# ============================================================
# LARGEST BOUNDARY GAPS
# ============================================================

print("\n")
print("=" * 100)
print("LARGEST BOUNDARY GAPS")
print("=" * 100)

largest = (
    result[
        display_columns
    ]
    .sort_values(
        "boundary_fpt_gap",
        ascending=False
    )
    .head(20)
)

print(
    largest.to_string(index=False)
)


# ============================================================
# UNUSUAL BOUNDARIES
# ============================================================

unusual = result[
    result["boundary_exceeds_p95"]
].copy()

print("\n")
print("=" * 100)
print("BOUNDARIES ABOVE INTERNAL P95")
print("=" * 100)

if len(unusual) == 0:

    print(
        "No boundary gap exceeds the internal 95th percentile."
    )

else:

    print(
        unusual[
            display_columns
        ].sort_values(
            "boundary_fpt_gap",
            ascending=False
        ).to_string(index=False)
    )


# ============================================================
# ABOVE INTERNAL P99
# ============================================================

very_unusual = result[
    result["boundary_exceeds_p99"]
].copy()

print("\n")
print("=" * 100)
print("BOUNDARIES ABOVE INTERNAL P99")
print("=" * 100)

if len(very_unusual) == 0:

    print(
        "No boundary gap exceeds the internal 99th percentile."
    )

else:

    print(
        very_unusual[
            display_columns
        ].sort_values(
            "boundary_fpt_gap",
            ascending=False
        ).to_string(index=False)
    )


# ============================================================
# FINAL
# ============================================================

print("\n")
print("=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\nIMPORTANT:")
print(
    "Do NOT modify mu_iot_cleaned.csv based on this analysis yet."
)

print(
    "Use the results above to validate the capture-session boundaries first."
)

print("=" * 100)