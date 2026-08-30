# Varshini D N — Explainability & Dashboard

## 1. SHAP Explainability Implementation

### Method

We use **SHAP GradientExplainer** (Lundberg & Lee, 2017) to generate local, per-window
feature attributions for each CNN-LSTM prediction. GradientExplainer was chosen over
DeepExplainer because:

- It computes exact Shapley values when the model is differentiable (which the
  CNN-LSTM is), under the assumption that the background distribution is Gaussian — a
  reasonable approximation after StandardScaler normalization.
- DeepExplainer requires a TensorFlow background reference that matches the training
  distribution, and does not fall back gracefully when raw training data is unavailable.
- KernelExplainer is model-agnostic but prohibitively slow (~100x) for recurrent
  architectures, making it unsuitable for real-time or interactive use.

### Background Distribution

The explainer is initialized with 32 synthetic sequences drawn from N(0,1) — matching
the post-scaling feature distribution. This is a known approximation; when the original
training array (`train.npy`) is available, the background should be replaced with actual
training samples for tighter Shapley value estimates.

### Attribution Pipeline (`backend/shap_service.py`)

1. Raw input rows are scaled using `scaler_v2.pkl` (row-wise, per `MODEL_INTERFACE.md`).
2. The scaled 3D tensor `(1, 10, 20)` is fed through the model and the explainer.
3. The raw SHAP output tensor is sliced to the predicted class dimension.
4. Per-feature attributions are obtained by averaging across the 10 timesteps.
5. Attributions are ranked by `|shap_value|` and returned with the raw feature means —
   enough data to render diverging bar charts or waterfall plots in the frontend.

### Dashboard Integration

The frontend (`dashboard.tsx`) displays SHAP attributions as:
- A **diverging bar chart** (positive = pushes toward predicted class, negative = pushes
  away) with a Recharts `<BarChart>`.
- A **waterfall-style summary** listing the top contributing features with their raw and
  SHAP values.
- The explanation is triggered on window selection (from batch analysis) or on demand for
  any single prediction.

### Known Limitations

- SHAP values are approximate under the Gaussian background assumption; real background
  samples would improve fidelity.
- Attributions are averaged across the 10-step sequence window — timestep-specific
  contribution patterns are not surfaced (this would require 3D attribution display,
  which is out of scope for the current UI).

---

## 2. Dashboard & Backend Architecture

### Backend (`backend/app.py`)

A Flask API serving the trained model, SHAP explanations, prevention policy, and stream
replay. Key design decisions:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Model + SHAP load status, headline metrics |
| `GET /api/meta` | Feature columns (contract order), sequence length, dashboard categories, label mapping |
| `POST /api/predict` | Single or batch sequence prediction with prevention action |
| `POST /api/explain` | SHAP attributions for a single sequence |
| `POST /api/predict_csv` | CSV upload → windowed batch prediction (max 2000 windows) |
| `POST /api/explain_window` | SHAP explanation for a specific window index in the last CSV upload |
| `POST /api/stream/load` | Load a CSV for live-feed replay |
| `GET /api/stream/next` | Advance the stream cursor by one window, returning a prediction |

The backend follows the contract in `model/MODEL_INTERFACE.md` exactly:
- Feature columns are ordered as specified (20 CICFlowMeter features).
- Scaling is applied row-wise before windowing.
- Sequence length is fixed at 10.
- The CNN-LSTM v2 model (`cnn_lstm_best_v2.keras`) is loaded at startup with lazy
  initialization (SHAP explainer is created after the model is confirmed loaded).

### Frontend (`frontend/src/`)

Built with React + Vite + TanStack Router + Recharts. The dashboard provides two
analysis modes:

1. **Batch Analysis** — upload a CSV, get aggregate stats (attack rate, class
   distribution, CERT-In categories) and per-window results with SHAP explanations on
   demand.
2. **Live Feed Replay** — upload a CSV, replay predictions one window at a time with a
   configurable delay, showing a real-time-style detection log with a threat confidence
   bar chart and running counts.

### API Client (`frontend/src/lib/api.ts`)

TypeScript interfaces mirror the backend's JSON response shapes, ensuring compile-time
safety across the full request/response cycle.

---

## 3. CERT-In Mapping

### Rationale

CICIDS2017 defines 15 classes (including BENIGN), but displaying 15 separate categories
on a dashboard is noisy and not aligned with how CERT-In reports are structured. We map
the 15 CICIDS classes to 9 operational categories:

| CICIDS Classes | Dashboard Category |
|---|---|
| BENIGN | Normal |
| DDoS | DDoS |
| DoS GoldenEye, DoS Hulk, DoS Slowhttptest, DoS slowloris | DoS |
| PortScan | Port Scan |
| FTP-Patator, SSH-Patator, Web Attack - Brute Force | Brute Force |
| Web Attack - Sql Injection, Web Attack - XSS | Web Attack |
| Bot | Botnet |
| Heartbleed | Exploit |
| Infiltration | Infiltration |

### Low-Confidence Classes

Six classes are flagged as `low_confidence_class: true` in every prediction response:

- Bot, Web Attack - Brute Force, Web Attack - XSS, Web Attack - Sql Injection,
  Infiltration, Heartbleed

These classes have poor-to-zero recall in the CNN-LSTM v2 model (see `PROJECT_STATUS_CURRENT.md`). The dashboard displays a warning badge for these predictions, and the prevention layer holds them for manual review rather than auto-acting.

### Prevention Integration

Each prediction includes a structured prevention response from `model/class_action_mapping.py`:
- `status`: `auto_action`, `held_for_review`, or `no_action_needed`
- `action`: specific countermeasure (e.g., `block_ip`, `rate_limit`, `drop_connection`)
- `severity`: `critical`, `high`, `medium`, `low`

---

## 4. Known Limitations

1. **SHAP background is synthetic** — N(0,1) approximates the scaled training
   distribution but is not exact. Attributions should be treated as indicative, not
   precise.

2. **Macro F1 is 0.586** — the model has strong accuracy (98.4%) and weighted F1
   (0.986) but performs poorly on 4-5 rare classes. This is a data-level limitation
   (flow-level features cannot distinguish these attack types), not a training bug.

3. **Prevention thresholds are RF-calibrated** — the `CLASS_ACTION_MAP` thresholds
   were originally set against the Random Forest baseline's per-class F1 scores. They
   have not been recalibrated for the CNN-LSTM's different reliability profile. This
   means some CNN-LSTM predictions may be held for review unnecessarily (or auto-acted
   when they shouldn't be).

4. **No live feature extraction** — the system assumes the input CSV already contains
   the 20 CICFlowMeter features. In a real deployment, a feature extraction pipeline
   (CICFlowMeter or equivalent) would be needed upstream.

5. **Stream replay is not real-time** — the live feed replays a static CSV with a
   configurable delay. True real-time inference would require packet capture → flow
   extraction → windowing → inference, which is out of scope.

6. **Sequence gap handling** — MODEL_INTERFACE.md §6 notes that training never let a
   10-row window span two capture days. CSV inference treats the file as one continuous
   stream with no gap detection. This is documented as a known limitation.
