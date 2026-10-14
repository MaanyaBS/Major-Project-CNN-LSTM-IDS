# Project Status — IDS → IPS-lite, Current State (2026-10-02)

Supersedes the August version of this file. If you are an assistant helping
on this project with no other context, read this file fully before touching
integration code, then the interface documents it points to.

---

## 1. What This Project Is

A CNN-LSTM intrusion detection system that reads short sequences of network
flows, explains its decisions with SHAP, and acts on them through a cautious
prevention layer. It is evaluated on two datasets: **CICIDS2017** (benchmark,
15 classes) and **MU-IoT** (real IoT traffic from Manipur University,
7 classes). Prevention is **IPS-lite**: real Windows Firewall rules, but only
for RFC 5737 TEST-NET addresses and only when a kill switch is turned on; it
is a controlled demonstration, not a production IPS.

Team: Maanya B S — data; Ruthwik Sai Ganesh — model, evaluation, prevention;
Varshini D N — dashboard and backend.

---

## 2. Where Each Area Stands

| Area | State | Branch |
|---|---|---|
| CICIDS2017 data pipeline (cleaning, 20 features, day tags) | Done | `main` |
| MU-IoT data package (3.94M rows, 38 features, held-out recordings) | Done | Drive `Major_Project/handoff_v3` |
| CICIDS2017 CNN-LSTM, evaluation, baselines | Done | `person-b-model` |
| MU-IoT CNN-LSTM, evaluation, SHAP, baseline | Done | `person-b-model` |
| Prevention policy (both datasets) and execution engine | Done, 31 tests | `person-b-model` |
| Flask API: predict, CSV upload, SHAP, stream replay | Done | `varshini-dashboard` |
| React dashboard | Done | `varshini-dashboard` |
| Backend wiring of real prevention (`execute_action`) | **Not done** (handed off 2026-09-02) | — |
| Merge to `main` | **Not done**: `main` has no work since August | — |

---

## 3. Results

### CICIDS2017 (`model/MODEL_INTERFACE.md`)

Chronological day-and-class split; 530,951 test windows of 10 flows.

| Model, same test examples | Accuracy | Weighted F1 | Macro F1 |
|---|---|---|---|
| CNN-LSTM (10-flow windows) | 0.9842 | 0.9864 | 0.5857 |
| Random forest (single flows) | 0.9911 | 0.9908 | 0.7803 |

- **On CICIDS2017 the single-flow random forest is better.** The CNN-LSTM
  wins clearly only on DoS Hulk.
- Bot fails for both models (feature or data limit). The web attacks (brute
  force, XSS, SQL injection) fail only for the CNN-LSTM, so that weakness is
  the model's or its windowing's, not the features'.
- The older full-dataset baselines used a random split and are not comparable.

### MU-IoT (`model/results/mu_iot/FINDINGS.md`)

20-flow windows, timestamps removed; four whole recordings held out. Scores
on windows whose exact sequence never appears in training:

| Model, same test examples | Within macro F1 | Held-out macro F1 | Normal flagged as attack |
|---|---|---|---|
| CNN-LSTM (20-flow windows) | 0.936 | 0.676 | 9.3% |
| Random forest (single rows) | 0.816 | 0.404 | 17.2% |

- **On MU-IoT the CNN-LSTM is clearly better**: single MU-IoT rows repeat
  under different labels, which only sequences resolve.
- It almost never misses an attack on unseen recordings (0.08% called normal);
  its held-out errors are about naming the attack.
- SHAP finds three different error causes: normal traffic genuinely resembling
  Spyware, the hping3 flood resembling scans, and the vulnerability scan
  carrying TCP window values outside the training range.

---

## 4. Prevention Layer

- **Policy** (`model/class_action_mapping.py`): per class an action, severity
  and confidence threshold, set inversely to F1. One policy per dataset:
  `get_action(cls, conf)` is CICIDS2017; MU-IoT needs `dataset="mu_iot"`
  (both datasets have a `DDoS` class with different thresholds).
