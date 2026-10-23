# Report Artefact Inventory — Figures, Diagrams, Screenshots, Tables

**Required** = named in the template's chapter structure. **Recommended** =
useful for this project, not mandated. Proposed numbers follow the template's
chapter-based convention (e.g. 4.1(a)); Chapter 6 items depend on Q9.
Action: **Create** (draw new), **Capture** (screenshot), **Reuse** (exists),
**Update**, **Verify**. Paths on `main` unless noted.

## 1. Diagrams required by the template (all must be created)

| No. | Proposed title | Section | Purpose | Evidence needed (all available) | Exists? | Action | Req. |
|---|---|---|---|---|---|---|---|
| Fig. 4.1 | System architecture of the hybrid CNN-LSTM IDS/IPS | 4.1 | Show components and interactions | Traffic sources (Npcap interface, Wireshark file, flow CSV); `model/flow_features.py`; `backend/live_capture.py` (capture thread → queue → flow table → worker); `backend/model_service.py` (scaler + CNN-LSTM); `model/class_action_mapping.py`; `model/target_selection.py`; `backend/prevention_runtime.py` + `model/prevention_executor.py` → Windows Firewall (`netsh`); `backend/shap_service.py`; `backend/cert_in_mapping.py`; `backend/app.py` (Flask API); `frontend/` (React dashboard, 1 s polling); `model/results/prevention_execution_log.jsonl`; offline training in Colab → `model/artifacts/` | No (a simplified 6-step pipeline exists on Review 4 slide 5) | Create | Required |
| Fig. 4.2 | Use case diagram | 4.2 | Actors and functions | Actors: analyst/operator, administrator (env-var configuration), attacker device, Windows Firewall. Use cases: upload CSV; upload Wireshark capture; replay stream; start/stop live capture; view detections; view SHAP explanation; view window flows; view blocked devices; revoke; system: auto-block, hold for review | No | Create | Required |
| Fig. 4.3(a) | Data flow diagram, Level 0 | 4.3 | System context | Entities: network/attacker, analyst, Windows Firewall; process: ThreatLens IDS/IPS | No | Create | Required |
| Fig. 4.3(b) | Data flow diagram, Level 1 | 4.3 | Internal processes and stores | 1.0 capture/parse → 2.0 flows & features → 3.0 window & scale → 4.0 classify → 5.0 policy → 6.0 target & execute → 7.0 explain → 8.0 present; stores: D1 model artifacts, D2 execution log (JSONL), D3 results buffer | No | Create | Required |
| Fig. 4.4(a) | Sequence: live detection and automatic blocking | 4.4 | Time order of the live path | `backend/live_capture.py` (`_on_frame`, `_flow_step`, `_predict_step`), `prevention_runtime.execute_for_result`, `prevention_executor.execute_action`, `/api/live/poll` | No | Create | Required |
| Fig. 4.4(b) | Sequence: Wireshark capture / CSV upload | 4.4 | Batch path | `/api/predict_pcap`, `/api/predict_csv`, `analyze_frame` | No | Create | Required (one or more sequence diagrams) |
| Fig. 4.4(c) | Sequence: SHAP explanation request | 4.4 | Explain path | `/api/explain_window`, `backend/shap_service.py` | No | Create | Recommended |
| Fig. 4.4(d) | Sequence: revoke a block | 4.4 | Undo path | `/api/prevention/revoke`, `revoke_action`, `/api/prevention/active` | No | Create | Recommended |

Note: no code-generated diagrams exist in the repository; all of these must be
drawn (e.g. draw.io / PlantUML) and checked against the source files listed.

## 2. Other figures

