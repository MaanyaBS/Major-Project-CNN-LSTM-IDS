from pathlib import Path
import pandas as pd

PAIRS = [
    (
        r"D:\Major_Project\dataset\mu_iot\CSV\ATTACK\DDoS\HTTP_FLood\Botnet_HTTP_Flood.csv",
        r"D:\Major_Project\dataset\mu_iot\CSV\ATTACK\DDoS\HTTP_FLood\Botnet_HTTP_Flood1.csv",
    ),
    (
        r"D:\Major_Project\dataset\mu_iot\CSV\ATTACK\Injection\XSS\XSS_Injection.csv",
        r"D:\Major_Project\dataset\mu_iot\CSV\ATTACK\Injection\XSS\XSS_Injection1.csv",
    ),
    (
        r"D:\Major_Project\dataset\mu_iot\CSV\ATTACK\Scan\Recon\Scan_Recon1.csv",
        r"D:\Major_Project\dataset\mu_iot\CSV\ATTACK\Scan\Recon\Scan_Recon2.csv",
    ),
]

CHUNK_SIZE = 200_000


def get_boundary(filepath):
    first_fpt = None
    last_fpt = None
    categories = set()
    labels = set()

    for chunk in pd.read_csv(
        filepath,
        usecols=["FPT", "category", "label"],
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        fpt = pd.to_numeric(chunk["FPT"], errors="coerce").dropna()

        if not fpt.empty:
            if first_fpt is None:
                first_fpt = float(fpt.iloc[0])

            last_fpt = float(fpt.iloc[-1])

        categories.update(
            chunk["category"].dropna().astype(str).str.strip().unique()
        )

        labels.update(
            chunk["label"].dropna().astype(str).str.strip().unique()
        )

    return first_fpt, last_fpt, categories, labels


for first_file, second_file in PAIRS:

    _, first_last, first_categories, first_labels = get_boundary(first_file)
    second_first, _, second_categories, second_labels = get_boundary(second_file)

    gap = second_first - first_last

    print("=" * 70)
    print(Path(first_file).name)
    print("        ->")
    print(Path(second_file).name)

    print(f"Last FPT of first file : {first_last}")
    print(f"First FPT of next file : {second_first}")
    print(f"Gap (seconds)          : {gap}")

    print(f"Categories first       : {sorted(first_categories)}")
    print(f"Categories next        : {sorted(second_categories)}")
    print(f"Category match         : {first_categories == second_categories}")

    print(f"Labels first           : {sorted(first_labels)}")
    print(f"Labels next            : {sorted(second_labels)}")
    print(f"Label match            : {first_labels == second_labels}")