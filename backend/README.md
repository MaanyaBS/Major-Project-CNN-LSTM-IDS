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

### `POST /api/predict_pcap`
Multipart form with a `file` field containing a Wireshark **`.pcap` or
`.pcapng`** capture. The capture is converted to bidirectional flows and the
20 CICIDS2017 feature columns with `model/flow_features.py` (needs
`scapy>=2.6`), then analysed by the *same* code path as `/api/predict_csv`
(`analyze_frame()`), so the response is identical plus `"flows"`: how many
flows the capture became.

Equivalence check:

```bash
python model/flow_features.py capture.pcap -o x.csv
# uploading x.csv and uploading capture.pcap give identical results
```

The body is streamed to a temp file in chunks and the temp file is always
deleted. A capture over the size limit is refused with HTTP 413 while it is
being read. The limit defaults to **200 MB** and is configurable:

```powershell
$env:IDS_MAX_PCAP_MB = "500"
```

An upload is rejected with HTTP 400 if no IPv4 TCP/UDP flows are found (an
empty or non-IP capture cannot be analysed).

### Live capture (Person B's `backend/live_capture.py`)
The UI polls these; until the capture engine lands, a stub in `app.py` answers
with deterministic demo data and the responses carry `"stub": true`.

| Endpoint | Body / query | Returns |
| --- | --- | --- |
| `GET /api/live/interfaces` | – | `{ interfaces: [{name, description, ip}], stub }` |
| `POST /api/live/start` | `{ "interface": "Wi-Fi" }` | `{ running: true, interface }` |
| `GET /api/live/poll` | `?after=<last window>&limit=<≤50>` | `{ running, packets, flows, windows, results, skipped, queue_depth, dropped }` |
| `POST /api/live/stop` | – | `{ running: false }` |

`after` is exclusive and defaults to `-1` (nothing seen yet, so window 0 is
included). A poll returns at most 50 windows so a busy scan cannot freeze the
page, and `queue_depth` tells the page more are waiting. Each result is one
`/api/predict_csv` result plus `window`, `source_ip` and `time`; real-engine
results go through the same execution bookkeeping as a CSV upload. `stop()` is
also called on server shutdown.

> Live capture needs **Npcap** (installed with Wireshark) and the backend
> running **as administrator**.

### `GET /api/prevention/active`
Lists the firewall rules currently in force — the dashboard's "Blocked
devices" panel, refreshed on every live poll. Read-only, so it needs no kill
switch. Uses Person B's `pe.active_rules()` once it exists (`engine_ready:
true`); until then it reads the engine's own in-process registry so a rule
created by a real execution is still listed and revocable (`engine_ready:
false`).

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
