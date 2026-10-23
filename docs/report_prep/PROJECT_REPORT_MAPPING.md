# Project-to-Report Mapping

Maps every report section (see `REPORT_OUTLINE.md`) to the project's actual
evidence. Paths refer to the `main` branch (tag `v2-live`, commit `0ee880d`)
unless stated. Task IDs refer to `REPORT_MASTER_CHECKLIST.md`; question IDs
(`Q…`) to `MISSING_INFORMATION_QUESTIONNAIRE.md`.

**Inspection limitations.** The template ZIP was not available; the
specification in `REPORT_TEMPLATE_SPECIFICATION.md` was used instead. Large
data files (`dataset/`, captures, MU-IoT arrays) are not in Git; their
statistics are taken from committed reports and outputs. Backend API/stream/
smoke test outputs are reported by the dashboard teammate but not committed.
Screenshots of the running system exist only outside the repository.

---

## Part A — What the project actually implements

| # | Feature / component | Status | Evidence (path) | What it demonstrates |
|---|---|---|---|---|
| 1 | CICIDS2017 cleaning (8 CSVs → 2,655,060 rows; missing/infinite, duplicates, constant columns removed) | Implemented and verified | `docs/report/person_a_report.md` §2–3; `output/cleaning_report.csv`, `output/dataset_summary.csv` | Per-file cleaning statistics |
| 2 | Feature selection (top 20 by random-forest importance, 100,000-row sample) | Implemented and verified | `output/feature_importance.csv`, `output/selected_features.csv`; `person_a_report.md` §3 | Selected 20 features; known mild selection leak noted in `person_b_report.md` §10 |
| 3 | Chronological (day, class) split, 10-flow windows, train-only scaler | Implemented and verified | `model/rebuild_chronological_split.py`, `model/sequence_reshaping.py`; `person_b_report.md` §3.1 | 530,951 test windows |
| 4 | MU-IoT preparation (24,171,263 → 3,936,753 rows × 38 features; held-out recordings; blocks) | Implemented and verified | `scripts/build_mu_iot_handoff_v3.py`, `output/mu_iot/handoff_v3/*`, `config/mu_iot_feature_sets.json`; `person_a_report.md` §5–12 | Split manifest, class counts per split |
| 5 | CICIDS2017 CNN-LSTM (v2 deployed; 83,919 params) | Implemented and verified | `model/cnn_lstm_architecture.py`, `model/train_cnn_lstm.py`, `notebooks/v2_training_cells.txt`, `model/artifacts/cnn_lstm_best_v2.keras`; `model/results/cnn_lstm_v2_full_test_results.txt`, `cnn_lstm_versions_comparison.txt`, `cnn_lstm_v2_training_curves.png`, `cnn_lstm_v2_confusion_matrix.png` | Accuracy 0.9842, weighted F1 0.9864, macro F1 0.5857 |
| 6 | MU-IoT CNN-LSTM (20-flow windows; 86,855 params; mixed precision) | Implemented and verified | `model/train_cnn_lstm_mu_iot.py`, `model/test_mu_iot_windows.py` (8 tests), `model/artifacts/mu_iot/*`; `model/results/mu_iot/*` (`FINDINGS.md`, `mu_iot_unseen_only_rescore.txt`) | Within macro F1 0.936; held-out 0.676 |
| 7 | Baselines (random forest on identical examples; logistic regression; earlier full-dataset RF) | Implemented and verified | `model/baseline_chronological_rf.py`, `baseline_mu_iot_rf.py`, `baseline_logistic_regression.py`, `baseline_full_dataset.py`; matching files in `model/results/` | RF 0.9911 / 0.9908 / 0.7803 on CICIDS2017; 0.816 / 0.404 on MU-IoT |
| 8 | SHAP error analysis of the MU-IoT model (expected gradients) | Implemented and verified | `model/explain_mu_iot.py`; `model/results/mu_iot/mu_iot_shap_report.txt`, `mu_iot_shap_*.png` | Three error causes (cosine similarity table) |
| 9 | Dashboard SHAP (KernelExplainer, 20 grouped features, real-traffic background) | Implemented and verified (by Person C, measured additivity ~1e-9) | `backend/shap_service.py`, `backend/shap_background.npy`, `model/build_shap_background.py`; `docs/report/person_c_report.md` §1 | Per-window attributions in the UI |
| 10 | Prevention policy (per-class action, severity, F1-derived threshold; 6 review-locked classes) | Implemented and verified | `model/class_action_mapping.py`, `model/evaluate_prevention_policy.py`; `model/results/prevention_policy_cicids2017.txt`, `mu_iot/prevention_policy_mu_iot.txt` | 0.33% benign auto-actioned, 96.6% attacks handled (CICIDS2017) |
| 11 | Prevention execution engine (Windows Firewall via `netsh advfirewall`; kill switch; allow-list; one rule per device; expiry; sweep; revoke) | Implemented and verified | `model/prevention_executor.py`, `model/test_prevention.py` (35 tests), `model/live_check_prevention.py`; `model/results/prevention_live_check.txt` (22/22) | Real rules added/removed on Windows Firewall |
| 12 | Live target selection (LAN device that sent traffic to this host; never host/gateway) | Implemented and verified | `model/target_selection.py`, `model/test_target_selection.py` (8 tests) | Bystander refused in live run |
| 13 | Packet-to-flow extractor (CICFlowMeter-V3 rules; IPv4 + IPv6; raw-byte reader) | Implemented and verified | `model/flow_features.py`, `model/test_flow_features.py` (20 tests); `model/validate_against_cicids.py`, `model/test_validate_against_cicids.py` (3 tests); `model/results/extractor_validation.md` | 99.8% agreement with official CICIDS2017 rows; 49/49 PortScan |
| 14 | Live capture engine (Npcap; 3 threads; 1 prediction/s; executes prevention itself) | Implemented and verified | `backend/live_capture.py`, `backend/test_live_capture.py` (14 tests); `model/results/hotspot_live_results.md` | Live run: PortScan ~2 s after first probe, tablet blocked, revoke restores |
| 15 | Wireshark capture upload (`/api/predict_pcap`) | Implemented and verified | `backend/app.py` (`predict_pcap`, `analyze_frame`); teammate's pcap-vs-CSV equivalence check (reported); upload test on Capture2: 104/114 windows PortScan | Same results for capture and its flow CSV |
| 16 | Flask REST API | Implemented and verified | `backend/app.py` (routes: `/api/health`, `/api/meta`, `/api/predict`, `/api/explain`, `/api/predict_csv`, `/api/predict_pcap`, `/api/explain_window`, `/api/stream/load`, `/api/stream/next`, `/api/prevention/revoke`, `/api/prevention/active`, `/api/live/interfaces|start|poll|stop`); `backend/README.md` | Endpoint contract |
| 17 | ThreatLens AI dashboard (React 19 + TypeScript, TanStack Router/Start, Tailwind 4, Recharts) | Implemented and verified | `frontend/src/routes/index.tsx`, `dashboard.tsx`, `about.tsx`; `frontend/src/components/LiveFeed.tsx`; `frontend/src/lib/api.ts`; `frontend/package.json` | Batch Analysis (CSV/capture upload, threat timeline, class distribution, traffic composition, SHAP), Live Feed (Replay file / Live capture), Blocked devices + Revoke |
| 18 | CERT-In category mapping | Implemented and verified | `backend/cert_in_mapping.py`; `person_c_report.md` §3 | Category shown per class |
| 19 | Backend API / stream / smoke tests | Implemented but not verified by committed output | `backend/api_test.py`, `stream_test.py`, `smoke_test.py` (need a running server) | Teammate reports them passing; no committed log |
| 20 | Demo dataset for all 14 attack classes | Implemented and verified | `demo/demo_cicids_test.csv`, `demo/demo_cicids_test_expected.txt`, `model/build_demo_csv.py` | 220 rows / 22 windows of real test data |
| 21 | Inference speed benchmark | Implemented and verified | `model/benchmark_inference.py`; `model/results/inference_benchmark.txt` | 1.48 ms per window (`predict_on_batch`), Ryzen 3 5300U |
| 22 | `rate_limit` action | Partially implemented | `model/prevention_executor.py`; `model/PREVENTION_EXECUTION_INTERFACE.md` §3 | Implemented as a temporary full block, not bandwidth throttling |
| 23 | `sanitize_input` (XSS) / `terminate_session` | Partially implemented (recommendation only, by design) | same | Not executable at network level |
| 24 | MU-IoT model in the dashboard | Planned but not implemented (deferred pending team sign-off) | `person_c_report.md` §5 | Dashboard serves CICIDS2017 only |
| 25 | "IoT-based data collection" (registered title) | Not found | — | MU-IoT is an external dataset; no IoT sensor/collection hardware in the repo |
| 26 | "Cloud deployment" (registered title) | Not found | no Dockerfile / Procfile / deploy config | Runs locally (backend bound to 127.0.0.1) |
| 27 | "Indian network databases" (Review 2 title) | Not found | — | No Indian network dataset in the repo |
| 28 | Database / persistent storage | Not found (not used) | no DB code | State in memory + JSONL execution log `model/results/prevention_execution_log.jsonl` |
| 29 | Authentication / authorisation | Not found (not used) | no auth code | Safety via environment kill switch, address allow-list, admin rights; CORS open; backend on localhost |
| 30 | Deployment configuration | Not found | — | Local run instructions only (`backend/README.md`, `docs/LIVE_DEMO_CHECKLIST.md`) |

