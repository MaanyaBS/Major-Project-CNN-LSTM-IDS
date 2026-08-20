"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : 13 - Feature Separability Analysis
Purpose : Identify excluded features that may help weak classes
==========================================================
"""

import os
import pandas as pd
import numpy as np

DATA_PATH = r"D:\Major_Project\dataset\merged\cicids2017_cleaned_with_day.csv"
OUTPUT_PATH = r"D:\Major_Project\output\feature_separability_report.csv"

# Current top-20 features
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
    'Subflow Fwd Packets'
]

TARGET_CLASSES = [
    'Bot',
    'Web Attack - Brute Force',
    'Web Attack - XSS',
    'Web Attack - Sql Injection'
]

print("=" * 80)
print("FEATURE SEPARABILITY ANALYSIS")
print("=" * 80)

print("\nLoading dataset...")

df = pd.read_csv(DATA_PATH)

print("Dataset Shape:", df.shape)

# ------------------------------------------------------------------
# Reproduce the same chronological 80% training portion
# ------------------------------------------------------------------

print("\nCreating chronological training portion...")

train_parts = []

for source, group in df.groupby('source_day', sort=False):

    split_index = int(len(group) * 0.80)

    train_group = group.iloc[:split_index].copy()

    train_parts.append(train_group)

    print(
        f"{source:25s} "
        f"Total={len(group):8d} "
        f"Train={len(train_group):8d}"
    )

train_df = pd.concat(train_parts, ignore_index=True)

print("\nChronological training shape:", train_df.shape)

# ------------------------------------------------------------------
# Identify excluded features
# ------------------------------------------------------------------

all_features = [
    c for c in df.columns
    if c not in ['Label', 'source_day']
]

excluded_features = [
    c for c in all_features
    if c not in SELECTED_FEATURES
]

print("\nTotal original features :", len(all_features))
print("Current top-20 features :", len(SELECTED_FEATURES))
print("Excluded features       :", len(excluded_features))

# ------------------------------------------------------------------
# Convert feature columns to numeric
# ------------------------------------------------------------------

for feature in excluded_features:
    train_df[feature] = pd.to_numeric(
        train_df[feature],
        errors='coerce'
    )

# ------------------------------------------------------------------
# Analyze each weak class vs BENIGN
# ------------------------------------------------------------------

results = []

for attack_class in TARGET_CLASSES:

    print("\n" + "=" * 70)
    print(f"{attack_class} vs BENIGN")
    print("=" * 70)

    benign = train_df[train_df['Label'] == 'BENIGN']
    attack = train_df[train_df['Label'] == attack_class]

    print("BENIGN rows:", len(benign))
    print(f"{attack_class} rows:", len(attack))

    if len(attack) == 0:
        print("No samples found. Skipping.")
        continue

    for feature in excluded_features:

        benign_values = benign[feature].dropna()
        attack_values = attack[feature].dropna()

        if len(benign_values) == 0 or len(attack_values) == 0:
            continue

        benign_mean = benign_values.mean()
        attack_mean = attack_values.mean()

        benign_std = benign_values.std()
        attack_std = attack_values.std()

        benign_median = benign_values.median()
        attack_median = attack_values.median()

        # Cohen-like standardized separation
        pooled_std = np.sqrt(
            (benign_std ** 2 + attack_std ** 2) / 2
        )

        if pooled_std > 0:
            separation = abs(
                attack_mean - benign_mean
            ) / pooled_std
        else:
            separation = 0

        results.append({
            'Attack_Class': attack_class,
            'Feature': feature,
            'BENIGN_Mean': benign_mean,
            'Attack_Mean': attack_mean,
            'BENIGN_Std': benign_std,
            'Attack_Std': attack_std,
            'BENIGN_Median': benign_median,
            'Attack_Median': attack_median,
            'Separation_Score': separation
        })

# ------------------------------------------------------------------
# Save results
# ------------------------------------------------------------------

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    ['Attack_Class', 'Separation_Score'],
    ascending=[True, False]
)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

results_df.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\n" + "=" * 80)
print("TOP FEATURES BY CLASS")
print("=" * 80)

for attack_class in TARGET_CLASSES:

    class_results = results_df[
        results_df['Attack_Class'] == attack_class
    ].head(10)

    print(f"\n{attack_class}:")
    print(
        class_results[
            [
                'Feature',
                'BENIGN_Mean',
                'Attack_Mean',
                'Separation_Score'
            ]
        ].to_string(index=False)
    )

print("\n" + "=" * 80)
print("REPORT SAVED")
print("=" * 80)

print(OUTPUT_PATH)
print("\nCompleted Successfully!")