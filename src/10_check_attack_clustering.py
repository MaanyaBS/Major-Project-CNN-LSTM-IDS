import pandas as pd

INPUT_FILE = r"D:\Major_Project\dataset\merged\cicids2017_cleaned_with_day.csv"

print("=" * 80)
print("ATTACK CLUSTERING CHECK")
print("=" * 80)

df = pd.read_csv(INPUT_FILE)

for group in df["source_day"].unique():

    sub = df[df["source_day"] == group].reset_index(drop=True)

    attack_idx = sub[sub["Label"] != "BENIGN"].index

    print("\n" + "=" * 60)
    print("Source:", group)

    if len(attack_idx) == 0:
        print("No attack records.")
        continue

    print("Total Rows       :", len(sub))
    print("Attack Rows      :", len(attack_idx))
    print("First Attack Row :", attack_idx.min())
    print("Last Attack Row  :", attack_idx.max())

    gaps = attack_idx.to_series().diff().fillna(1)
    clusters = (gaps > 1).sum() + 1

    print("Approx Clusters  :", clusters)

    print("First 20 Attack Indices:")
    print(attack_idx[:20].tolist())

print("\nDone.")