**Documentation inconsistencies found** (fix before writing): `README.md`
still describes prevention as "recommended/simulated responses" (real
execution now exists); project title appears in four variants (Q1).

---

## Part B — Section-by-section mapping

### Preliminary pages

| Field | Title sheet / Certificate / Declaration / Acknowledgement |
|---|---|
| Purpose | Identify the work, certify authorship, declare originality, thank contributors |
| Project-specific content | Title (Q1); students: Maanya B S 1JT23AI030, Ruthwik Sai Ganesh 1JT23AI042, Varshini D N 1JT23AI060 (from the team's Review 2 deck, 17 Sep 2026 — verify spelling, Q2); guide: "Dr. Madhu B R, Professor & Head, Department of AIML" (Review 2 deck) — confirm whether the guide and HOD are the same person (Q3); principal and coordinator names (Q4); academic year (Q5); degree name (Q6) |
| Evidence | Team's Review 2 deck (outside repo: `Downloads/Review_2_-_Presentation_on_Project_Phase-2 (1).pptx`); Review 4 deck (`PROJECTS/Report format AIML 8th sem/Phase 2 Review 4 - CNN-LSTM IDS Presentation.pptx`) |
| Repository path | none (institutional data is not in the repo) |
| Figures and tables | College logo (from the template) |
| Availability | Partially available; needs verification |
| Outstanding questions | Q1–Q7 |
| Next action | Get Q1–Q7 answered; fill placeholders; signatures at submission (A10) |

### Abstract

| Field | Content |
|---|---|
| Purpose | One-page summary: problem, objective, method, results, significance |
| Project-specific content | Problem (benchmark-only IDS, leakage, no live action); objective; method (CNN-LSTM on 10-flow windows, chronological split, RF baseline, SHAP, F1-derived prevention policy, Windows Firewall execution, live capture with validated extractor); results (CICIDS2017 0.984 acc / 0.586 macro F1 vs RF 0.780; MU-IoT held-out macro F1 0.676 vs 0.404; policy 96.6% / 0.33%; extractor 99.8%; live block ~2 s); significance |
| Evidence | `docs/report/ieee_paper_content.md` (abstract draft, on `person-b-model`); result files above |
| Repository path | `model/results/`, `docs/report/` |
| Figures and tables | none |
| Availability | Available |
| Outstanding questions | Q1 (title scope affects framing) |
| Next action | Adapt the paper abstract to one page, TNR 12, justified, 1.5 spacing (C01) |

### Chapter 1 — Introduction

| Field | Content |
|---|---|
| Purpose | Background, problem, motivation, scope, report organisation |
| Project-specific content | IDS background; problem statement (above); motivation incl. the guide's review requirements (live input, real captures) and the team's addition (live prevention); scope: IPS-lite, CICIDS2017 model in the dashboard, MU-IoT evaluated offline, one live attack type |
| Evidence | `README.md` overview; `docs/PROJECT_STATUS_CURRENT.md` §1; `ieee_paper_content.md` §I; Review 2 deck intro slides |
| Repository path | as listed |
| Figures and tables | optional overview figure (reuse Fig. 4.1) |
| Availability | Available |
| Outstanding questions | Q1 (title/scope), Q8 (does the guide want "Indian network" or "IoT data collection" claims addressed explicitly) |
| Next action | Draft from paper §I and status doc; state scope honestly (C02) |

### Chapter 2 — Literature Survey

| Field | Content |
|---|---|
| Purpose | Prior work and the gap addressed |
| Project-specific content | Currently cited: Sharafaldin 2018 (CICIDS2017), Lashkari 2017 (CICFlowMeter), Vinayakumar 2019 (DL-IDS), Engelen 2021 (CICIDS2017 artefacts), Lundberg & Lee 2017 (SHAP), Sommer & Paxson 2010, Arp et al. 2022, Hochreiter & Schmidhuber 1997 (LSTM), Breiman 2001 (RF); MU-IoT dataset citation missing |
| Evidence | `docs/report/ieee_paper_content.md` §II and References; Review 4 deck slide 4 |
| Repository path | `docs/report/ieee_paper_content.md` (person-b-model) |
| Figures and tables | Table 2.1 literature summary (author/year, method, dataset, result, limitation) |
| Availability | Partially available (9 verified-by-memory references; a typical survey needs more, and all need checking) |
| Outstanding questions | Q10 (expected number of surveyed papers), Q11 (papers the team already read in Phase 1), Q12 (MU-IoT citation) |
| Next action | Collect Phase-1 literature; verify each reference; build Table 2.1 (C04, C19, C20) |

### Chapter 3 — Objective and Methodology

| Field | 3.1 Objective / 3.2 Methodology |
|---|---|
| Purpose | What the project set out to do; how it was done |
| Project-specific content | Objectives (5, as in the Review 4 deck). Methodology: datasets and preprocessing (Person A: CICIDS2017 cleaning steps and per-file table; MU-IoT pipeline, Table-8 feature set 48→40→38, blocks, held-out sessions); evaluation design (chronological split rationale; unseen-only rescoring; RF on identical examples); CNN-LSTM (layers, optimiser, loss, class-weight comparison v1/v2/v3, early stopping); SHAP (dashboard KernelExplainer: nsamples 1000, 20 grouped features, background; MU-IoT expected gradients); prevention (policy + engine); live capture (extractor rules, live engine); backend/dashboard |
| Evidence | `docs/report/person_a_report.md`; `person_b_report.md` §2–7; `person_c_report.md` §1–3; `model/MODEL_INTERFACE.md`, `MU_IOT_MODEL_INTERFACE.md`, `PREVENTION_EXECUTION_INTERFACE.md` |
| Repository path | `docs/report/`, `model/` |
| Figures and tables | Fig. 3.1 methodology pipeline; Table 3.x dataset summary; Table 3.x cleaning statistics; Table 3.x 20 selected features; Table 3.x MU-IoT split counts; Table 3.x class-weight comparison |
| Availability | Available |
| Outstanding questions | none blocking |
| Next action | Write from the three person reports; create Fig. 3.1 (C05) |

### Chapter 4 — System Design

| Field | 4.1 System Architecture |
|---|---|
| Purpose | Components and their interactions |
| Project-specific content | Components: traffic sources (network interface via Npcap; Wireshark .pcap/.pcapng; flow CSV) → packet-to-flow extractor (`model/flow_features.py`) → live engine threads (capture → bounded queue → flow table → worker; `backend/live_capture.py`) → model service (scaler + CNN-LSTM, `backend/model_service.py`) → policy (`class_action_mapping.py`) → target selection → prevention runtime + executor → Windows Firewall (`netsh`); SHAP service; CERT-In mapping; Flask API (`backend/app.py`); React dashboard over HTTP/JSON (poll every 1 s); execution log (JSONL). Offline: training pipelines in Colab, artifacts in `model/artifacts/` |
| Evidence | source files listed; `docs/PROJECT_STATUS_CURRENT.md` §1, §7 |
| Figures and tables | Fig. 4.1 system architecture (must create) |
| Availability | Information available; diagram missing |
| Next action | Draw Fig. 4.1 (C06) |

| Field | 4.2 Use Case Diagram |
|---|---|
| Project-specific content | Actors: Security analyst/operator (dashboard user); Attacker device (external); Windows Firewall (system actor); Administrator (starts backend, sets kill switch and demo targets via environment). Use cases: upload flow CSV; upload Wireshark capture; replay file stream; start/stop live capture; view detections, confidence, CERT-In category; view SHAP explanation; view window flows; view blocked devices; revoke block; (system) auto-block attacker; (system) hold for review; configure execution (env vars) |
| Evidence | `frontend/src/routes/dashboard.tsx`, `LiveFeed.tsx`, `backend/app.py`, `docs/LIVE_DEMO_CHECKLIST.md` |
| Figures and tables | Fig. 4.2 (must create) |
| Availability | Information available; diagram missing |
| Next action | C07 |

| Field | 4.3 Data Flow Diagram |
|---|---|
| Project-specific content | Level 0: external entities Network, Analyst, Firewall; process "ThreatLens IDS/IPS"; flows: packets/captures in; detections, explanations out; block/revoke commands to firewall. Level 1: 1.0 Capture/parse packets → 2.0 Build flows & features → 3.0 Window & scale → 4.0 Classify (CNN-LSTM) → 5.0 Decide action (policy) → 6.0 Select target & execute → 7.0 Explain (SHAP) → 8.0 Present (API/UI); data stores: model artifacts (D1), execution log JSONL (D2), results buffer (D3, in memory) |
| Figures and tables | Fig. 4.3(a), 4.3(b) (must create) |
| Availability | Information available; diagrams missing |
| Next action | C08 |

| Field | 4.4 Sequence Diagram |
|---|---|
| Project-specific content | (a) Live: Attacker → NIC/Npcap → capture thread → queue → flow thread (FIN/RST/120 s) → worker (every 1 s: model → policy → target → `execute_for_result` → `netsh`) → results buffer ← dashboard poll `/api/live/poll`. (b) Upload: UI → `/api/predict_pcap` → `flows_from_pcap` → `analyze_frame` → model → policy → response. (c) Explain: UI → `/api/explain_window` → SHAP KernelExplainer → attributions. (d) Revoke: UI → `/api/prevention/revoke` → `revoke_action` → `netsh delete` → `/api/prevention/active` |
| Figures and tables | Fig. 4.4(a)–(d) (must create) |
| Availability | Information available; diagrams missing |
| Next action | C09 |

| Field | 4.5 Algorithms Used |
|---|---|
| Project-specific content | Flow extraction rules (first packet counted twice in length stats; sample std; Ethernet padding; whole microseconds; FIN-first rule; 120 s timeout; live RST end); sliding windows; CNN-LSTM; RF baseline; SHAP KernelExplainer and expected gradients; prevention thresholds (inverse to F1) and locks; target selection; execution safety checks |
| Evidence | `model/flow_features.py` docstring; `person_b_report.md` §2, §6–8; `person_c_report.md` §1; `model/target_selection.py`; `model/prevention_executor.py` |
| Figures and tables | Algorithm boxes/pseudo-code; Table 4.x CNN-LSTM layers; Table 4.x prevention policy per class; equations (C21) |
| Availability | Available |
| Next action | Write pseudo-code and equations (C10, C21) |

### Chapter 5 — Hardware and Software Requirement

| Field | Content |
|---|---|
| Project-specific content | **Hardware (measured):** IDS/demo laptop AMD Ryzen 3 5300U (8 logical cores), 7.3 GB RAM, Windows 11 Home, Wi-Fi adapter Realtek RTL8822CE; attacker device: Android tablet (Termux, nmap 7.991 as printed in the live run); network: phone hotspot / Wi-Fi router; training: Google Colab GPU (T4 recorded for MU-IoT; CICIDS2017 v2 GPU type not recorded, Q13). **Software:** Python 3.13.2; TensorFlow 2.21.0 / Keras 3.15.0; scikit-learn 1.6.1; pandas; NumPy; scapy 2.8.0; SHAP 0.52.0; Flask 3.x, Flask-CORS; Npcap; Wireshark; Node.js (v24.22.1 measured) with npm; React 19, TypeScript 5.8, Vite 8, TanStack Router/Start, Tailwind CSS 4, Recharts 2; Google Colab; Git/GitHub; nmap (Termux) |
| Evidence | `model/results/inference_benchmark.txt`; `backend/requirements.txt`; `frontend/package.json`; `model/results/hotspot_live_results.md`; `docs/LIVE_DEMO_CHECKLIST.md` |
| Figures and tables | Table 5.1 hardware; Table 5.2 software (with versions) |
| Availability | Mostly available |
| Outstanding questions | Q13 (Colab GPU for CICIDS2017; teammates' machines if they should be listed); minimum vs used requirements (Q14) |
| Next action | C11, C12 |

### [VERIFY] Chapter 6 — Implementation, Testing and Results

| Field | Content |
|---|---|
| Project-specific content | Implementation screenshots; tests (prevention 35, live engine 14, extractor 20, validator 3, target selection 8, MU-IoT windows 8; real-firewall live check 22/22; mutation check); results tables (CICIDS2017 overall + per-class; MU-IoT within/held-out + per-recording; SHAP error-cause table; prevention outcomes; extractor validation; hotspot captures; live run timeline; inference speed); limitations |
| Evidence | `model/results/*`; `docs/report/person_b_report.md` §5–10; `model/results/hotspot_live_results.md`; `model/results/extractor_validation.md` |
| Figures and tables | existing PNGs (training curves, confusion matrix, SHAP plots); screenshots to capture (C15) |
| Availability | Results available; screenshots missing from repo; backend test outputs not committed |
| Outstanding questions | Q9 (chapter allowed?), Q15 (screenshots/recording), Q16 (backend test logs) |
| Next action | C13–C15 |

### Conclusion

| Field | Content |
|---|---|
| Project-specific content | What was achieved (with numbers), where the CNN-LSTM helps vs not, live detection and blocking, safety; future enhancements |
| Evidence | `ieee_paper_content.md` §IX; `person_b_report.md` §10 |
| Availability | Available |
| Next action | C16 |

### References

| Field | Content |
|---|---|
| Project-specific content | 10 entries in the paper draft; MU-IoT citation missing; datasets/tools (CICIDS2017, Npcap, scapy, TensorFlow, SHAP, Flask, React) may be cited if the style allows |
| Availability | Partially available; all need verification |
| Outstanding questions | Q10–Q12, Q17 (citation style) |
| Next action | C19, C20 |
