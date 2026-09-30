# MU-IoT CNN-LSTM Model Interface — Handoff for Dashboard Integration

This document defines the contract for loading the MU-IoT model and running
inference on it. It is the MU-IoT counterpart of `model/MODEL_INTERFACE.md`
(CICIDS2017). The two models are separate: different features, window length,
classes and scaler. Nothing from one can be fed to the other.

Read Section 2 (input preparation) and Section 7 (prevention) before wiring
this in; both contain steps that fail silently if skipped.

---

## 1. Artifacts

```text
model/artifacts/mu_iot/best.keras
model/artifacts/mu_iot/scaler_38.pkl
model/artifacts/mu_iot/feature_list_38.json
model/artifacts/mu_iot/label_mapping.json
```

| File | What it is |
|---|---|
| `best.keras` | Trained model: the epoch-7 checkpoint that early stopping chose (of 12 epochs). This is the exact file the committed results in `model/results/mu_iot/` were produced from. Load with `keras.models.load_model(path, compile=False)`; `compile=False` skips the saved optimizer state, which inference doesn't need (loading it prints a harmless warning). |
| `scaler_38.pkl` | `sklearn.preprocessing.StandardScaler`, fitted on the 2,171,995 training rows only. It was fitted on a plain array, so it has **no column names**: column order is the only thing that ties values to features. Saved with scikit-learn 1.9.0; loading it on 1.6.1 prints a version warning, but its `transform` was checked to equal `(x - mean_) / scale_` exactly, so the warning does not affect results. |
| `feature_list_38.json` | The 38 input features, in model column order. |
| `label_mapping.json` | `{class name: index}`. The softmax output is in index order; invert this dict to decode. |

Verified before handoff: model input `(None, 20, 38)` and output `(None, 7)`;
feature order identical to `config/mu_iot_feature_sets.json`
(`paper_top48_coverage95_nonconstant_38`); no timestamp features (FPT/LPT);
label ids 0–6; `best.keras` is the epoch-7 file (its save time is 187 s before
`last.keras`, matching the logged duration of epochs 8–12).

---

## 2. Input Contract

- **Shape:** `(20, 38)` per sample: 20 consecutive flow records, 38 features
  each. A batch is `(batch_size, 20, 38)`.
- **Features**, in this exact order (from `feature_list_38.json`):

```text
FPC, RTSP_ML, RTSP_MUL, ECE_FC, DNS_RCUL, FD, DNS_QTUL, RTSP_MM, DNS_RCL,
DNSQTL, URG_FC, MQTT_MTUL, HTTP_SCL, ECN_M, MQTT_MTL, DSCP_S, ECN_S, TPackets,
TCPWS_Mode, PLM, DSCP_M, TCPWS_Mean, BJitter, BThroughput, HL_Mode, TCPWS_Sum,
MGA_UL, FAMax, FH_M, DSCP_UV, SDuration, FlowR, MGA_L, PacketsPS, FIMin,
ECN_C, FAMean, RCount
```

These are original MU-IoT CSV column names. Preparing one flow record takes
three steps, which reproduce what training did
(`src/12_mu_iot_preprocess.py`, then `scripts/build_mu_iot_handoff_v3.py`):

1. **Encode `RTSP_MM`.** In the raw MU-IoT CSVs this column holds an RTSP
   method *name* and is empty in almost every row. Training mapped it to a
   number: `GET_PARAMETER` 0, `SETUP` 1, `OPTIONS` 2, `TEARDOWN` 3,
   `DESCRIBE` 4, `PLAY` 5, anything else (including empty) −1. Skipping this
   step turns the column into NaN. Data exported from the cleaned file already
   holds the codes and passes through unchanged.
2. **Convert to numbers and reject non-finite values.** The other 37 columns
   are numeric. Training refused any NaN or infinite value, so the model has
   never seen one: reject such a row rather than filling it in.
3. **Scale** with `scaler_38.pkl` (`scaler.transform`), then cast to float32.
   Scale each row first, then assemble the window.

### Windows

- Training and evaluation windows were 20 **consecutive** rows from **one
  capture file**, in the file's original row order, never crossing a gap.
  Rows from different CSV files must never share a window.
- Evaluation used sliding windows (one window per row). The backend's
  current `predict_matrix()` cuts rows into non-overlapping blocks instead
  (one window per 20 rows). Both are valid inputs; the report should say
  which one the demo uses.
- Each MU-IoT CSV file is a single recording of a single class, so replaying
  one file gives windows that all have the same true label.

---

