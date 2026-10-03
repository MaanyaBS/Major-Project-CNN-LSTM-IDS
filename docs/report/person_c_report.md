# Varshini D N — Explainability & Dashboard

## 1. SHAP Explainability Implementation

### Method

We use **SHAP KernelExplainer** (Lundberg & Lee, 2017) to generate local, per-window
feature attributions for each CNN-LSTM prediction. The explainer is an exact Shapley
value computation (model-agnostic linear-sampling hybrid) run with `nsamples=100` on a
flattened representation of each window.

We originally specified **GradientExplainer**, and measured it against KernelExplainer on
the actual CNN-LSTM v2 model before switching. GradientExplainer did not hold up on three
counts that matter for a dashboard explanation:

| Property | GradientExplainer | KernelExplainer (shipped) |
|---|---|---|
| Additivity error (`base + Σϕ` vs model output) | ~1.3 × 10⁻¹ (e.g. sum 0.903 vs required 0.988 — a 9% shortfall) | ~1 × 10⁻⁹ (measured max 7.23 × 10⁻⁹) |
| Determinism | Unstable — same input returned 0.693 / 0.903 / 1.043 on repeated runs | Deterministic (seeded) |
| Latency per window | 1–16 s | 137–200 ms |

Additivity is the property that makes an explanation trustworthy: if the attributions do
not sum to the prediction they are explaining, they cannot be read as "these are the
reasons". GradientExplainer's ~1e-1 error was too large to display as a waterfall without
misleading the viewer. KernelExplainer's error is at floating-point noise level.

A further practical note: in `shap` 0.52 the `GradientExplainer` object exposes no
`expected_value` attribute, so the base value cannot be reported to the frontend at all —
which is precisely the number needed to display the additive decomposition.

KernelExplainer is normally considered too slow for recurrent models, but that concern
applies to explaining large batches. We explain **one window at a time, on demand**, so
the 100-sample cost is acceptable at ~137 ms.

### Background Distribution

The explainer is initialised from **100 real windows sampled from the actual training
tensor** (`X_train_seq.npy`), a few per class, produced by
`model/build_shap_background.py` and stored as `backend/shap_background.npy` (~78 KB).
Using real training windows instead of a synthetic surrogate is what item 4 of the
integration asked for, and it makes the `base value` in the additive decomposition
meaningful: it is the model's average output over real traffic rather than over an assumed
Gaussian.

> **Outstanding:** the sampler script and the service that consumes it are complete and
> tested, but `X_train_seq.npy` is not present in this working copy (`datasets/` is
> gitignored), so `backend/shap_background.npy` has not been generated yet. The service is
> therefore currently running in `synthetic_fallback` mode. Generate it with
> `python model/build_shap_background.py` on a machine that has the training arrays, then
> commit the resulting ~78 KB file. Until that happens, treat the shipped attributions as
> indicative — the code path is correct, the data is missing.

Sampling is deliberately class-balanced rather than proportional, so that rare attack
classes (Heartbleed: 3 rows; Bot; Web Attack variants) are represented in the
explanation baseline. A proportional sample would be ~97% BENIGN and the attributions would
be dominated by normal traffic. Classes with zero support (Infiltration) are absent, since
there is nothing to sample.

If `backend/shap_background.npy` is absent, the service falls back to a 32-sequence
synthetic N(0,1) background so the dashboard still works, and reports this honestly:
`GET /api/health` → `shap_background.source` returns `real_training_windows` or
`synthetic_fallback`, and the frontend surfaces it as a banner. The dashboard should never
silently show approximate explanations as if they were exact.

### Attribution Pipeline (`backend/shap_service.py`)

1. Raw input rows are scaled using `scaler_v2.pkl` (row-wise, per `MODEL_INTERFACE.md`).
2. The window `(10, 20)` is **flattened to 200 columns** before being handed to SHAP. This
   is required, not cosmetic: a `(n, 10, 20)` array is interpreted by SHAP as an *image*
   stack, and the tabular masker rejects it. The model itself still receives the proper
   `(1, 10, 20)` tensor through an internal wrapper, so predictions are unaffected.
3. KernelExplainer is queried with `nsamples=100` under `np.random.seed(0)`; KernelExplainer
   draws from the global NumPy RNG, and without the seed the unseeded spread was 0.17 —
   large enough to change the displayed ranking between two clicks.
4. The raw SHAP output is sliced to the predicted class dimension.
5. Per-feature attributions are obtained by **summing** across the 10 timesteps, not
   averaging. Summation is required for the additivity check to hold:
   `base_value + Σϕ == f(x)`. An average silently divides the explanation by 10 and breaks
   that identity.
6. Attributions are ranked by `|shap_value|` and returned with the raw feature means —
   enough data to render diverging bar charts or waterfall plots in the frontend.

`/api/explain` returns a `local_accuracy` block (`base_value`, `sum_all_attributions`,
`model_output`, `reconstructed`, `abs_error`) so the additive property is checkable from the
UI and from tests rather than taken on trust.

### Dashboard Integration

The frontend (`dashboard.tsx`) displays SHAP attributions as:
- A **diverging bar chart** (positive = pushes toward predicted class, negative = pushes
  away) with a Recharts `<BarChart>`.
- A **waterfall-style summary** listing the top contributing features with their raw and
  SHAP values.
- The explanation is triggered on window selection (from batch analysis) or on demand for
  any single prediction.

### Known Limitations

- The exactness of the attribution now depends entirely on the background being real.
  While `shap_background.npy` is missing, the service is in `synthetic_fallback` mode and
  attributions must be treated as indicative. `/api/health` reports which mode is active.