- **Locked to human review:** CICIDS2017 Sql Injection, Heartbleed,
  Infiltration (too little data), Bot, Brute Force, XSS (F1 < 0.15); MU-IoT
  MiTM and Spyware (no held-out evidence).
- **Engine** (`model/prevention_executor.py`, `PREVENTION_EXECUTION_INTERFACE.md`):
  kill switch, TEST-NET allow-list, deny-list, admin check, auto-expiry,
  startup sweep, JSONL log.
- **Measured on every test window** (`evaluate_prevention_policy.py`):

| | Benign windows auto-actioned | Attacks handled automatically | Attacks missed |
|---|---|---|---|
| CICIDS2017 | 0.33% | 96.6% | 2.4% |
| MU-IoT, held-out recordings | no normal traffic | 94.4% | 0.08% |
| MU-IoT, within recordings | 1.6% (mostly via Injection) | 94.1% | 1.5% |

Thresholds come from test-set F1; there is no separate calibration set.

---

## 5. What the Dashboard Still Needs (in priority order)

1. **Wire real prevention**: `PREVENTION_EXECUTION_INTERFACE.md` Section 6
   (`sweep_expired_rules()` at startup, `execute_action()` on `auto_action`,
   an env-var kill switch).
2. **Sync `model/class_action_mapping.py`** from `person-b-model`: the
   dashboard branch has the August version (no Bot/Brute Force/XSS lock, no
   `dataset` argument).
3. **Single-window speed**: in `backend/model_service.py`, call
   `model.predict_on_batch()` for one window instead of `model.predict()`;
   it cuts about 67 ms to about 1.5 ms per call (same predictions,
   `model/results/inference_benchmark.txt`).
4. **SHAP background**: use real training windows instead of random N(0,1)
   sequences.
5. **Only if MU-IoT is shown**: follow `model/MU_IOT_MODEL_INTERFACE.md`
   (RTSP_MM encoding, 20-row windows, `dataset="mu_iot"`).

---

## 6. Open Team Decisions

1. **Project title**: it promises "IoT-based Data Collection and Cloud
   Deployment"; neither is built. Change the title or explain the scope.
2. **Merge to `main`**: `person-b-model` and `varshini-dashboard` both carry
   work `main` lacks.
3. **Whether the dashboard shows the MU-IoT model** or only CICIDS2017.
4. **Windowing in the report**: the backend cuts uploads into non-overlapping
   10-row blocks; evaluation used sliding windows. Both are valid; the report
   should say which the demo uses.

---

## 7. Where Things Are

| What | Where |
|---|---|
| CICIDS2017 model, scaler, labels | `model/artifacts/` · `model/MODEL_INTERFACE.md` |
| MU-IoT model, scaler, features, labels | `model/artifacts/mu_iot/` · `model/MU_IOT_MODEL_INTERFACE.md` |
| CICIDS2017 results | `model/results/cnn_lstm_v2_full_test_results.txt`, `chronological_random_forest_results.txt` |
| MU-IoT results and analysis | `model/results/mu_iot/` (start with `FINDINGS.md`) |
| Prevention policy outcomes | `model/results/prevention_policy_cicids2017.txt`, `mu_iot/prevention_policy_mu_iot.txt` |
| Speed | `model/results/inference_benchmark.txt` |
| Tests | `python model/test_prevention.py` (31), `python model/test_mu_iot_windows.py` (8) |

---

## 8. Integration Gotchas

- The MU-IoT scaler was saved with scikit-learn 1.9.0; older versions warn
  on load but transform identically (checked on 1.6.1).
- Load the MU-IoT model with `keras.models.load_model(path, compile=False)`;
  it computes in mixed precision, as trained.
- Resolve artifact paths from the repository root, not the working directory.
- `MODEL_INTERFACE.md`'s `predict()` assumes rows arrive as dicts keyed by
  the 20 feature names; confirm the dashboard's data format matches.
