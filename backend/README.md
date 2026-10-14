# Backend — Flask API for CNN-LSTM IDS

Serves the trained CNN-LSTM v2 model (per `model/MODEL_INTERFACE.md`), SHAP
explanations, and the prevention policy to the frontend.

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

Server runs at `http://127.0.0.1:5000`.

## Endpoints

### `GET /api/health`
Model + SHAP load status and headline metrics.

### `GET /api/meta`
Feature columns (contract order), sequence length, dashboard categories,
label mapping, model metrics.

### `POST /api/predict`
Single sequence:
```json
{ "flows": [ { "Destination Port": 80, "...": 0 }, ... 10 rows ] }
```
Batch:
```json
{ "sequences": [ [ ...10 rows... ], [ ...10 rows... ] ] }
```
Returns per-sequence: predicted class, CERT-In category, confidence, full
15-class probability breakdown, prevention action/severity/status (from
`model/class_action_mapping.py`), and a `low_confidence_class` flag for the
known-weak classes.

### `POST /api/explain`
Body: `{ "flows": [...10 rows...] }`.
Returns SHAP attributions for the predicted class: per-feature shap values,
raw feature means, base value — enough data to render summary bar / waterfall /
force-style plots in the frontend.

### `POST /api/predict_csv`
Multipart form with a `file` field containing a CSV that includes all 20
feature columns. Windows the rows into 10-step sequences (max 2000 windows),
returns summary stats, class counts, timeline buckets for charts, and the
first 200 per-window results.

An optional `Source IP` column (case-insensitive; `source_ip`, `src_ip`, `ip`
etc. also accepted) is used as the target for any prevention action. The value
is taken from the **first flow row of each window**. Blank / `null` / `n/a` /
non-IP values become `None`, and `None` targets are never executed.

### `POST /api/prevention/revoke`
Body: `{ "action": "block_ip", "target_ip": "192.0.2.50" }`.
Removes a demo firewall rule previously created by the execution engine and
returns the engine's own verdict. Deliberately **not** gated on the kill
switch — undoing must stay possible after a restart without the env var — but
the engine re-checks scope (RFC 5737 TEST-NET only) and admin rights itself.
A refusal comes back as HTTP 400 with `{"revoked": false, "reason": ...}`.

## Prevention execution

Actions are **recommended by default and not executed**. Execution is off unless
`IDS_PREVENTION_EXECUTION_ENABLED` is deliberately set in the environment
before starting the server:

```bash
# Windows PowerShell — OFF (default)
$env:IDS_PREVENTION_EXECUTION_ENABLED = "0"

# Windows PowerShell — ON (requires an elevated shell; creates real firewall rules)
$env:IDS_PREVENTION_EXECUTION_ENABLED = "1"
```

Truthy values are `1`, `true`, `yes`, `on` (case-insensitive). Anything else,
including unset, means execution is off.

Design notes:

- There is intentionally **no HTTP endpoint that can enable execution**. An inbound
  request must never be able to authorise itself to modify the host firewall.
- Enabling this creates **real, host-level firewall rules** prefixed `IDS_DEMO_`.
  Only run it in a lab VM.
- The engine re-checks safety independently of the backend: public/routable
  addresses (e.g. `8.8.8.8`), loopback, and unspecified addresses are always
  refused, and rules created for the local lab range expire automatically.
  `sweep_expired_rules()` runs once at startup.
- Every call — including refusals — is appended to
  `model/results/prevention_execution_log.jsonl`.
- `GET /api/health` → `prevention_execution` reports the current mode so the
  dashboard can show it.

## SHAP background

`shap_background.npy` (~78 KB) holds 100 real windows sampled from
`X_train_seq.npy`. Generate it where the training data lives:

```bash
python model/build_shap_background.py
```

If the file is missing the service falls back to a 32-sequence synthetic
background and reports `synthetic_fallback` via `GET /api/health` →
`shap_background.source`. The file is intentionally **not** gitignored — it is
small enough to commit, and committing it keeps every clone honest about which
explanation mode it is running.

## Notes

- Scaling is applied row-wise with `scaler_v2.pkl` before windowing, exactly as
  the contract requires.
- CSV inference uses **non-overlapping 10-row blocks** (one prediction per 10
  flows). Training and evaluation used **overlapping sliding windows** (one per
  flow). Per-window accuracy is unaffected, but window counts are not directly
  comparable between the two schemes — see `docs/report/person_c_report.md` §2.
- Sequence gaps across capture sessions (MODEL_INTERFACE.md §6) are not yet
  handled; CSV inference treats the file as one continuous stream. Documented
  as a known limitation.
