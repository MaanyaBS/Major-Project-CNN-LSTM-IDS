"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Baseline – Random Forest
Author  : Maanya & Team
==========================================================
Trains a Random Forest classifier on a 100k-row sample of
the cleaned CICIDS2017 dataset and saves results.
"""

import os
import sys
import numpy as np

# Ensure the project root is on sys.path so `model.load_data` resolves
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from model.load_data import load_cleaned_data

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)


def main():
    # ------------------------------------------------------------------
    # 1. Load cleaned data
    # ------------------------------------------------------------------
    df = load_cleaned_data()

    # ------------------------------------------------------------------
    # 2. Sample 100,000 rows for fast baseline training
    # ------------------------------------------------------------------
    print("\nSampling 100,000 rows (random_state=42) ...")
    df_sample = df.sample(n=100_000, random_state=42).reset_index(drop=True)
    print(f"Sample shape: {df_sample.shape}")

    # Drop classes with fewer than 2 samples (can't stratify-split them)
    label_counts = df_sample["Label"].value_counts()
    rare_classes = label_counts[label_counts < 2].index.tolist()
    if rare_classes:
        print(f"  ⚠ Dropping rare classes with <2 samples: {rare_classes}")
        df_sample = df_sample[~df_sample["Label"].isin(rare_classes)].reset_index(drop=True)
        print(f"  Sample shape after drop: {df_sample.shape}")

    # ------------------------------------------------------------------
    # 3. Encode labels
    # ------------------------------------------------------------------
    le = LabelEncoder()
    y = le.fit_transform(df_sample["Label"])
    X = df_sample.drop(columns=["Label"])

    class_names = le.classes_
    print(f"Classes ({len(class_names)}): {list(class_names)}")

    # ------------------------------------------------------------------
    # 4. Train / test split (80/20, stratified)
    # ------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Train size: {X_train.shape[0]:,}  |  Test size: {X_test.shape[0]:,}")

    # ------------------------------------------------------------------
    # 5. Feature scaling
    # ------------------------------------------------------------------
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # ------------------------------------------------------------------
    # 6. Train Random Forest
    # ------------------------------------------------------------------
    print("\nTraining RandomForest (n_estimators=100, random_state=42) ...")
    model = RandomForestClassifier(
        n_estimators=100, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)
    print("Training complete.")

    # ------------------------------------------------------------------
    # 7. Evaluate
    # ------------------------------------------------------------------
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=class_names, zero_division=0)

    # ------------------------------------------------------------------
    # 8. Print results
    # ------------------------------------------------------------------
    results_text = (
        "=" * 70 + "\n"
        "BASELINE – RANDOM FOREST RESULTS\n"
        "=" * 70 + "\n\n"
        f"Sample size      : 100,000\n"
        f"Train / Test     : 80,000 / 20,000\n\n"
        f"Accuracy         : {acc:.6f}\n"
        f"Precision (wt.)  : {prec:.6f}\n"
        f"Recall    (wt.)  : {rec:.6f}\n"
        f"F1-score  (wt.)  : {f1:.6f}\n\n"
        f"Classification Report:\n{report}\n\n"
        f"Confusion Matrix:\n{cm}\n"
        "=" * 70 + "\n"
    )

    print(results_text)

    # ------------------------------------------------------------------
    # 9. Save results
    # ------------------------------------------------------------------
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)

    results_path = os.path.join(results_dir, "random_forest_results.txt")
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(results_text)

    print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    main()
