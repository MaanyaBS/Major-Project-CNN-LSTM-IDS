import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder

INPUT_FILE = r"D:\Major_Project\dataset\merged\cicids2017_cleaned.csv"

OUTPUT_FOLDER = r"D:\Major_Project\dataset\encoded"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

OUTPUT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "cicids2017_encoded.csv"
)

MAPPING_FILE = r"D:\Major_Project\output\label_mapping.csv"

print("="*80)
print("LABEL ENCODING")
print("="*80)

encoder = LabelEncoder()

labels = set()

print("\nScanning labels...")

for chunk in pd.read_csv(
        INPUT_FILE,
        chunksize=100000,
        usecols=["Label"],
        low_memory=False):

    chunk.columns = chunk.columns.str.strip()

    chunk["Label"] = (
        chunk["Label"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    chunk = chunk[chunk["Label"] != ""]

    labels.update(chunk["Label"].tolist())

labels = sorted(list(labels))

print("\nUnique Labels Found:")
print(labels)

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

    chunk.columns = chunk.columns.str.strip()

    chunk = chunk.dropna(subset=["Label"])

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

print("\nDone!")

print(f"\nEncoded Dataset : {OUTPUT_FILE}")
print(f"Label Mapping   : {MAPPING_FILE}")