| No. | Proposed title | Section | Purpose | Exists? | Current path | Action | Req. |
|---|---|---|---|---|---|---|---|
| Fig. 3.1 | Methodology pipeline (data → model → policy → firewall → dashboard) | 3.2 | Overview | Partially (slide 5 of the Review 4 deck) | deck, outside repo | Create/Reuse | Recommended |
| Fig. 3.2 | CICIDS2017 class distribution | 3.2.1 | Imbalance | Yes | `output/class_distribution.png` | Reuse/Verify (matches 2,655,060 rows?) | Recommended |
| Fig. 3.3 | Feature correlation heatmap | 3.2.2 | Feature analysis | Yes | `output/correlation_heatmap.png` | Reuse/Verify | Recommended |
| Fig. 4.5 | CNN-LSTM layer diagram | 4.5 | Model structure | Partially (slide 7 layer stack) | deck | Create | Recommended |
| Fig. 4.6 | Live engine thread model | 4.5 / 4.1 | Explain real-time design | No | — | Create | Recommended |
| Fig. 6.1 | CNN-LSTM v2 training and validation curves | 6.3 | Training behaviour | Yes | `model/results/cnn_lstm_v2_training_curves.png` | Reuse | Recommended |
| Fig. 6.2 | CNN-LSTM v2 confusion matrix (CICIDS2017 test) | 6.3 | Per-class errors | Yes | `model/results/cnn_lstm_v2_confusion_matrix.png` | Reuse | Recommended |
| Fig. 6.3(a)–(c) | SHAP profiles of the three MU-IoT error groups | 6.3 | Error causes | Yes | `model/results/mu_iot/mu_iot_shap_spyware.png`, `mu_iot_shap_hping3.png`, `mu_iot_shap_vulnscan.png` | Reuse | Recommended |
| Fig. 6.4 | Dashboard home page | 6.1 | UI | No (in repo) | — | Capture | Recommended |
| Fig. 6.5 | Batch Analysis results (timeline, class distribution, traffic composition) | 6.1 | Upload path | No | — | Capture (upload `demo/demo_cicids_test.csv` and `captures/Capture2.pcapng`) | Recommended |
| Fig. 6.6 | SHAP explanation panel | 6.1 | Explainability | No | — | Capture | Recommended |
| Fig. 6.7 | Live capture: PortScan executed, repeats "already blocked" | 6.4 | Live detection and blocking | Outside repo (team screenshots, demo recording) | — | Capture/Copy into `docs/report_assets/` | Recommended |
| Fig. 6.8 | Blocked devices panel and Revoke | 6.4 | Prevention UI | Outside repo | — | Capture | Recommended |
| Fig. 6.9 | Windows Firewall rules created (`Get-NetFirewallRule IDS_DEMO_*`) | 6.4 | Proof of real rules | No | — | Capture | Recommended |
| Fig. 6.10 | nmap output on the attacker tablet | 6.4 | Attack evidence | Outside repo | — | Capture | Recommended |
| Fig. 6.11 | Live-run timeline (probe → detection → block → revoke) | 6.4 | Latency | Data yes | `model/results/hotspot_live_results.md` | Create | Recommended |

Screenshots must not show personal data (other people's IP addresses are
acceptable only if anonymised; no browsing content; no tokens).

## 3. Tables

