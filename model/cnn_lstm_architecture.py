"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : CNN-LSTM Architecture Definition
Author  : Maanya & Team
==========================================================
Defines a hybrid CNN-LSTM model for network intrusion
detection on the CICIDS2017 dataset.
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import (
    Conv1D,
    MaxPooling1D,
    LSTM,
    Dense,
    Dropout,
    BatchNormalization,
)
from tensorflow.keras.models import Sequential


def build_cnn_lstm_model(input_shape, num_classes):
    """
    Build a hybrid CNN-LSTM Sequential model.

    Architecture:
        Conv1D(64) -> BN -> MaxPool -> Conv1D(128) -> BN -> MaxPool
        -> LSTM(64) -> Dropout -> Dense(64) -> Dropout -> Dense(softmax)

    Args:
        input_shape : tuple  – (sequence_length, num_features)
        num_classes : int    – number of output classes

    Returns:
        tf.keras.Model – compiled Sequential model
    """

    model = Sequential([
        # --- CNN Feature Extraction Block 1 ---
        Conv1D(filters=64, kernel_size=3, activation='relu',
               padding='same', input_shape=input_shape),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),

        # --- CNN Feature Extraction Block 2 ---
        Conv1D(filters=128, kernel_size=3, activation='relu',
               padding='same'),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),

        # --- LSTM Temporal Learning ---
        LSTM(64, return_sequences=False),
        Dropout(0.3),

        # --- Fully Connected Classifier ---
        Dense(64, activation='relu'),
        Dropout(0.3),
        Dense(num_classes, activation='softmax'),
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy'],
    )

    return model


# ------------------------------------------------------------------
# Smoke test: verify architecture builds, compiles, and trains
# ------------------------------------------------------------------
if __name__ == "__main__":

    # Dummy synthetic data
    # 500 samples, sequence_length=10, num_features=40
    X_dummy = np.random.rand(500, 10, 40).astype('float32')

    # 6 classes (DoS, DDoS, brute-force, port scanning, web attacks, normal)
    y_dummy = np.random.randint(0, 6, size=(500,))

    # Build model
    model = build_cnn_lstm_model(input_shape=(10, 40), num_classes=6)

    # Print summary
    model.summary()

    # Quick training run
    model.fit(
        X_dummy, y_dummy,
        epochs=2,
        batch_size=32,
        validation_split=0.2,
        verbose=1,
    )

    print("\nArchitecture test completed successfully - no crashes.")
