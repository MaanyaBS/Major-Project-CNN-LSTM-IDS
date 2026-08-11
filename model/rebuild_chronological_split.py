"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Chronological Split Rebuild Script
Author  : Person B (Model Development)
==========================================================
Rebuilds a day-and-label-stratified chronological train/test split from the
source-tagged dataset (cicids2017_cleaned_with_day.csv), then builds
day-aware sliding-window sequences for CNN-LSTM training.

A pure day-level 80/20 split silently dropped 8 of 15 attack classes from
the test set entirely (an entire class's attack burst could land wholly
within the first 80% of a day). Splitting independently within each
(source_day, Label) group guarantees every class with enough samples
appears in both train and test, while still respecting chronological order
within each class's own occurrences.
"""

import os
import argparse
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    'Destination Port', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
    'Fwd Packet Length Max', 'Fwd Packet Length Mean', 'Bwd Packet Length Max',
    'Bwd Packet Length Mean', 'Bwd Packet Length Std', 'Flow IAT Max', 'Fwd IAT Std',
    'Max Packet Length', 'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
    'Average Packet Size', 'Avg Fwd Segment Size', 'Avg Bwd Segment Size',
    'Subflow Fwd Packets', 'Subflow Fwd Bytes', 'Subflow Bwd Bytes',
]


def _create_sequences_day_aware(X_df, y_df, feature_cols, label_col, seq_length=10, day_col='source_day'):
    """Build sliding-window sequences, never crossing a source_day boundary."""
    X_parts, y_parts = [], []
    for day, group in X_df.groupby(day_col, sort=False):
        idx = group.index
        X_day = group[feature_cols].values.astype('float32')
        y_day = y_df.loc[idx, label_col].values
        n = len(X_day)
        if n < seq_length:
            continue
        windows = np.lib.stride_tricks.sliding_window_view(X_day, window_shape=seq_length, axis=0)
        windows = windows.transpose(0, 2, 1)
        labels = y_day[seq_length - 1:]
        X_parts.append(windows)
        y_parts.append(labels)
    return np.concatenate(X_parts, axis=0), np.concatenate(y_parts, axis=0)


def rebuild_chronological_split(source_csv_path, label_mapping_path, output_dir, seq_length=10):
    """
    Loads the day-tagged source CSV, applies a day+label stratified 80/20
    split, scales features (fit on train only), maps labels via the
    canonical label_mapping.csv, and builds day-aware sequence windows.

    Saves X_train_seq.npy, y_train_seq.npy, X_test_seq.npy, y_test_seq.npy
    to output_dir and returns them.
    """
    full_df = pd.read_csv(source_csv_path)
    # Re-applies the same U+FFFD fix used in 05_label_encoding.py; the
    # rebuild path doesn't currently pass through that script, so labels
    # need the fix re-applied here.
    full_df['Label'] = full_df['Label'].str.replace('\ufffd', '-', regex=False)

    df = full_df[FEATURE_COLS + ['source_day', 'Label']].copy()
    df = df.reset_index(drop=False).rename(columns={'index': 'orig_idx'})

    train_parts, test_parts = [], []
    for (day, label), group in df.groupby(['source_day', 'Label'], sort=False):
        g = group.sort_values('orig_idx')
        split = int(len(g) * 0.8)
        train_parts.append(g.iloc[:split])
        test_parts.append(g.iloc[split:])

    train_df = pd.concat(train_parts).sort_values(['source_day', 'orig_idx']).reset_index(drop=True)
    test_df = pd.concat(test_parts).sort_values(['source_day', 'orig_idx']).reset_index(drop=True)

    scaler = StandardScaler()
    train_df[FEATURE_COLS] = scaler.fit_transform(train_df[FEATURE_COLS])
    test_df[FEATURE_COLS] = scaler.transform(test_df[FEATURE_COLS])

    label_mapping = pd.read_csv(label_mapping_path)
    label_mapping['Attack'] = label_mapping['Attack'].str.replace('\ufffd', '-', regex=False)
    label_to_int = dict(zip(label_mapping['Attack'], label_mapping['Encoded']))
    train_df['Label'] = train_df['Label'].map(label_to_int)
    test_df['Label'] = test_df['Label'].map(label_to_int)

    unmapped_train = train_df['Label'].isna().sum()
    unmapped_test = test_df['Label'].isna().sum()
    if unmapped_train or unmapped_test:
        raise ValueError(f"Unmapped labels found: train={unmapped_train}, test={unmapped_test}")

    X_train_seq, y_train_seq = _create_sequences_day_aware(
        train_df, train_df[['Label']], FEATURE_COLS, 'Label', seq_length
    )
    X_test_seq, y_test_seq = _create_sequences_day_aware(
        test_df, test_df[['Label']], FEATURE_COLS, 'Label', seq_length
    )

    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, 'X_train_seq.npy'), X_train_seq)
    np.save(os.path.join(output_dir, 'y_train_seq.npy'), y_train_seq)
    np.save(os.path.join(output_dir, 'X_test_seq.npy'), X_test_seq)
    np.save(os.path.join(output_dir, 'y_test_seq.npy'), y_test_seq)

    return X_train_seq, y_train_seq, X_test_seq, y_test_seq


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild day+label-stratified chronological sequences for CNN-LSTM training"
    )
    parser.add_argument(
        "--source", required=True,
        help="Path to cicids2017_cleaned_with_day.csv (source-of-truth, day-tagged dataset).",
    )
    parser.add_argument(
        "--label-mapping", required=True,
        help="Path to label_mapping.csv (canonical Attack -> Encoded mapping).",
    )
    parser.add_argument(
        "--output", required=True,
        help="Directory to save the 4 output .npy sequence files.",
    )
    parser.add_argument(
        "--seq-length", type=int, default=10,
        help="Sliding-window sequence length (default: 10).",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("CHRONOLOGICAL SPLIT REBUILD")
    print("=" * 70)
    print(f"[+] Source file:       {args.source}")
    print(f"[+] Label mapping:     {args.label_mapping}")
    print(f"[+] Output directory:  {args.output}")
    print(f"[+] Sequence length:   {args.seq_length}")

    X_train, y_train, X_test, y_test = rebuild_chronological_split(
        args.source, args.label_mapping, args.output, args.seq_length
    )

    print(f"[+] Train sequences: {X_train.shape}, labels: {y_train.shape}")
    print(f"[+] Test sequences:  {X_test.shape}, labels: {y_test.shape}")
    print(f"[+] Saved to: {args.output}")
    print("=" * 70)


if __name__ == "__main__":
    main()
