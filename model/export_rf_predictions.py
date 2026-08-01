"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : RF Prediction + Confidence Score Export
Author  : Person B (Model Development)
==========================================================
Trains the Random Forest classifier on the full CICIDS2017 dataset
(using the same configuration as baseline_full_dataset.py) and exports
per-row predictions, confidence scores, and true labels to a CSV file
for use by prevention_simulation.py in real (non-demo) mode.

Outputs: model/results/rf_predictions.csv
Columns: predicted_class, confidence, true_class

Skip logic: If model/results/rf_predictions.csv already exists, skips
training entirely and prints the existing file's row count.

Usage (in Colab):
    python model/export_rf_predictions.py
    python model/export_rf_predictions.py --data-path /content/drive/MyDrive/.../cicids2017_cleaned.csv
"""

import os
import sys
import time
import argparse
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Ensure project root on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ----------------------------------------------------------------
# Configuration — kept in sync with baseline_full_dataset.py
# ----------------------------------------------------------------

RESULTS_DIR = os.path.join(PROJECT_ROOT, "model", "results")
OUTPUT_CSV = os.path.join(RESULTS_DIR, "rf_predictions.csv")

COLAB_DRIVE_PATHS = [
    "/content/drive/MyDrive/cicids2017_cleaned.csv",
    "/content/drive/MyDrive/MAJOR-PROJECT-CNN-LSTM-IDS/datasets/merged/cicids2017_cleaned.csv",
    "/content/drive/MyDrive/datasets/merged/cicids2017_cleaned.csv",
    "/content/cicids2017_cleaned.csv",
]

SELECTED_FEATURES = [
    'Bwd Packet Length Mean',
    'Packet Length Variance',
    'Packet Length Std',
    'Average Packet Size',
    'Total Length of Bwd Packets',
    'Bwd Packet Length Std',
    'Bwd Packet Length Max',
    'Total Length of Fwd Packets',
    'Packet Length Mean',
    'Max Packet Length',
    'Subflow Fwd Bytes',
    'Avg Bwd Segment Size',
    'Fwd IAT Std',
    'Fwd Packet Length Mean',
    'Subflow Bwd Bytes',
    'Flow IAT Max',
    'Avg Fwd Segment Size',
    'Fwd Packet Length Max',
    'Destination Port',
    'Subflow Fwd Packets',
]

LABEL_MAPPING = {
    'BENIGN': 0,
    'Bot': 1,
    'DDoS': 2,
    'DoS GoldenEye': 3,
    'DoS Hulk': 4,
    'DoS Slowhttptest': 5,
    'DoS slowloris': 6,
    'FTP-Patator': 7,
    'Heartbleed': 8,
    'Infiltration': 9,
    'PortScan': 10,
    'SSH-Patator': 11,
    'Web Attack - Brute Force': 12,
    'Web Attack - Sql Injection': 13,
    'Web Attack - XSS': 14,
}

# Reverse mapping: int -> label string (for decoding predictions)
INT_TO_LABEL = {v: k for k, v in LABEL_MAPPING.items()}
CLASS_NAMES = [INT_TO_LABEL[i] for i in range(len(LABEL_MAPPING))]


def resolve_dataset_path(custom_path=None) -> str:
    """
    Resolves dataset path in order of priority:
      1. Explicit --data-path argument
      2. DATASET_PATH environment variable
      3. Google Drive mount paths in Colab
      4. Local relative fallback path
    """
    if custom_path and os.path.exists(custom_path):
        return custom_path

    env_path = os.environ.get("DATASET_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    for drive_path in COLAB_DRIVE_PATHS:
        if os.path.exists(drive_path):
            return drive_path

    return os.path.join(PROJECT_ROOT, "datasets", "merged", "cicids2017_cleaned.csv")


def load_full_dataset(dataset_path: str) -> pd.DataFrame:
    """
    Loads the full CICIDS2017 dataset in chunks, using the same
    cleaning pipeline as baseline_full_dataset.py.
    """
    print("=" * 70)
    print("LOADING FULL DATASET")
    print("=" * 70)
    print(f"Source path: {dataset_path}")

    COLS_TO_LOAD = SELECTED_FEATURES + ['Label']
    chunks = []

    for chunk in pd.read_csv(dataset_path, chunksize=100_000, low_memory=False):
        chunk.columns = chunk.columns.str.strip()
        chunk['Label'] = chunk['Label'].astype(str).str.strip()

        # Corruption safety net (consistent with baseline_full_dataset.py)
        chunk['Label'] = chunk['Label'].str.replace('\ufffd', '-', regex=False)

        chunk = chunk[COLS_TO_LOAD]
        chunk.replace([np.inf, -np.inf], np.nan, inplace=True)
        chunk.dropna(inplace=True)
        chunk = chunk[chunk['Label'].isin(LABEL_MAPPING)]
        chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    print(f"\nFinal row count after cleaning : {len(df):,}")
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Export RF predictions + confidence scores to CSV for prevention simulation."
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Optional path to clean cicids2017_cleaned.csv dataset (overrides auto-detection).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-training even if rf_predictions.csv already exists.",
    )
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ----------------------------------------------------------------
    # Skip guard: re-use existing CSV unless --force is given
    # ----------------------------------------------------------------
    if os.path.exists(OUTPUT_CSV) and not args.force:
        existing = pd.read_csv(OUTPUT_CSV)
        print("=" * 70)
        print(f"[+] rf_predictions.csv already exists ({len(existing):,} rows).")
        print(f"    Path: {OUTPUT_CSV}")
        print(f"    Columns: {list(existing.columns)}")
        print("[+] Skipping re-training. Use --force to regenerate.")
        print("=" * 70)
        return

    # Resolve actual dataset location (Drive vs local vs custom arg)
    dataset_path = resolve_dataset_path(args.data_path)

    # ----------------------------------------------------------------
    # Step 1: Load + clean full dataset
    # ----------------------------------------------------------------
    df = load_full_dataset(dataset_path)

    # ----------------------------------------------------------------
    # Step 2: Encode labels + split
    # ----------------------------------------------------------------
    df['Label'] = df['Label'].map(LABEL_MAPPING)

    X = df[SELECTED_FEATURES].values.astype('float32')
    y = df['Label'].values.astype('int32')

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    print(f"\nTrain size : {len(X_train):,}")
    print(f"Test size  : {len(X_test):,}")

    # ----------------------------------------------------------------
    # Step 3: Train RF (identical hyperparameters to baseline_full_dataset.py)
    # ----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TRAINING: Random Forest (n_estimators=100, n_jobs=-1, random_state=42)")
    print("=" * 70)

    t0 = time.time()
    rf = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)
    rf.fit(X_train, y_train)
    train_secs = time.time() - t0
    print(f"[+] Training complete in {train_secs:.1f}s.")

    # ----------------------------------------------------------------
    # Step 4: Predict + predict_proba on the test set
    # ----------------------------------------------------------------
    print("[+] Running predict() and predict_proba() on test set...")

    y_pred = rf.predict(X_test)                    # shape: (n_test,)
    y_proba = rf.predict_proba(X_test)             # shape: (n_test, n_classes)

    # confidence = probability of the predicted class for each row
    confidence = y_proba[np.arange(len(y_pred)), y_pred]

    # Decode integer labels to class name strings
    predicted_class = [INT_TO_LABEL[i] for i in y_pred]
    true_class = [INT_TO_LABEL[i] for i in y_test]

    # ----------------------------------------------------------------
    # Step 5: Write CSV
    # ----------------------------------------------------------------
    df_out = pd.DataFrame({
        "predicted_class": predicted_class,
        "confidence": confidence,
        "true_class": true_class,
    })

    df_out.to_csv(OUTPUT_CSV, index=False)

    print(f"[+] Exported {len(df_out):,} rows to: {OUTPUT_CSV}")
    print("\nPredicted class distribution:")
    print(df_out["predicted_class"].value_counts().to_string())
    print("\nFirst 10 rows:")
    print(df_out.head(10).to_string(index=False))
    print("=" * 70)


if __name__ == "__main__":
    main()
