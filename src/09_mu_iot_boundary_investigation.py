from pathlib import Path
import pandas as pd
import re

# ============================================================
# MU-IoT Step A: Chunk Boundary Investigation
# ============================================================

ROOT = Path(r"D:\Major_Project\dataset\mu_iot\CSV")
OUTPUT_DIR = Path(r"D:\Major_Project\output\mu_iot")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = OUTPUT_DIR / "mu_iot_boundary_report.csv"

USECOLS = ["FPT", "label", "category"]
CHUNK_SIZE = 200_000


def inspect_file(filepath):
    """Read only the required columns and obtain boundary information."""

    first_fpt = None
    last_fpt = None

    categories = set()
    labels = set()

    total_rows = 0

    for chunk in pd.read_csv(
        filepath,
        usecols=USECOLS,
        chunksize=CHUNK_SIZE,
        low_memory=False
    ):
        total_rows += len(chunk)

        # FPT
        fpt = pd.to_numeric(chunk["FPT"], errors="coerce").dropna()

        if not fpt.empty:
            if first_fpt is None:
                first_fpt = float(fpt.iloc[0])

            last_fpt = float(fpt.iloc[-1])

        # Labels
        categories.update(
            chunk["category"].dropna().astype(str).str.strip().unique()
        )

        labels.update(
            chunk["label"].dropna().astype(str).str.strip().unique()
        )

    return {
        "filename": filepath.name,
        "path": str(filepath),
        "rows": total_rows,
        "first_fpt": first_fpt,
        "last_fpt": last_fpt,
        "categories": "|".join(sorted(categories)),
        "labels": "|".join(sorted(labels)),
    }


def get_numbered_groups(files):
    """
    Group files based on the same prefix followed by a numeric suffix.

    Examples:
        bonesi_udp_0.csv
        bonesi_udp_1.csv
        bonesi_udp_2.csv

    become one group.
    """

    groups = {}

    for filepath in files:
        stem = filepath.stem

        match = re.match(r"^(.*)_(\d+)$", stem)

        if match:
            prefix = match.group(1)
            number = int(match.group(2))

            groups.setdefault(prefix, []).append(
                (number, filepath)
            )

    return groups


def main():

    print("=" * 70)
    print("MU-IoT STEP A - CHUNK BOUNDARY INVESTIGATION")
    print("=" * 70)

    csv_files = sorted(ROOT.rglob("*.csv"))

    print(f"\nCSV files found: {len(csv_files)}")

    print("\nInspecting files...")
    print("Only FPT, label and category are being read.")
    print("Large files are processed in chunks.\n")

    file_info = {}

    for i, filepath in enumerate(csv_files, start=1):

        print(
            f"[{i:02d}/{len(csv_files):02d}] "
            f"{filepath.name}"
        )

        file_info[filepath] = inspect_file(filepath)

    # --------------------------------------------------------
    # Identify numbered groups
    # --------------------------------------------------------

    groups = get_numbered_groups(csv_files)

    print("\n" + "=" * 70)
    print("NUMBERED FILE GROUPS")
    print("=" * 70)

    for prefix, items in sorted(groups.items()):

        items.sort(key=lambda x: x[0])

        print(f"\n{prefix}")

        for number, filepath in items:
            print(f"   {number}: {filepath.name}")

    # --------------------------------------------------------
    # Compare consecutive files
    # --------------------------------------------------------

    results = []

    for prefix, items in sorted(groups.items()):

        items.sort(key=lambda x: x[0])

        for index, (number, filepath) in enumerate(items):

            current = file_info[filepath]

            # Last file in group has no next file
            if index == len(items) - 1:

                results.append({
                    "group": prefix,
                    "file_number": number,
                    "filename": current["filename"],
                    "next_filename": "",
                    "rows": current["rows"],
                    "first_fpt": current["first_fpt"],
                    "last_fpt": current["last_fpt"],
                    "next_first_fpt": None,
                    "fpt_gap_seconds": None,
                    "current_categories": current["categories"],
                    "next_categories": "",
                    "category_match": None,
                    "current_labels": current["labels"],
                    "next_labels": "",
                    "label_match": None,
                    "classification": "LAST_IN_GROUP",
                })

                continue

            next_number, next_filepath = items[index + 1]

            next_info = file_info[next_filepath]

            last_fpt = current["last_fpt"]
            next_first_fpt = next_info["first_fpt"]

            if last_fpt is not None and next_first_fpt is not None:
                gap = next_first_fpt - last_fpt
            else:
                gap = None

            current_categories = set(
                current["categories"].split("|")
            ) if current["categories"] else set()

            next_categories = set(
                next_info["categories"].split("|")
            ) if next_info["categories"] else set()

            current_labels = set(
                current["labels"].split("|")
            ) if current["labels"] else set()

            next_labels = set(
                next_info["labels"].split("|")
            ) if next_info["labels"] else set()

            category_match = current_categories == next_categories
            label_match = current_labels == next_labels

            results.append({
                "group": prefix,
                "file_number": number,
                "filename": current["filename"],
                "next_filename": next_info["filename"],
                "rows": current["rows"],
                "first_fpt": current["first_fpt"],
                "last_fpt": current["last_fpt"],
                "next_first_fpt": next_first_fpt,
                "fpt_gap_seconds": gap,
                "current_categories": current["categories"],
                "next_categories": next_info["categories"],
                "category_match": category_match,
                "current_labels": current["labels"],
                "next_labels": next_info["labels"],
                "label_match": label_match,

                # IMPORTANT:
                # Classification is deliberately NOT assigned yet.
                # We need to inspect the empirical gap distribution first.
                "classification": "REVIEW_GAP",
            })

    report = pd.DataFrame(results)

    report.to_csv(REPORT_FILE, index=False)

    print("\n" + "=" * 70)
    print("BOUNDARY REPORT CREATED")
    print("=" * 70)

    print(f"\nSaved to:")
    print(REPORT_FILE)

    print("\nBoundary gaps:")
    print(
        report[
            [
                "group",
                "filename",
                "next_filename",
                "fpt_gap_seconds",
                "category_match",
                "label_match",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()