# CNN-LSTM Model Interface — Handoff for Dashboard Integration (Person C)

This document defines the contract for loading the trained CNN-LSTM model and
running inference on it. It's the reference for wiring the model into the
dashboard — read it fully before integrating, especially the "Known
Limitations" and "Sequence Construction" sections, since both affect how
predictions should be presented in the UI.

---

## 1. Artifacts

All three files live together in the repo, under `model/artifacts/` — this is now the real, versioned source of truth (no longer the Drive copy):

```
model/artifacts/cnn_lstm_best_v2.keras
model/artifacts/scaler_v2.pkl
model/artifacts/label_mapping_v2.json
```

| File | What it is |
|---|---|
| `cnn_lstm_best_v2.keras` | Trained Keras model. Load directly with `keras.models.load_model()` — architecture is unchanged from `model/cnn_lstm_architecture.py` (v1/v2/v3 only ever differed in the `class_weight` dict passed to `.fit()`, never the model definition), so `build_model()` is **not** needed unless retraining from scratch. |
| `scaler_v2.pkl` | Pickled `sklearn.preprocessing.StandardScaler`, fit on the training split's 20 feature columns. **Must** be applied to raw feature values before they reach the model — the model was never trained on unscaled input. |
| `label_mapping_v2.json` | `{label: int}`, e.g. `{"BENIGN": 0, "Bot": 1, "DDoS": 2, ...}` — the canonical class encoding, same one used across RF, CNN-LSTM, and the prevention policy table. The model's softmax output is index-ordered by these integers, so **decoding a prediction requires inverting this dict** (`int → label`) — don't assume the JSON file is already in that direction. |

---

## 2. Input Contract

- **Shape:** `(10, 20)` per sample — a 10-timestep sequence of 20 features. A batch is `(batch_size, 10, 20)`.
- **Features:** the same 20 selected columns used throughout the project, **in this exact order** (order matters — the model has no column names, only positions):

```python
FEATURE_COLS = [
    'Destination Port', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
    'Fwd Packet Length Max', 'Fwd Packet Length Mean', 'Bwd Packet Length Max',
    'Bwd Packet Length Mean', 'Bwd Packet Length Std', 'Flow IAT Max', 'Fwd IAT Std',
    'Max Packet Length', 'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
    'Average Packet Size', 'Avg Fwd Segment Size', 'Avg Bwd Segment Size',
    'Subflow Fwd Packets', 'Subflow Fwd Bytes', 'Subflow Bwd Bytes',
]
```

- **Scaling:** apply `scaler_v2.pkl`'s `.transform()` to the raw 20-feature rows **before** assembling them into a sequence (scale each row, then window — not the other way around).

## 3. Output Contract

- Softmax vector of length 15 (one probability per class).
- Decode the predicted class via the inverted `label_mapping_v2.json` (see code example below).
- The full probability vector (not just argmax) is worth keeping around — the prevention policy (`model/class_action_mapping.py`) and any "low confidence" UI treatment both key off confidence, not just the top label.

---

## 4. Test Performance

| Metric | Value |
|---|---|
| Accuracy | 0.9842 |
| Weighted F1 | 0.9864 |
| Macro F1 | 0.5857 |

The large gap between weighted F1 (0.9864) and macro F1 (0.5857) is expected and important to carry into the report/dashboard messaging: weighted F1 is dominated by BENIGN and the large attack classes; macro F1 weights every class equally and exposes that several minority classes perform poorly. Don't present accuracy or weighted F1 alone as "the" headline number — see limitations below.

---

## 5. Known Limitations (state these plainly — don't smooth them over)

- **Bot, Web Attack - Brute Force, and Web Attack - XSS have poor recall**, despite three different class-weighting strategies being tried across v1/v2/v3 (uniform heavy weighting, uniform dampened weighting, targeted per-class boost). This mirrors the RF baseline's own weakest classes, which is the reason to believe it's a **feature-level limitation, not a training artifact**: these attacks are distinguished by behavior/payload content (e.g. request contents, timing of brute-force attempts) that flow-level statistical features (packet lengths, inter-arrival times, byte counts) don't capture. More epochs, different weighting, or more training time would not be expected to fix this without different/additional features.
- **Web Attack - Sql Injection**: only 5 test examples. Any recall/precision number for this class is statistically noise, not a meaningful measurement. This is why the prevention policy hard-locks Sql Injection to `held_for_review` regardless of confidence (`model/class_action_mapping.py`) — the same reasoning applies to how the dashboard should treat this class: never present it as a confidently-detected class.
- **Infiltration: 0 test examples** in the sequence-windowed test set. Raw test rows existed for this class, but all of them fell within the first 9 rows of a day's sequence-window boundary and were excluded during windowing (a sequence needs 10 consecutive same-day rows to exist at all). Zero support means no metric can be reported for this class at all — this is a dataset-size limitation, not a bug.
- **Dashboard messaging implication:** for these four classes (Bot, Web Attack - Brute Force, Web Attack - XSS, Web Attack - Sql Injection, and Infiltration), avoid presenting model confidence as a reliable signal in the UI. Consider a visual "low-confidence class" marker, or simply lean on the prevention policy's `held_for_review` path, which already exists for exactly this reason.