## 3. Output Contract

- Softmax vector of length 7, index-ordered by `label_mapping.json`:

| Index | Class |
|---|---|
| 0 | DDoS |
| 1 | Injection |
| 2 | MiTM |
| 3 | Password_Hacking |
| 4 | Scan |
| 5 | Spyware |
| 6 | normal |

- The benign class is `normal` (lowercase), not `BENIGN` as in CICIDS2017.
- Keep the full probability vector, not just the top class: confidence drives
  the prevention policy and any low-confidence UI treatment.

---

## 4. Test Performance

Two test tracks, reported separately
(`model/results/mu_iot/FINDINGS.md` has the full analysis):

- **test_within:** later traffic from the recordings used in training.
- **test_heldout:** four whole recordings never seen in training (the
  generalization test).

**Headline numbers:** scored only on windows whose exact 20-row sequence never
appears in training (`mu_iot_unseen_only_rescore.txt`):

| Track | Accuracy | Macro F1 |
|---|---|---|
| test_within | 0.964 | 0.936 |
| test_heldout | 0.680 | 0.676 |

- Normal traffic flagged as an attack (false-alarm rate): **9.3%**.
- Attacks classified as normal on unseen recordings: **0.08%**. The model
  almost never misses an attack; its held-out errors are about naming the
  attack type.

**Per-class F1** (all windows, `mu_iot_metrics.json`):

| Class | test_within | test_heldout |
|---|---|---|
| DDoS | 0.980 | 0.446 |
| Injection | 0.978 | 0.918 |
| MiTM | 0.963 | — |
| Password_Hacking | 0.990 | 0.804 |
| Scan | 0.994 | 0.420 |
| Spyware | 0.747 | — |
| normal | 0.909 | — |

"—" means the class has no held-out recording.

---

## 5. Known Limitations (state these plainly)

- **Unfamiliar attack variants get the wrong attack name.** On held-out
  recordings, attacks similar to something in training score well
  (dictionary attack 0.998 recall, XSS 0.882). New variants do not: an hping3
  UDP flood is called Scan in 68% of its windows, and a vulnerability scan is
  called Password_Hacking in 41% of its windows (confusion matrix in
  `mu_iot_test_heldout_results.txt`). These are still flagged as attacks,
  but the named type, and so the recommended action, can be wrong.
- **Normal vs Spyware is the main false-alarm source.** Most of the 9.3%
  false alarms are normal traffic called Spyware. Quiet keylogger
  exfiltration looks like ordinary background traffic (Spyware F1 0.747).
  A Spyware alert on its own should be treated as a lead for review.
- **Single-recording classes.** Normal and Spyware each come from one
  recording, so their test scores come from the same recording as their
  training data and are optimistic. MiTM has only 3,954 test windows.
- **Rare feature values.** Several features are almost always one value in
  training (for example RTSP_MM, the RTSP_* length fields, BJitter, ECE_FC,
  URG_FC). A rare non-default value becomes an extreme scaled input: RTSP
  method `SETUP` scales to about 207, where typical inputs are within ±3.
  Predictions on such flows are less trustworthy.
- **Dataset properties (for the report).** Two MU-IoT files are the same
  Slowloris capture with different timestamps. The DNS amplification
  recording is too small to learn (618 test windows, 0% correct). Flow
  timestamps were removed as inputs because each file is one class with its
  own time range, so timestamps would reveal the answer.

---

## 6. Speed on CPU

From `model/results/inference_benchmark.txt` (Ryzen 3 5300U laptop, plugged
in; `python model/benchmark_inference.py` reproduces it):

| Measurement | Value |
|---|---|
| Load time | 0.18 s |
| One window with `model.predict_on_batch` | 1.60 ms median (p99 2.42 ms) |
| One window with `model.predict` | 66 ms median |
| Batches of 2048 windows | ~21,900 windows/s |

- **Use `predict_on_batch` for one window at a time.** `model.predict()`
  adds a fixed ~65 ms of Keras overhead to every call, whatever the input
  size; both give the same class.
- The model computes in mixed precision (float16), as trained. A float32
  copy measured ~1.6x faster in batches but disagreed on 13 of 16,384 test
  windows, so it would no longer be exactly the evaluated model. The
  evaluated file is kept; its speed is well within what the dashboard needs.

---

## 7. Prevention Policy

`model/class_action_mapping.py` holds one policy per dataset. For MU-IoT
predictions, **always pass `dataset="mu_iot"`**:

```python
from class_action_mapping import get_action
prevention = get_action(result["predicted_class"], result["confidence"], dataset="mu_iot")
```

