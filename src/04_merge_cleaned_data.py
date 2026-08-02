"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 04 - Merge Cleaned Datasets (with source_day)
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd

# --------------------------------------------------------
# Paths
# --------------------------------------------------------

CLEANED_PATH = r"D:\Major_Project\dataset\cleaned"
MERGED_PATH = r"D:\Major_Project\dataset\merged"

os.makedirs(MERGED_PATH, exist_ok=True)

OUTPUT_FILE = os.path.join(
    MERGED_PATH,
    "cicids2017_cleaned_with_day.csv"
)

# --------------------------------------------------------
# Day Mapping
# --------------------------------------------------------

DAY_MAPPING = {
    "Monday-WorkingHours.pcap_ISCX.csv": "Monday",
    "Tuesday-WorkingHours.pcap_ISCX.csv": "Tuesday",
    "Wednesday-workingHours.pcap_ISCX.csv": "Wednesday",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": "Thursday_WebAttacks",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": "Thursday_Infiltration",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv": "Friday_Morning",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": "Friday_PortScan",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": "Friday_DDoS"
}

# --------------------------------------------------------
# Read Files
# --------------------------------------------------------

csv_files = sorted(
    [
        f for f in os.listdir(CLEANED_PATH)
        if f.lower().endswith(".csv")
    ]
)

print("=" * 80)
print("MERGING CLEANED DATASETS WITH SOURCE DAY")
print("=" * 80)

first_file = True
total_rows = 0

for file in csv_files:

    print(f"\nProcessing : {file}")

    file_path = os.path.join(CLEANED_PATH, file)

    df = pd.read_csv(file_path)

    # ----------------------------------------------------
    # Add source_day column
    # ----------------------------------------------------

    df["source_day"] = DAY_MAPPING.get(file, "Unknown")

    total_rows += len(df)

    print(f"Rows : {len(df)}")
    print(f"Source Day : {DAY_MAPPING.get(file, 'Unknown')}")

    # ----------------------------------------------------
    # Append to merged file
    # ----------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        mode="w" if first_file else "a",
        header=first_file,
        index=False
    )

    first_file = False

print("\n" + "=" * 80)
print("MERGING COMPLETED")
print("=" * 80)

print(f"\nTotal Rows Merged : {total_rows}")
print(f"Merged Dataset    : {OUTPUT_FILE}")