- Attribution cost is ~137 ms per window, so explaining every window in a 2000-window
  batch is not practical on demand; the UI explains the selected window only.
- Timestep-specific contribution patterns are not surfaced. Summing across the 10
  timesteps is required for additivity, but it means a feature that spikes on one
  timestep and is flat on the other nine is displayed with the same weight as a feature
  that is consistently elevated. Separating the two would require a 3D attribution
  display, which is out of scope for the current UI.

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
| `POST /api/prevention/revoke` | Remove a demo firewall rule created by the execution engine |

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

### Windowing: Demo vs Training (read this before comparing counts)

The dashboard and the training/evaluation pipeline do **not** window identically, and the
difference changes every count you see on screen. This is the single most common source of
confusion when comparing a dashboard number against a reported metric.

| | Training & evaluation | Dashboard demo (CSV upload / live feed) |
|---|---|---|
| Window type | Overlapping sliding window | Non-overlapping contiguous blocks |
| Stride | 1 row | 10 rows (the full window length) |
| Windows produced | ~1 per flow | 1 per 10 flows |
| Predictions over N rows | ≈ N | ≈ N / 10 |

So on a 10,000-row file the dashboard issues ~1,000 predictions, while a training-shaped
run over the same flows would issue ~10,000. The demo is a **display decision made to keep
the UI legible** — one prediction per 10 flows maps to one readable card in the live feed
and one entry in the detection log. It is not a modelling change, and it does not affect
per-window accuracy.

Practical consequences to keep in mind when reading the dashboard:

- A single attack burst spanning 30 rows produces **3** demo predictions, versus ~30 under
  sliding-window inference. The dashboard therefore under-reports the *number of windows*
  an attack occupies.
- Aggregate attack *rate* (percentage of windows flagged) is comparable between the two
  schemes only when the attack occupies many windows; short, sparse attacks are sampled
  more coarsely by the demo.
- Any figure quoted as "accuracy" must come from the evaluation pipeline, never from the
  dashboard's aggregate stats. The dashboard reports what the model did on a given file;
  it does not measure correctness.

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

### Recommended ≠ Executed

The dashboard keeps two distinct states and must never conflate them:

- **Recommended** — the policy engine's output. Always present when `status == auto_action`.
- **Executed** — whether a real firewall rule was actually created on the host.

These are separate because execution is gated by a kill switch
(`IDS_PREVENTION_EXECUTION_ENABLED`) and by a safety check in the engine, so a prediction
can recommend `block_ip` with no rule being created. The stat cards are split into "Actions
Recommended" and "Actually Executed" for this reason.

Execution is **off by default** and is enabled only by deliberately setting the environment
variable (`1`/`true`/`yes`/`on`). There is deliberately no HTTP endpoint that can turn it on:
an inbound request must never be able to authorise itself to modify the host's firewall.
`/api/health` → `prevention_execution` reports the current mode, and the frontend shows a
banner so the demo state is always visible.

On `status == auto_action` with a parsed Source IP, the backend calls
`prevention_executor.execute_action(action, source_ip, predicted_class, confidence)` and
returns the result under `"execution"`. The engine enforces its own safety boundary
independently of the backend — routable, public addresses such as `8.8.8.8` are always
refused — and every call, including refusals, is appended to
`model/results/prevention_execution_log.jsonl`.

---

## 4. Known Limitations

1. **SHAP background depends on a generated artefact** — `backend/shap_background.npy`
   is sampled from `X_train_seq.npy` by `model/build_shap_background.py`. Until that file
   is generated and committed, the service reports `synthetic_fallback` and the
   attributions are indicative rather than exact. `/api/health` states which mode is live;
   the frontend shows a banner.

2. **Macro F1 is 0.586** — the model has strong accuracy (98.4%) and weighted F1
   (0.986) but performs poorly on 4-5 rare classes. This is a data-level limitation
   (flow-level features cannot distinguish these attack types), not a training bug.
   Accuracy alone should not be quoted as "the" number for this reason.

3. **Prevention thresholds are calibrated against per-class F1, not end-to-end cost** —
   the `CLASS_ACTION_MAP` thresholds were recalibrated against the CNN-LSTM v2 per-class F1
   scores (replacing the earlier Random Forest calibration, which no longer matched the
   deployed model). They are still not tuned against the real cost of an action — a false
   block and a missed block are weighted equally here, which they are not in production.

4. **Demo windowing is coarser than training windowing** — see §2. The dashboard uses
   non-overlapping 10-row blocks (one prediction per 10 flows) where training used
   overlapping sliding windows (one per flow). Per-window accuracy is unaffected, but any
   count of "windows" is not comparable between the two schemes.

5. **No live feature extraction** — the system assumes the input CSV already contains
   the 20 CICFlowMeter features. In a real deployment, a feature extraction pipeline
   (CICFlowMeter or equivalent) would be needed upstream.

6. **Stream replay is not real-time** — the live feed replays a static CSV with a
   configurable delay. True real-time inference would require packet capture → flow
   extraction → windowing → inference, which is out of scope.

7. **Sequence gap handling** — MODEL_INTERFACE.md §6 notes that training never let a
   10-row window span two capture days. CSV inference treats the file as one continuous
   stream with no gap detection. This is documented as a known limitation.

8. **Two countermeasure actions are advisory only** — `rate_limit` is implemented as a
   temporary full block (the OS has no portable QoS primitive that matches the name), and
   `sanitize_input` is recommendation-only with no executor. Both are deliberate, but the
   UI must not present them as enforced policy.
