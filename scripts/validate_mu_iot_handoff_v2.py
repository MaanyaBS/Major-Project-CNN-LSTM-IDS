import pandas as pd
from pathlib import Path
import numpy as np

root = Path(r"D:\Major_Project\dataset\processed\mu_iot\handoff_v2")
parts = sorted((root / "full").glob("*.parquet"))

total = 0
sessions = set()
categories = {}
types = {}
bad_inf = 0
bad_null_labels = 0
duplicates = 0

print("=" * 70)
print("FINAL MU-IoT HANDOFF VALIDATION")
print("=" * 70)

print(f"Parquet parts: {len(parts)}")
print()

for p in parts:
    df = pd.read_parquet(p)

    total += len(df)

    sessions.update(df["capture_session"].astype(str).unique())

    for k, v in df["category"].value_counts().items():
        categories[str(k)] = categories.get(str(k), 0) + int(v)

    for k, v in df["type"].value_counts().items():
        types[str(k)] = types.get(str(k), 0) + int(v)

    feature_cols = [
        "FPC","RTSP_ML","RTSP_MUL","ECE_FC","DNS_RCM",
        "DNS_RCUL","FD","RTSP_SETUPC","DNS_QTUL","RTSP_MM",
        "DNS_QTM","DNS_RCL","DNSQTL","URG_FC","MQTT_MTUL",
        "HTTP_SCL","HTTPOptC","HTTP_SCM","ECN_M","ECN_UV",
        "MQTT_MTL","HTTPPutC","DSCP_S","ECN_S","TPackets",
        "HTTPPostC","TCPWS_Mode","PLM","DSCP_M","TCPWS_Mean",
        "BJitter","BThroughput","HL_Mode","TCPWS_Sum","MGA_UL",
        "FAMax","FH_M","DSCP_UV","SDuration","FlowR","MGA_L",
        "PacketsPS","FIMin","ECN_C","FAMean","RCount"
    ]

    bad_inf += int(
        np.isinf(df[feature_cols].to_numpy(dtype=float)).sum()
    )

    bad_null_labels += int(
        df[["label","category","type"]].isna().any(axis=1).sum()
    )

    duplicates += int(df.duplicated().sum())

    print(
        f"{p.name}: {len(df):,} rows"
    )

print()
print("=" * 70)
print("RESULT")
print("=" * 70)

print(f"TOTAL ROWS       : {total:,}")
print(f"SESSIONS         : {len(sessions)}")
print(f"INFINITE VALUES  : {bad_inf:,}")
print(f"NULL LABEL ROWS  : {bad_null_labels:,}")
print(f"DUPLICATE ROWS   : {duplicates:,}")

print()
print("CATEGORY COUNTS")
for k, v in sorted(categories.items()):
    print(f"{k:25s} {v:>12,}")

print()
print("TYPE COUNTS")
for k, v in sorted(types.items()):
    print(f"{k:25s} {v:>12,}")

print()
print("SUPPORT FILES")

for name in [
    "column_groups.json",
    "label_mappings.json",
    "feature_stats.csv",
    "session_summary.csv",
    "class_counts.csv",
    "source_type_audit.csv",
    "source_quota_plan.csv",
    "README.md"
]:
    p = root / name
    print(f"{name:30s} {'OK' if p.exists() else 'MISSING'}")

print()
print("=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