Without it, `get_action()` uses the CICIDS2017 policy, and `DDoS` exists in
both datasets: an MU-IoT `DDoS` prediction would get the CICIDS2017
threshold (0.55 instead of 0.84). An unknown `dataset` value raises
`ValueError` instead of guessing.

| Class | Action | Severity | Auto-acts at confidence ≥ | Evidence |
|---|---|---|---|---|
| normal | no_action | low | never acts | — |
| Injection | block_ip | high | 0.63 | held-out F1 0.918 |
| Password_Hacking | block_ip | high | 0.71 | held-out F1 0.804 |
| DDoS | block_ip | critical | 0.84 | held-out F1 0.446 |
| Scan | block_ip | medium | 0.84 | held-out F1 0.420 |
| MiTM | isolate_host | high | never (always review) | no held-out recording |
| Spyware | isolate_host | high | never (always review) | no held-out recording; main false-alarm source |

How the thresholds were set:

- **Same rule as CICIDS2017.** Each threshold is the CICIDS2017 F1 → threshold
  curve evaluated at the class's F1 (less reliable class, higher threshold).
- **Held-out F1, not within-recording F1.** Scores on recordings seen in
  training overstated every class that could be checked (Scan 0.994 → 0.420
  on an unseen recording), so only held-out scores are used.
- **No held-out evidence, no automatic action.** MiTM and Spyware have no
  held-out recording, so they always go to review. Spyware also absorbs most
  false alarms (6.2% of normal test windows are predicted as Spyware).
- All automatic MU-IoT actions are `block_ip`, which the execution engine
  (`prevention_executor.py`) performs for real within its safety limits.

The thresholds come from test-set F1, as the CICIDS2017 ones do: there is no
separate calibration set for behaviour on unseen recordings. What the policy
actually does on the test windows is measured by
`model/evaluate_prevention_policy.py --dataset mu_iot` (run in Colab, where the
data is).

---

## 8. Loading and Running Inference

```python
import json
import pickle

import numpy as np
from tensorflow import keras

ART = "model/artifacts/mu_iot/"
SEQ_LEN = 20

# RTSP method name -> code, exactly as in src/12_mu_iot_preprocess.py
RTSP_MAPPING = {"GET_PARAMETER": 0, "SETUP": 1, "OPTIONS": 2,
                "TEARDOWN": 3, "DESCRIBE": 4, "PLAY": 5}

# --- Load once at startup ---
model = keras.models.load_model(ART + "best.keras", compile=False)
with open(ART + "scaler_38.pkl", "rb") as f:
    scaler = pickle.load(f)
with open(ART + "feature_list_38.json") as f:
    FEATURES = json.load(f)
with open(ART + "label_mapping.json") as f:
    int_to_label = {v: k for k, v in json.load(f).items()}  # softmax index -> class


def encode_rtsp_method(value):
    """RTSP_MM holds a method name in the raw CSVs and a code in the cleaned file."""
    if isinstance(value, str):
        return RTSP_MAPPING.get(value, -1)
    value = float(value)
    return -1.0 if np.isnan(value) else value


def row_to_features(row):
    """One flow record (dict keyed by MU-IoT column name) -> 38 numbers in model order."""
    return [encode_rtsp_method(row[c]) if c == "RTSP_MM" else float(row[c]) for c in FEATURES]


def predict(flow_rows):
    """
    flow_rows: 20 consecutive flow records from one capture file, oldest first.
    Returns the predicted class, its confidence, and all 7 probabilities.
    """
    if len(flow_rows) != SEQ_LEN:
        raise ValueError(f"Expected {SEQ_LEN} flow rows for one window, got {len(flow_rows)}")

    X_raw = np.array([row_to_features(r) for r in flow_rows], dtype=np.float64)
    if not np.isfinite(X_raw).all():
        raise ValueError("Window contains a missing or infinite value; the model never saw one in training")

    X = scaler.transform(X_raw).astype(np.float32)[np.newaxis]  # (1, 20, 38)
    probs = model.predict_on_batch(X)[0]                        # (7,)
    pred_idx = int(np.argmax(probs))

    return {
        "predicted_class": int_to_label[pred_idx],
        "confidence": float(probs[pred_idx]),
        "probabilities": {int_to_label[i]: float(p) for i, p in enumerate(probs)},
    }
```

For many windows at once (a CSV upload), stack them into one
`(n, 20, 38)` array and call `model.predict(X, batch_size=2048)` instead.
