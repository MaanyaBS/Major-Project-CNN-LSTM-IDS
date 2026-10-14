"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : CNN-LSTM Training Script
Author  : Person B (Model Development)
==========================================================
Trains the CNN-LSTM architecture (model/cnn_lstm_architecture.py) on the
day-aware chronological sequences produced by
model/rebuild_chronological_split.py, with class weights, early stopping,
and best-checkpoint saving.

Class weights (--class-weights):
    sqrt     square root of 'balanced' weights, no cap - the deployed v2
             model (model/artifacts/cnn_lstm_best_v2.keras); the default
    capped   'balanced' weights capped at --class-weight-cap - the earlier
             v1 run, kept for comparison

The v2 settings here are the ones in the original Colab training cell
(notebooks/v2_training_cells.txt, cells 168-169). GPU training is not
bit-for-bit deterministic, so a retrain gives a close, not identical, model.
"""

import os
import pickle
import argparse
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from tensorflow import keras
from tensorflow.keras import layers, callbacks


def build_model(seq_length=10, n_features=20, n_classes=15):
    """Conv1D(64)->BN->MaxPool->Conv1D(128)->BN->MaxPool->LSTM(64)->Dense(64)->Softmax(n_classes)."""
    model = keras.Sequential([
        layers.Conv1D(64, 3, activation='relu', input_shape=(seq_length, n_features)),
        layers.BatchNormalization(),
        layers.MaxPooling1D(2),
        layers.Conv1D(128, 3, activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(2),
        layers.LSTM(64),
        layers.Dense(64, activation='relu'),
        layers.Dense(n_classes, activation='softmax'),
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model


def class_weights(y, mode='sqrt', cap=50):
    """'balanced' class weights, square-rooted (v2) or capped (v1)."""
    classes = np.unique(y)
    raw_weights = compute_class_weight('balanced', classes=classes, y=y)
    if mode == 'sqrt':
        weights = np.sqrt(raw_weights)
    elif mode == 'capped':
        weights = np.clip(raw_weights, None, cap)
    else:
        raise ValueError(f"Unknown class-weight mode {mode!r}; expected 'sqrt' or 'capped'")
    return dict(zip(classes.astype(int), weights))


def train(sequences_dir, checkpoint_path, history_path, epochs=25, batch_size=512,
          val_split=0.1, class_weights_mode='sqrt', class_weight_cap=50, patience=5, seed=42):
    """
    Loads X_train_seq.npy / y_train_seq.npy from sequences_dir, holds out a
    stratified validation split, trains with class weights and early
    stopping (monitor val_loss), and saves the best checkpoint plus
    training history.
    """
    X_train_seq = np.load(os.path.join(sequences_dir, 'X_train_seq.npy'))
    y_train_seq = np.load(os.path.join(sequences_dir, 'y_train_seq.npy'))

    X_tr, X_val, y_tr, y_val = train_test_split(
        X_train_seq, y_train_seq, test_size=val_split, stratify=y_train_seq, random_state=seed
    )

    # Uncapped 'balanced' weighting would give classes with single-digit
    # counts (Heartbleed, Sql Injection) weights in the thousands. v1 capped
    # them at 50, which still pushed BENIGN into rare classes (test macro F1
    # 0.43); v2 takes the square root instead (test macro F1 0.59).
    class_weight_dict = class_weights(y_tr, class_weights_mode, class_weight_cap)

    model = build_model(seq_length=X_train_seq.shape[1], n_features=X_train_seq.shape[2])

    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    cb = [
        callbacks.ModelCheckpoint(checkpoint_path, monitor='val_loss', save_best_only=True, verbose=1),
        callbacks.EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True, verbose=1),
    ]

    history = model.fit(
        X_tr, y_tr,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        class_weight=class_weight_dict,
        callbacks=cb,
        verbose=1,
    )

    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, 'wb') as f:
        pickle.dump(history.history, f)

    return model, history


def main():
    parser = argparse.ArgumentParser(
        description="Train the CNN-LSTM model on day-aware chronological sequences"
    )
    parser.add_argument(
        "--sequences-dir", required=True,
        help="Directory containing X_train_seq.npy / y_train_seq.npy (from rebuild_chronological_split.py).",
    )
    parser.add_argument(
        "--checkpoint", required=True,
        help="Path to save the best .keras checkpoint (e.g. models/cnn_lstm_best.keras).",
    )
    parser.add_argument(
        "--history", required=True,
        help="Path to save training_history.pkl (loss/accuracy curves).",
    )
    parser.add_argument("--epochs", type=int, default=25, help="Max training epochs (default: 25).")
    parser.add_argument("--batch-size", type=int, default=512, help="Training batch size (default: 512).")
    parser.add_argument("--val-split", type=float, default=0.1, help="Stratified validation split fraction (default: 0.1).")
    parser.add_argument("--class-weights", choices=["sqrt", "capped"], default="sqrt",
                        help="sqrt = deployed v2 model (default); capped = earlier v1 run.")
    parser.add_argument("--class-weight-cap", type=float, default=50, help="Cap for --class-weights capped (default: 50).")
    parser.add_argument("--patience", type=int, default=5, help="Early stopping patience on val_loss (default: 5).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for the validation split (default: 42).")
    args = parser.parse_args()

    print("=" * 70)
    print("CNN-LSTM TRAINING")
    print("=" * 70)
    print(f"[+] Sequences directory: {args.sequences_dir}")
    print(f"[+] Checkpoint path:     {args.checkpoint}")
    print(f"[+] History path:        {args.history}")
    print(f"[+] Epochs (max):        {args.epochs}")
    print(f"[+] Batch size:          {args.batch_size}")

    model, history = train(
        args.sequences_dir, args.checkpoint, args.history,
        epochs=args.epochs, batch_size=args.batch_size, val_split=args.val_split,
        class_weights_mode=args.class_weights, class_weight_cap=args.class_weight_cap,
        patience=args.patience, seed=args.seed,
    )

    print(f"[+] Best val_loss: {min(history.history['val_loss']):.4f}")
    print(f"[+] Stopped at epoch: {len(history.history['loss'])}")
    print(f"[+] Checkpoint saved to: {args.checkpoint}")
    print("=" * 70)


if __name__ == "__main__":
    main()
