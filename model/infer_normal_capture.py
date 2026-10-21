import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "output" / "live_captures" / "normal_browsing_10min_v2.flows.csv"
ARTIFACTS = ROOT / "model" / "artifacts"
OUTPUT = ROOT / "output" / "live_captures" / "normal_browsing_10min_v2.predictions.csv"
SUMMARY = ROOT / "output" / "live_captures" / "normal_browsing_10min_v2.prediction_summary.txt"

SEQUENCE_LENGTH = 10

FEATURES = [
    "Destination Port",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
    "Fwd Packet Length Mean",
    "Bwd Packet Length Max",
    "Bwd Packet Length Mean",
    "Bwd Packet Length Std",
    "Flow IAT Max",
    "Fwd IAT Std",
    "Max Packet Length",
    "Packet Length Mean",
    "Packet Length Std",
    "Packet Length Variance",
    "Average Packet Size",
    "Avg Fwd Segment Size",
    "Avg Bwd Segment Size",
    "Subflow Fwd Packets",
    "Subflow Fwd Bytes",
    "Subflow Bwd Bytes",
]


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Capture CSV not found: {INPUT}")

    df = pd.read_csv(INPUT)
    required = FEATURES + ["Flow Start", "Flow End"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    # Sort by flow start time before creating temporal windows.
    start_numeric = pd.to_numeric(df["Flow Start"], errors="coerce")
    if start_numeric.notna().all():
        df["_sort_time"] = start_numeric
    else:
        start_datetime = pd.to_datetime(df["Flow Start"], errors="coerce", utc=True)
        if start_datetime.isna().any():
            raise ValueError("Flow Start contains timestamps that cannot be sorted reliably.")
        df["_sort_time"] = start_datetime

    # Preserve the converter's original flow-end order.
    # flow_features.py emits completed flows in flow-end-time order.
    df = df.reset_index(drop=True)

    # Enforce numeric, finite feature values; report any rows excluded.
    X_df = df[FEATURES].apply(pd.to_numeric, errors="coerce")
    finite_rows = np.isfinite(X_df.to_numpy(dtype=np.float64)).all(axis=1)
    dropped = int((~finite_rows).sum())
    df = df.loc[finite_rows].reset_index(drop=True)
    X_df = X_df.loc[finite_rows].reset_index(drop=True)

    if len(df) < SEQUENCE_LENGTH:
        raise ValueError(f"Only {len(df)} valid flows; need at least {SEQUENCE_LENGTH}.")

    scaler_path = ARTIFACTS / "scaler_v2.pkl"
    model_path = ARTIFACTS / "cnn_lstm_best_v2.keras"
    mapping_path = ARTIFACTS / "label_mapping_v2.json"

    scaler = joblib.load(scaler_path)
    with mapping_path.open("r", encoding="utf-8") as f:
        label_to_id = json.load(f)
    id_to_label = {int(v): k for k, v in label_to_id.items()}

    if hasattr(scaler, "n_features_in_") and scaler.n_features_in_ != len(FEATURES):
        raise ValueError(
            f"Scaler expects {scaler.n_features_in_} features, but this script has {len(FEATURES)}."
        )

    scaled = scaler.transform(X_df).astype(np.float32)

    # Overlapping windows: 10 flows per window, advancing by one flow.
    windows = np.stack([
        scaled[i:i + SEQUENCE_LENGTH]
        for i in range(len(scaled) - SEQUENCE_LENGTH + 1)
    ])

    model = load_model(model_path, compile=False)
    expected_shape = tuple(model.input_shape[1:])
    if expected_shape != (SEQUENCE_LENGTH, len(FEATURES)):
        raise ValueError(
            f"Model expects {expected_shape}; script is preparing "
            f"({SEQUENCE_LENGTH}, {len(FEATURES)}). Stop and verify the model interface."
        )

    probabilities = model.predict(windows, batch_size=256, verbose=1)
    if probabilities.ndim != 2 or probabilities.shape[1] != len(id_to_label):
        raise ValueError(
            f"Unexpected model output shape {probabilities.shape}; "
            f"mapping contains {len(id_to_label)} classes."
        )

    class_ids = probabilities.argmax(axis=1)
    confidences = probabilities.max(axis=1)

    result = pd.DataFrame({
        "window_start_flow_index": np.arange(len(windows)),
        "window_end_flow_index": np.arange(SEQUENCE_LENGTH - 1, len(df)),
        "window_start_time": df["Flow Start"].iloc[:-SEQUENCE_LENGTH + 1].to_numpy(),
        "window_end_time": df["Flow End"].iloc[SEQUENCE_LENGTH - 1:].to_numpy(),
        "predicted_class_id": class_ids,
        "predicted_label": [id_to_label[int(i)] for i in class_ids],
        "confidence": confidences,
        "benign_probability": probabilities[:, label_to_id["BENIGN"]],
    })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)

    counts = result["predicted_label"].value_counts()
    lines = [
        "NORMAL-BROWSING CAPTURE: CNN-LSTM INFERENCE",
        f"Input: {INPUT}",
        f"Valid flows: {len(df)}",
        f"Rows excluded for invalid feature values: {dropped}",
        f"Window length: {SEQUENCE_LENGTH}",
        "Window stride: 1 flow (overlapping windows)",
        f"Prediction windows: {len(result)}",
        f"Mean maximum-class confidence: {result['confidence'].mean():.6f}",
        f"Median maximum-class confidence: {result['confidence'].median():.6f}",
        f"Windows predicted BENIGN: {(result['predicted_label'] == 'BENIGN').sum()}",
        "",
        "Predicted class counts:",
    ]
    lines.extend(f"  {label}: {count}" for label, count in counts.items())
    lines.extend([
        "",
        "Caution: this capture has no ground-truth labels.",
        "These are model predictions, not an accuracy or false-positive-rate evaluation.",
        "Confidence is the model's maximum softmax probability, not a guarantee of correctness.",
        f"Predictions CSV: {OUTPUT}",
    ])

    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved predictions: {OUTPUT}")
    print(f"Saved summary: {SUMMARY}")


if __name__ == "__main__":
    main()