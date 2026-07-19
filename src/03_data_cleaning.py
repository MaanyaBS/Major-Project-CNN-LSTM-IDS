"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 05 - Label Encoding
Author  : Maanya & Team
==========================================================
"""

import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder

INPUT_FILE = r"D:\Major_Project\dataset\merged\cicids2017_cleaned.csv"

OUTPUT_FOLDER = r"D:\Major_Project\dataset\encoded"
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "cicids2017_encoded.csv")

MAPPING_FILE = r"D:\Major_Project\output\label_mapping.csv"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("=" * 80)
print("LABEL ENCODING")
print("=" * 80)

# --------------------------------------------------------
# Step 1 : Find all unique labels
# --------------------------------------------------------

print("\nScanning Labels...")

labels = set()

for chunk in pd.read_csv(
        INPUT_FILE,
        chunksize=100000,
        usecols=["Label"],
        low_memory=False):

    chunk["Label"] = (
        chunk["Label"]
        .astype(str)
        .str.strip()
    )

    labels.update(chunk["Label"].unique())

labels = sorted(labels)

print("\nLabels Found:")

for label in labels:
    print(label)

# --------------------------------------------------------
# Step 2 : Encode Labels
# --------------------------------------------------------

encoder = LabelEncoder()

encoder.fit(labels)

mapping = pd.DataFrame({
    "Attack": encoder.classes_,
    "Encoded": encoder.transform(encoder.classes_)
})

mapping.to_csv(MAPPING_FILE, index=False)

print("\nEncoding Dataset...")

first = True

for chunk in pd.read_csv(
        INPUT_FILE,
        chunksize=100000,
        low_memory=False):

    chunk["Label"] = (
        chunk["Label"]
        .astype(str)
        .str.strip()
    )

    chunk["Label"] = encoder.transform(chunk["Label"])

    chunk.to_csv(
        OUTPUT_FILE,
        mode="w" if first else "a",
        header=first,
        index=False
    )

    first = False

print("\n" + "=" * 80)
print("LABEL ENCODING COMPLETED")
print("=" * 80)

print(f"\nEncoded Dataset : {OUTPUT_FILE}")
print(f"Label Mapping   : {MAPPING_FILE}")