| No. | Proposed title | Section | Source (path) | Exists as data? | Action | Req. |
|---|---|---|---|---|---|---|
| Table 2.1 | Summary of surveyed literature | 2.1 | `docs/report/ieee_paper_content.md` §II + Q11 | Partial | Create | Recommended |
| Table 3.1 | Datasets used | 3.2.1 | `docs/report/person_a_report.md` §14 | Yes | Reuse | Recommended |
| Table 3.2 | CICIDS2017 cleaning statistics per file | 3.2.2 | `person_a_report.md` §2; `output/cleaning_report.csv` | Yes | Reuse | Recommended |
| Table 3.3 | The 20 selected CICIDS2017 features | 3.2.2 | `person_a_report.md` §3.2; `output/selected_features.csv` | Yes | Reuse | Recommended |
| Table 3.4 | MU-IoT class counts per split | 3.2.2 | `output/mu_iot/handoff_v3/class_counts_by_split.csv`; `person_a_report.md` | Yes | Reuse | Recommended |
| Table 3.5 | Class-weighting schemes compared (v1/v2/v3) | 3.2.4 | `model/results/cnn_lstm_versions_comparison.txt` | Yes | Reuse | Recommended |
| Table 4.1 | CNN-LSTM layers and parameters | 4.5 | `person_b_report.md` §2 | Yes | Reuse | Recommended |
| Table 4.2 | Prevention policy per class (action, threshold or review lock) | 4.5 | `model/class_action_mapping.py`; Review 4 slide 9 | Yes | Reuse | Recommended |
| Table 4.3 | REST API endpoints | 4.1 | `backend/app.py`; `backend/README.md` | Yes | Create | Recommended |
| Table 5.1 | Hardware requirement | 5.1 | `model/results/inference_benchmark.txt`; `hotspot_live_results.md` | Mostly (Q13, Q14) | Create | Required (content of 5.1) |
| Table 5.2 | Software requirement and versions | 5.2 | `backend/requirements.txt`; `frontend/package.json` | Yes | Create | Required (content of 5.2) |
| Table 6.1 | CICIDS2017 overall: CNN-LSTM vs random forest | 6.3 | `cnn_lstm_v2_full_test_results.txt`; `chronological_random_forest_results.txt` | Yes | Reuse | Recommended |
| Table 6.2 | CICIDS2017 per-class F1 | 6.3 | `person_b_report.md` §5.1 | Yes | Reuse | Recommended |
| Table 6.3 | MU-IoT unseen-only results | 6.3 | `model/results/mu_iot/mu_iot_unseen_only_rescore.txt`; `mu_iot_random_forest_results.txt` | Yes | Reuse | Recommended |
| Table 6.4 | MU-IoT held-out recordings | 6.3 | `person_b_report.md` §5.2 | Yes | Reuse | Recommended |
| Table 6.5 | Causes of the main MU-IoT errors (SHAP) | 6.3 | `model/results/mu_iot/mu_iot_shap_report.txt` | Yes | Reuse | Recommended |
| Table 6.6 | Prevention policy outcomes | 6.3 | `prevention_policy_cicids2017.txt`; `mu_iot/prevention_policy_mu_iot.txt` | Yes | Reuse | Recommended |
| Table 6.7 | Extractor vs CICFlowMeter-V3 on the original pcap | 6.4 | `model/results/extractor_validation.md` | Yes | Reuse | Recommended |
| Table 6.8 | Real-traffic captures (scan, browsing, device use) | 6.4 | `model/results/hotspot_live_results.md` | Yes | Reuse | Recommended |
| Table 6.9 | Live-run timeline | 6.4 | `hotspot_live_results.md` | Yes | Reuse | Recommended |
| Table 6.10 | Inference speed | 6.3 | `model/results/inference_benchmark.txt` | Yes | Reuse | Recommended |
| Table 6.11 | Test summary (suites, counts, real-firewall check) | 6.2 | `model/test_*.py`, `backend/test_live_capture.py`, `prevention_live_check.txt` | Mostly (Q16) | Create | Recommended |
| Table 6.12 | SHAP explainer comparison (Gradient vs Kernel) | 3.2.5 / 6.3 | `docs/report/person_c_report.md` §1 | Yes | Reuse | Recommended |

## 4. Equations (only if used in the text)

| No. | Equation | Section | Source |
|---|---|---|---|
| (4.1) | 1-D convolution output | 4.5 | standard; layer settings `person_b_report.md` §2 |
| (4.2)–(4.4) | LSTM gates and state update | 4.5 | standard [Hochreiter & Schmidhuber] |
| (4.5) | Softmax | 4.5 | standard |
| (4.6) | Weighted sparse categorical cross-entropy with √-balanced class weights | 4.5 | `person_b_report.md` §4 |
| (4.7) | Standardisation (fit on training rows) | 3.2.2 | `person_a_report.md` |
| (4.8) | SHAP additivity (base value + Σφ = output) | 4.5 | `person_c_report.md` §1 |
| (6.1) | Precision, recall, F1, macro-F1 | 6.3 | standard |
