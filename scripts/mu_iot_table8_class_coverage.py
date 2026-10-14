import pandas as pd
import numpy as np

p = r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv"
out = r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_table8_class_coverage.csv"

paper = [
    "FPC","RTSP_ML","FPT","RTSP_MUL","ECE_FC","DNS_RCM","DNS_RCUL","FD",
    "RTSP_SETUPC","DNS_QTUL","RTSP_MM","DNS_QTM","DNS_RCL","DNSQTL","URG_FC",
    "HTTP_SCUL","MQTT_MTUL","HTTP_SCL","MQTT_MTM","HTTPOptC","HTTP_SCM",
    "ECN_M","ECN_UV","MQTT_MTL","HTTPPutC","DSCP_S","ECN_S","TPackets","LPT",
    "HTTPPostC","TCPWS_Mode","PLM","DSCP_M","TCPWS_Mean","BJitter",
    "BThroughput","HL_Mode","TCPWS_Sum","MGA_UL","FAMax","FH_M","DSCP_UV",
    "SDuration","FlowR","MGA_L","PacketsPS","FIMin","ECN_C","FAMean","RCount"
]

header = pd.read_csv(p, nrows=0)
features = [x for x in paper if x in header.columns]

classes = [
    "DDoS",
    "Scan",
    "Password_Hacking",
    "normal",
    "Injection",
    "Spyware",
    "MiTM"
]

nonzero_counts = {
    c: {f: 0 for f in features}
    for c in classes
}

totals = {c: 0 for c in classes}

reader = pd.read_csv(
    p,
    usecols=["category"] + features,
    chunksize=200000
)

processed = 0

for chunk in reader:
    processed += len(chunk)

    for c in classes:
        mask = chunk["category"].eq(c)

        if not mask.any():
            continue

        part = chunk.loc[mask, features]
        totals[c] += len(part)

        nonzero_counts[c] = {
            f: nonzero_counts[c][f] + int((part[f].fillna(0) != 0).sum())
            for f in features
        }

    if processed % 2000000 == 0:
        print(f"Processed: {processed:,} rows")

rows = []

rank_map = {f: i + 1 for i, f in enumerate(paper)}

for feature in features:
    row = {
        "paper_rank": rank_map[feature],
        "feature": feature
    }

    for c in classes:
        row[c + "_nonzero_pct"] = (
            nonzero_counts[c][feature] / totals[c] * 100
            if totals[c] else np.nan
        )

    rows.append(row)

result = pd.DataFrame(rows).sort_values("paper_rank")

result.to_csv(out, index=False)

print("\n" + "=" * 120)
print("TABLE 8 CLASS-WISE NONZERO COVERAGE")
print("=" * 120)
print(result.to_string(index=False))

print("\nClass totals:")
for c in classes:
    print(f"{c:20s}: {totals[c]:,}")

print("\nSaved to:")
print(out)
