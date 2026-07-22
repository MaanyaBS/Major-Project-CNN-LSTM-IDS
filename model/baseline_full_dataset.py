"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Baseline Models on Full Dataset (20 Selected Features)
Author  : Maanya & Team
==========================================================
Trains Logistic Regression and Random Forest classifiers on
the FULL cleaned CICIDS2017 dataset using Person A's 20
selected top features and official label encoding.
"""

import sys
import time
import os
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
)

# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------

DATA_PATH = "datasets/merged/cicids2017_cleaned.csv"
RESULTS_DIR = "model/results"

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

# Target names in label-encoding order (0-14)
CLASS_NAMES = [
    'BENIGN', 'Bot', 'DDoS', 'DoS GoldenEye', 'DoS Hulk',
    'DoS Slowhttptest', 'DoS slowloris', 'FTP-Patator',
    'Heartbleed', 'Infiltration', 'PortScan', 'SSH-Patator',
    'Web Attack - Brute Force', 'Web Attack - Sql Injection',
    'Web Attack - XSS',
]

os.makedirs(RESULTS_DIR, exist_ok=True)

# ----------------------------------------------------------------
# STEP 1: Load & clean the full dataset in chunks
# ----------------------------------------------------------------

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8',
                  errors='replace', buffering=1)

print("=" * 70)
print("LOADING FULL DATASET")
print("=" * 70)

COLS_TO_LOAD = SELECTED_FEATURES + ['Label']

chunks = []

for chunk in pd.read_csv(DATA_PATH, chunksize=100_000, low_memory=False):

    # Strip whitespace from column names
    chunk.columns = chunk.columns.str.strip()

    # Strip whitespace from Label values
    chunk['Label'] = chunk['Label'].astype(str).str.strip()

    # Keep only needed columns
    chunk = chunk[COLS_TO_LOAD]

    # Replace inf with NaN, then drop NaN rows
    chunk.replace([np.inf, -np.inf], np.nan, inplace=True)
    chunk.dropna(inplace=True)

    # Keep only rows whose label is in the mapping
    chunk = chunk[chunk['Label'].isin(LABEL_MAPPING)]

    chunks.append(chunk)

df = pd.concat(chunks, ignore_index=True)

# ----------------------------------------------------------------
# STEP 2: Encode labels
# ----------------------------------------------------------------

df['Label'] = df['Label'].map(LABEL_MAPPING)

print(f"\nFinal row count after cleaning : {len(df):,}")
print(f"\nEncoded Label value_counts (sorted by label index):")
print(df['Label'].value_counts().sort_index())

# ----------------------------------------------------------------
# STEP 3: Train / test split
# ----------------------------------------------------------------

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
# Helper — evaluate and save results
# ----------------------------------------------------------------

def evaluate_and_save(model_name, y_test, y_pred, train_secs, out_path):
    acc    = accuracy_score(y_test, y_pred)
    f1_wt  = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    f1_mac = f1_score(y_test, y_pred, average='macro',    zero_division=0)
    report = classification_report(
        y_test, y_pred,
        target_names=CLASS_NAMES,
        zero_division=0,
    )

    header = "=" * 70
    text = (
        f"{header}\n"
        f"{model_name} — FULL DATASET RESULTS\n"
        f"{header}\n\n"
        f"Training time    : {train_secs:.2f}s\n"
        f"Accuracy         : {acc:.6f}\n"
        f"F1-score (wt.)   : {f1_wt:.6f}\n"
        f"F1-score (macro) : {f1_mac:.6f}\n\n"
        f"Classification Report:\n{report}\n"
        f"{header}\n"
    )

    print(text)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Results saved to : {out_path}\n")


# ----------------------------------------------------------------
# STEP 4: Logistic Regression
# ----------------------------------------------------------------

print("\n" + "=" * 70)
print("TRAINING: Logistic Regression")
print("=" * 70)

t0 = time.time()
lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(X_train, y_train)
lr_time = time.time() - t0
print(f"Training time: {lr_time:.2f}s")

y_pred_lr = lr.predict(X_test)
evaluate_and_save(
    "Logistic Regression",
    y_test, y_pred_lr, lr_time,
    os.path.join(RESULTS_DIR, "full_dataset_logistic_regression_results.txt"),
)

# ----------------------------------------------------------------
# STEP 5: Random Forest
# ----------------------------------------------------------------

print("=" * 70)
print("TRAINING: Random Forest")
print("=" * 70)

t0 = time.time()
rf = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)
rf.fit(X_train, y_train)
rf_time = time.time() - t0
print(f"Training time: {rf_time:.2f}s")

y_pred_rf = rf.predict(X_test)
evaluate_and_save(
    "Random Forest",
    y_test, y_pred_rf, rf_time,
    os.path.join(RESULTS_DIR, "full_dataset_random_forest_results.txt"),
)

print("=" * 70)
print("FULL DATASET BASELINE TRAINING COMPLETE")
print("=" * 70)
