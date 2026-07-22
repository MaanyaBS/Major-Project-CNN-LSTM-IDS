"""
==========================================================
Project : CNN-LSTM Intrusion Detection System
Module  : Sequence Reshaping (Sliding Window)
Author  : Maanya & Team
==========================================================
Converts flat tabular network-flow data into overlapping
temporal sequences suitable for LSTM / CNN-LSTM models.
"""

import numpy as np
import pandas as pd


def create_sequences(data, labels, sequence_length):
    """
    Create overlapping temporal sequences from flat tabular data
    using a sliding window approach.

    Why sliding windows for LSTM?
    ----------------------------
    LSTM networks expect 3D input of shape (samples, timesteps, features).
    Raw network-flow datasets like CICIDS2017 are stored as independent
    rows (2D).  By grouping `sequence_length` consecutive rows into a
    single window, we give the LSTM a short history of recent flows to
    learn temporal patterns — e.g. a burst of SYN packets preceding a
    port scan, or a slow ramp-up characteristic of slowloris attacks.

    The window slides one row at a time (stride=1), so successive
    sequences overlap by (sequence_length - 1) rows.  The label
    assigned to each sequence is the label of the **last** row in that
    window, reflecting the most recent classification decision.

    Parameters
    ----------
    data : np.ndarray, shape (num_rows, num_features)
        Feature matrix (already scaled / encoded).
    labels : np.ndarray, shape (num_rows,)
        Corresponding integer-encoded class labels.
    sequence_length : int
        Number of consecutive rows per sequence (window size).

    Returns
    -------
    X : np.ndarray, shape (num_rows - sequence_length + 1,
                           sequence_length, num_features)
        3D array of overlapping sequences.
    y : np.ndarray, shape (num_rows - sequence_length + 1,)
        Label for each sequence (label of the last row in the window).
    """

    X, y = [], []

    for i in range(len(data) - sequence_length + 1):
        X.append(data[i : i + sequence_length])
        y.append(labels[i + sequence_length - 1])   # label of last row

    return np.array(X), np.array(y)


# ------------------------------------------------------------------
# Smoke test: verify shapes on dummy data
# ------------------------------------------------------------------
if __name__ == "__main__":

    # Dummy data: 1000 rows, 68 features (matching real feature count)
    dummy_data = np.random.rand(1000, 68).astype("float32")

    # 15 classes (matching real CICIDS2017 label count)
    dummy_labels = np.random.randint(0, 15, size=(1000,))

    sequence_length = 10

    X, y = create_sequences(dummy_data, dummy_labels, sequence_length)

    print(f"X.shape : {X.shape}")        # expect (991, 10, 40)
    print(f"y.shape : {y.shape}")        # expect (991,)

    print(f"\nFirst sequence shape  : {X[0].shape}")
    print(f"Second sequence shape : {X[1].shape}")

    print(f"\nFirst 5 label values  : {y[:5]}")

    print("\nSequence reshaping test completed successfully.")