---

## 6. Sequence Construction — Open Nuance, Not Silently Resolved

Training built sequences **day-aware**: a 10-row sliding window was never allowed to span two different `source_day` capture sessions (Monday, Tuesday, ... Friday_DDoS), because two different capture days aren't temporally continuous, and a window spanning them would encode a relationship the model never actually saw in real traffic.

**This doesn't map cleanly onto live dashboard inference**, and hasn't been tested or resolved — flagging it explicitly rather than assuming it's fine:

- In live inference there's no explicit "day" boundary — you're presumably buffering the most recent 10 flows from one ongoing capture/session.
- The closest analogous risk: if the traffic sensor has a gap (restart, reconnect, monitoring downtime), the 10 buffered flows could span across that gap the same way a day-boundary window would in training — an artificial temporal relationship the model was never trained to handle.
- Options worth considering, not yet decided:
  1. Treat it as negligible — a gap landing exactly inside a 10-flow buffer window may be rare enough in practice not to matter.
  2. Track a session/capture-start marker (analogous to `source_day`) and reset the sequence buffer on any detected gap.
  3. Accept and document it as a known limitation in the report, the same way the class-imbalance limitations above are documented, rather than solving it in the remaining time.

Whichever way this goes, it should be a deliberate call, not a default.

---

## 7. Loading and Running Inference

```python
import json
import pickle
import numpy as np
from tensorflow import keras

MODEL_PATH = "model/artifacts/cnn_lstm_best_v2.keras"
SCALER_PATH = "model/artifacts/scaler_v2.pkl"
LABEL_MAP_PATH = "model/artifacts/label_mapping_v2.json"

FEATURE_COLS = [
    'Destination Port', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
    'Fwd Packet Length Max', 'Fwd Packet Length Mean', 'Bwd Packet Length Max',
    'Bwd Packet Length Mean', 'Bwd Packet Length Std', 'Flow IAT Max', 'Fwd IAT Std',
    'Max Packet Length', 'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
    'Average Packet Size', 'Avg Fwd Segment Size', 'Avg Bwd Segment Size',
    'Subflow Fwd Packets', 'Subflow Fwd Bytes', 'Subflow Bwd Bytes',
]

# --- Load once at startup ---
model = keras.models.load_model(MODEL_PATH)

with open(SCALER_PATH, "rb") as f:
    scaler = pickle.load(f)

with open(LABEL_MAP_PATH) as f:
    label_to_int = json.load(f)
int_to_label = {v: k for k, v in label_to_int.items()}  # softmax index -> label


def predict(flow_rows):
    """
    flow_rows: 10 raw flow records (dicts keyed by FEATURE_COLS names, or
    anything indexable the same way), in FEATURE_COLS order, most-recent
    last, drawn from the same underlying traffic stream (see Section 6 —
    don't span a known capture gap without deciding how to handle it).

    Returns the predicted class, its confidence, and the full probability
    distribution over all 15 classes.
    """
    if len(flow_rows) != 10:
        raise ValueError(f"Expected 10 flow rows for one sequence, got {len(flow_rows)}")

    # Build a (10, 20) raw feature matrix
    X_raw = np.array(
        [[row[col] for col in FEATURE_COLS] for row in flow_rows],
        dtype="float32",
    )

    # Scale each row (scaler expects 2D: n_rows x 20 features)
    X_scaled = scaler.transform(X_raw)

    # Add batch dimension -> (1, 10, 20)
    X_seq = X_scaled[np.newaxis, :, :]

    probs = model.predict(X_seq, verbose=0)[0]  # (15,)
    pred_idx = int(np.argmax(probs))

    return {
        "predicted_class": int_to_label[pred_idx],
        "confidence": float(probs[pred_idx]),
        "probabilities": {int_to_label[i]: float(p) for i, p in enumerate(probs)},
    }


# Example usage:
# result = predict(last_10_flow_records)
# print(result["predicted_class"], result["confidence"])
```

To turn a prediction into a recommended action (for the prevention/IPS side of
the dashboard), pass `predicted_class` and `confidence` into
`model/class_action_mapping.py`'s `get_action()` — see `model/prevention_simulation.py`
for a working example of that hookup.
