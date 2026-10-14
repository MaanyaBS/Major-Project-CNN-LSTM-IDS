from pathlib import Path
import pandas as pd
import numpy as np

RAW_DIR = Path(r"D:\Major_Project\dataset\mu_iot\CSV")

FILES = [
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "bonesi_udp_0.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "bonesi_udp_1.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "bonesi_udp_2.csv",

    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "botnet_udp_3.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "botnet_udp_4.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "botnet_udp_5.csv",

    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "hping3_udp_6.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "hping3_udp_7.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "hping3_udp_8.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "hping3_udp_9.csv",
    RAW_DIR / "ATTACK" / "DDoS" / "UDP" / "hping3_udp_10.csv",
]

print("=" * 90)
print("MU-IoT INTERNAL FPT GAP ANALYSIS")
print("=" * 90)

results = []

for file in FILES:

    print(f"\nReading: {file.name}")

    df = pd.read_csv(
        file,
        usecols=["FPT"],
        low_memory=False
    )

    fpt = pd.to_numeric(df["FPT"], errors="coerce").dropna()

    gaps = fpt.diff().dropna()

    # Only positive gaps
    gaps = gaps[gaps >= 0]

    if gaps.empty:
        continue

    stats = {
        "file": file.name,
        "rows": len(fpt),
        "min_gap": gaps.min(),
        "median_gap": gaps.median(),
        "mean_gap": gaps.mean(),
        "p90_gap": gaps.quantile(0.90),
        "p95_gap": gaps.quantile(0.95),
        "p99_gap": gaps.quantile(0.99),
        "p999_gap": gaps.quantile(0.999),
        "max_gap": gaps.max(),
        "gaps_over_0.01": (gaps > 0.01).sum(),
        "gaps_over_0.05": (gaps > 0.05).sum(),
        "gaps_over_0.10": (gaps > 0.10).sum(),
        "gaps_over_0.20": (gaps > 0.20).sum(),
        "gaps_over_0.30": (gaps > 0.30).sum(),
        "gaps_over_0.40": (gaps > 0.40).sum(),
        "gaps_over_0.50": (gaps > 0.50).sum(),
    }

    results.append(stats)

    print(f"Rows              : {stats['rows']:,}")
    print(f"Median gap        : {stats['median_gap']:.6f}")
    print(f"90th percentile   : {stats['p90_gap']:.6f}")
    print(f"95th percentile   : {stats['p95_gap']:.6f}")
    print(f"99th percentile   : {stats['p99_gap']:.6f}")
    print(f"99.9th percentile : {stats['p999_gap']:.6f}")
    print(f"Maximum gap       : {stats['max_gap']:.6f}")

    print(
        f">0.10 sec: {stats['gaps_over_0.10']:,} | "
        f">0.20 sec: {stats['gaps_over_0.20']:,} | "
        f">0.30 sec: {stats['gaps_over_0.30']:,} | "
        f">0.40 sec: {stats['gaps_over_0.40']:,} | "
        f">0.50 sec: {stats['gaps_over_0.50']:,}"
    )


output = Path(
    r"D:\Major_Project\dataset\processed\mu_iot\mu_iot_internal_fpt_gap_analysis.csv"
)

pd.DataFrame(results).to_csv(output, index=False)

print("\n" + "=" * 90)
print("ANALYSIS COMPLETE")
print("=" * 90)

print(f"\nSaved to:")
print(output)