import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder

MERGED_PATH = r"D:\Major_Project\dataset\merged"
OUTPUT_PATH = r"D:\Major_Project\output"

input_file = os.path.join(MERGED_PATH, "cicids2017_cleaned.csv")
output_file = os.path.join(MERGED_PATH, "cicids2017_encoded.csv")
mapping_file = os.path.join(OUTPUT_PATH, "label_mapping.csv")

encoder = LabelEncoder()

# -------- Pass 1: Collect all labels --------
all_labels = set()

for chunk in pd.read_csv(input_file, chunksize=50000):
    label_col = [c for c in chunk.columns if c.strip().lower() == "label"][0]
    all_labels.update(chunk[label_col].unique())

encoder.fit(sorted(all_labels))

mapping = pd.DataFrame({
    "Original Label": encoder.classes_,
    "Encoded Value": range(len(encoder.classes_))
})

mapping.to_csv(mapping_file, index=False)

# -------- Pass 2: Encode and write --------
first = True

for chunk in pd.read_csv(input_file, chunksize=50000):

    label_col = [c for c in chunk.columns if c.strip().lower() == "label"][0]

    chunk[label_col] = encoder.transform(chunk[label_col])

    chunk.to_csv(
        output_file,
        mode="w" if first else "a",
        header=first,
        index=False
    )

    first = False

print("Label encoding completed successfully!")
print("Encoded dataset:", output_file)
print("Mapping:", mapping_file)