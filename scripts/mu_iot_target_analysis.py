import pandas as pd
import numpy as np

PATH = r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv"
OUT = r"D:\Major_Project\dataset\processed\mu_iot"

FEATURES = [
    "SIP_multicast",
    "DIP_loopback",
    "SIP_loopback",
    "DIP_link_local",
    "SIP_link_local",
    "RTSP_ML",
    "RTSP_MUL",
    "CWR_FC",
    "ECE_FC",
    "BP_Count",
    "BJitter",
    "BIPD_Var",
    "BIAT",
    "BThroughput",
    "URG_FC",
    "FPC",
    "ECN_M",
    "ECN_S",
    "MQTT_MTL",
    "MQTT_MTUL",
    "MGA_UL",
    "MP_Count",
    "MGA_L",
    "BAPS",
    "DBytes",
    "BackwardPC",
    "DIP_multicast",
    "DSCP_M",
    "DSCP_S"
]

USECOLS = ["category", "capture_session"] + FEATURES

print("=" * 80)
print("MU-IoT TARGET / FEATURE ANALYSIS")
print("=" * 80)

# ---------------------------------------------------------
# Overall category counts
# ---------------------------------------------------------

category_counts = {}

# ---------------------------------------------------------
# Feature non-zero counts
# ---------------------------------------------------------

nonzero_counts = {f: 0 for f in FEATURES}

# ---------------------------------------------------------
# Feature non-zero counts by category
# ---------------------------------------------------------

category_nonzero = {}

# ---------------------------------------------------------
# Capture session -> category counts
# ---------------------------------------------------------

session_category = {}

chunk_size = 500_000
chunk_no = 0

for df in pd.read_csv(
    PATH,
    usecols=USECOLS,
    chunksize=chunk_size,
    low_memory=False
):

    chunk_no += 1
    print(f"Processing chunk {chunk_no}...")

    # Category distribution
    counts = df["category"].value_counts()

    for category, count in counts.items():
        category_counts[category] = (
            category_counts.get(category, 0) + int(count)
        )

    # Non-zero counts
    for feature in FEATURES:
        nonzero_counts[feature] += int(
            (pd.to_numeric(df[feature], errors="coerce").fillna(0) != 0).sum()
        )

    # Non-zero by category
    for category, group in df.groupby("category"):

        if category not in category_nonzero:
            category_nonzero[category] = {
                f: 0 for f in FEATURES
            }

        for feature in FEATURES:
            values = pd.to_numeric(
                group[feature],
                errors="coerce"
            ).fillna(0)

            category_nonzero[category][feature] += int(
                (values != 0).sum()
            )

    # Capture session vs category
    ct = pd.crosstab(
        df["capture_session"],
        df["category"]
    )

    for session, row in ct.iterrows():

        if session not in session_category:
            session_category[session] = {}

        for category, value in row.items():

            session_category[session][category] = (
                session_category[session].get(category, 0)
                + int(value)
            )

# =========================================================
# RESULTS
# =========================================================

print("\n" + "=" * 80)
print("CATEGORY DISTRIBUTION")
print("=" * 80)

category_series = pd.Series(category_counts).sort_values(
    ascending=False
)

print(category_series.to_string())

category_series.to_csv(
    OUT + r"\mu_iot_category_distribution.csv",
    header=["count"]
)

# ---------------------------------------------------------

print("\n" + "=" * 80)
print("SUSPICIOUS FEATURE NON-ZERO COUNTS")
print("=" * 80)

nonzero_series = pd.Series(nonzero_counts).sort_values()

print(nonzero_series.to_string())

nonzero_series.to_csv(
    OUT + r"\mu_iot_suspicious_nonzero_counts.csv",
    header=["nonzero_count"]
)

# ---------------------------------------------------------

print("\n" + "=" * 80)
print("NON-ZERO FEATURES BY CATEGORY")
print("=" * 80)

rows = []

for category, features in category_nonzero.items():

    total = category_counts[category]

    for feature, count in features.items():

        rows.append({
            "category": category,
            "feature": feature,
            "nonzero_count": count,
            "nonzero_percentage": (count / total) * 100
        })

category_feature_df = pd.DataFrame(rows)

category_feature_df.to_csv(
    OUT + r"\mu_iot_feature_by_category.csv",
    index=False
)

print(
    category_feature_df
    .sort_values(
        ["category", "nonzero_percentage"],
        ascending=[True, False]
    )
    .to_string(index=False)
)

# ---------------------------------------------------------

print("\n" + "=" * 80)
print("CAPTURE SESSION vs CATEGORY")
print("=" * 80)

session_rows = []

for session, categories in session_category.items():

    total = sum(categories.values())

    row = {
        "capture_session": session,
        "total_rows": total
    }

    for category, count in categories.items():
        row[category] = count

    session_rows.append(row)

session_df = pd.DataFrame(session_rows).fillna(0)

print(session_df.head(50).to_string(index=False))

session_df.to_csv(
    OUT + r"\mu_iot_capture_session_vs_category.csv",
    index=False
)

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

print("\nFiles saved in:")
print(OUT)