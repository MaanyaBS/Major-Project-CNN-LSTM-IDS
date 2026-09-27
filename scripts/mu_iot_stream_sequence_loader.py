import numpy as np
import pandas as pd
import os

# ============================================================
# PATHS
# ============================================================

DATA_DIR = (
    r"D:\Major_Project\dataset\processed\mu_iot"
    r"\temporal_training_data"
)

MEMMAP_PATH = os.path.join(
    DATA_DIR,
    "mu_iot_scaled_40features_float32.dat"
)

METADATA_PATH = os.path.join(
    DATA_DIR,
    "mu_iot_temporal_metadata.csv"
)

# ============================================================
# SETTINGS
# ============================================================

SEQ_LEN = 20
N_FEATURES = 40
BATCH_SIZE = 128

# ============================================================
# LOAD METADATA
# ============================================================

print("=" * 70)
print("MU-IoT STREAMING SEQUENCE LOADER")
print("=" * 70)

print("\nLoading metadata...")

metadata = pd.read_csv(
    METADATA_PATH
)

metadata = metadata.sort_values(
    "row_id"
).reset_index(drop=True)

print(
    f"Rows: {len(metadata):,}"
)

# ============================================================
# OPEN MEMMAP
# ============================================================

X = np.memmap(
    MEMMAP_PATH,
    dtype="float32",
    mode="r",
    shape=(len(metadata), N_FEATURES)
)

print(
    f"Memmap shape: {X.shape}"
)

# ============================================================
# FIND VALID SEQUENCE STARTS
# ============================================================

def find_sequence_starts(
    metadata,
    split_name
):
    """
    Find sequence starting row positions.

    A valid sequence must:
    1. belong to one split
    2. belong to one capture session
    3. contain 20 consecutive row IDs
    """

    part = metadata[
        metadata["split"] == split_name
    ]

    starts = []

    for session in part[
        "capture_session"
    ].unique():

        session_df = part[
            part["capture_session"] == session
        ]

        row_ids = session_df[
            "row_id"
        ].to_numpy()

        if len(row_ids) < SEQ_LEN:
            continue

        gaps = np.diff(row_ids)

        valid = np.where(
            np.convolve(
                (gaps == 1).astype(np.int8),
                np.ones(
                    SEQ_LEN - 1,
                    dtype=np.int8
                ),
                mode="valid"
            )
            == SEQ_LEN - 1
        )[0]

        starts.extend(
            row_ids[valid].tolist()
        )

    return np.asarray(
        starts,
        dtype=np.int64
    )


# ============================================================
# STREAM BATCHES
# ============================================================

def sequence_batch_generator(
    split_name,
    batch_size=BATCH_SIZE
):

    starts = find_sequence_starts(
        metadata,
        split_name
    )

    for batch_start in range(
        0,
        len(starts),
        batch_size
    ):

        batch_starts = starts[
            batch_start:
            batch_start + batch_size
        ]

        X_batch = np.empty(
            (
                len(batch_starts),
                SEQ_LEN,
                N_FEATURES
            ),
            dtype=np.float32
        )

        y_batch = []

        for i, start_row in enumerate(
            batch_starts
        ):

            end_row = (
                start_row + SEQ_LEN
            )

            X_batch[i] = X[
                start_row:end_row
            ]

            # Label = final timestep
            y_batch.append(
                metadata.iloc[
                    end_row - 1
                ]["category"]
            )

        yield (
            X_batch,
            np.asarray(y_batch)
        )


# ============================================================
# TEST EACH SPLIT
# ============================================================

for split_name in [
    "train",
    "validation",
    "test"
]:

    print(
        f"\n{'-' * 70}"
    )

    print(
        f"Testing split: {split_name}"
    )

    starts = find_sequence_starts(
        metadata,
        split_name
    )

    print(
        f"Available sequences: "
        f"{len(starts):,}"
    )

    if len(starts) == 0:
        raise ValueError(
            f"No sequences found for {split_name}"
        )

    # --------------------------------------------------------
    # Read first batch
    # --------------------------------------------------------

    generator = sequence_batch_generator(
        split_name,
        batch_size=BATCH_SIZE
    )

    X_batch, y_batch = next(
        generator
    )

    print(
        "X batch shape:",
        X_batch.shape
    )

    print(
        "y batch shape:",
        y_batch.shape
    )

    # --------------------------------------------------------
    # Validate shape
    # --------------------------------------------------------

    if X_batch.shape[1:] != (
        SEQ_LEN,
        N_FEATURES
    ):
        raise ValueError(
            "Incorrect sequence shape."
        )

    # --------------------------------------------------------
    # Validate NaN / Inf
    # --------------------------------------------------------

    if np.isnan(X_batch).any():
        raise ValueError(
            "NaN found."
        )

    if np.isinf(X_batch).any():
        raise ValueError(
            "Infinite value found."
        )

    # --------------------------------------------------------
    # Validate sequence metadata
    # --------------------------------------------------------

    for start_row in starts[:10]:

        end_row = (
            start_row + SEQ_LEN - 1
        )

        rows = metadata.iloc[
            start_row:end_row + 1
        ]

        if rows["split"].nunique() != 1:
            raise ValueError(
                "Sequence crosses split."
            )

        if (
            rows["capture_session"]
            .nunique()
            != 1
        ):
            raise ValueError(
                "Sequence crosses session."
            )

        if not (
            np.diff(
                rows["row_id"].to_numpy()
            ) == 1
        ).all():
            raise ValueError(
                "Non-consecutive sequence."
            )

    print(
        "Boundary check: PASS"
    )

    print(
        "NaN/Inf check: PASS"
    )

    print(
        "Shape check: PASS"
    )

# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("STREAMING SEQUENCE LOADER TEST PASSED")
print("=" * 70)

print(
    "Sequence length:",
    SEQ_LEN
)

print(
    "Features:",
    N_FEATURES
)

print(
    "Batch size:",
    BATCH_SIZE
)

print(
    "\nPerson A temporal data pipeline is ready "
    "for CNN-LSTM training."
)

print("=" * 70)