# Project Status — Live IDS / IPS-lite, Current State (2026-10-18)

Supersedes the 2026-10-02 version. If you are an assistant helping on this
project with no other context, read this file fully before touching
integration code, then the interface documents it points to.

---

## 1. What This Project Is

A CNN-LSTM intrusion detection system that reads short sequences of network
flows, explains its decisions with SHAP, and acts on them through a cautious
prevention layer. It is evaluated on **CICIDS2017** (benchmark, 15 classes)
and **MU-IoT** (real IoT traffic from Manipur University, 7 classes).

After the guide's review of the first demo (input must be **live**, and from
**real captures** such as Wireshark rather than prepared test data), the
system also takes:

- **live traffic** from the laptop's network interface (Npcap), detected and
  blocked in real time; and
- **Wireshark captures** (.pcap / .pcapng) uploaded to the dashboard.

Both go through the same pipeline: packets -> flows -> 20 CICIDS2017
features -> CNN-LSTM -> policy -> Windows Firewall. Prevention is
**IPS-lite**: real firewall rules, but only for RFC 5737 TEST-NET addresses
or LAN devices explicitly listed in `IDS_PREVENTION_DEMO_TARGETS`, and only
when the kill switch `IDS_PREVENTION_EXECUTION_ENABLED` is on.

Team: Maanya B S — data; Ruthwik Sai Ganesh — model, evaluation, prevention,
live capture; Varshini D N — dashboard and backend.

---

## 2. Where Each Area Stands

| Area | State | Branch |
|---|---|---|
| CICIDS2017 / MU-IoT data, models, baselines, SHAP | Done | `main` (tag `v1-demo`) |
| Prevention policy and engine, wired into the backend | Done | `main` |
| Dashboard: CSV upload, replay, SHAP, prevention panel | Done | `main` |
| Packet -> flow extractor (IPv4 + IPv6), validated on the original CICIDS2017 pcap | Done | `person-b-model` |
| Opt-in LAN demo targets, one rule per device, `active_rules()` | Done | `person-b-model` |
| Live capture engine `backend/live_capture.py` (detect + block) | Done; live run on a real network passed (2026-10-18) | `person-b-model` |
| Backend: `/api/predict_pcap`, `/api/live/*`, Live capture UI, Blocked devices panel | Done (against a stub until the merge below) | `varshini-dashboard` |
| Merge `person-b-model` into `varshini-dashboard` | **Pending** (tested locally: clean) | — |
| PR to `main` and a new tag | **Pending**, after the live run | — |

---

## 3. Results

### Models (unchanged since `v1-demo`)

| CICIDS2017, same test windows | Accuracy | Weighted F1 | Macro F1 |
|---|---|---|---|
| CNN-LSTM (10-flow windows) | 0.9842 | 0.9864 | 0.5857 |
| Random forest (single flows) | 0.9911 | 0.9908 | 0.7803 |

| MU-IoT, same test windows | Within macro F1 | Held-out macro F1 | Normal flagged as attack |
|---|---|---|---|
| CNN-LSTM (20-flow windows) | 0.936 | 0.676 | 9.3% |
| Random forest (single rows) | 0.816 | 0.404 | 17.2% |

On CICIDS2017 the random forest is better; on MU-IoT the CNN-LSTM is clearly
better (details: `model/MODEL_INTERFACE.md`, `model/results/mu_iot/FINDINGS.md`).

### Extractor against the original data (`model/results/extractor_validation.md`)

UNB's original Friday pcap through our extractor, compared flow by flow with
CICFlowMeter-V3's official rows: **99.8%** of 5,957 matched flows agree on all
20 features (at the precision the CSV printed), **49/49 PortScan flows**.
Two differences were found this way and fixed: time features in whole
microseconds, and V3's rule that a FIN which *starts* a flow does not end it.

### Real traffic on a phone hotspot (`model/results/hotspot_live_results.md`)

| Capture | Result |
|---|---|
| `nmap -sT` scan from the tablet | 98% of windows PortScan; live replay: first detection 1.6 s after the first SYN, every automatic action against the scanner only |
| Laptop browsing (IPv4 + IPv6) | 11.1% of windows not BENIGN, 7.6% recommend automatic action, **0** with a target that could be blocked |
| Tablet reloading a page on the laptop | 0 automatic actions against the tablet (Bot predictions, held for review) |
| **Live run, shared router** | Scan blocked about 2 s after the first probes; three scan -> block -> revoke cycles; another person's device flagged and refused 10 times |

---

## 4. Prevention Layer

- **Policy** (`model/class_action_mapping.py`): per class an action, severity
  and confidence threshold set inversely to F1. `get_action(cls, conf)` is
  CICIDS2017; MU-IoT needs `dataset="mu_iot"`. Locked to human review:
  CICIDS2017 Sql Injection, Heartbleed, Infiltration, Bot, Brute Force, XSS;
  MU-IoT MiTM and Spyware.
- **Engine** (`model/prevention_executor.py`, `PREVENTION_EXECUTION_INTERFACE.md`):
  kill switch (off by default), TEST-NET or listed LAN devices only,
  deny-list, admin check, one rule per device, auto-expiry, startup sweep,
  `active_rules()`, revoke with the switch off, JSONL log.
- **Targets in live mode** (`model/target_selection.py`): the most frequent
  private IPv4 source in the window that is not this machine or the gateway;
  none -> recommendation only.
- Tests: 35 (policy + engine), 22/22 on the real firewall, 14 live engine,
  20 extractor, 3 validator, 8 target selection.

---

## 5. Open Work (in order)

1. **Dashboard teammate:** merge `origin/person-b-model` into
   `varshini-dashboard` (brings the live engine; the stub then switches off),
   show the poll's `error` and "recommended, no target", update the
   `revoke()` comment (TEST-NET or listed devices).
2. **Data teammate:** label the 10-minute browsing run as IPv4-only and
   re-run it with the current extractor (`--end-on-rst`, IPv6 included).
3. **Dashboard teammate, from the live run:** the Live detection log shows
   some window numbers more than once (the engine's are unique), and the
   armed-execution banner names only the TEST-NET ranges (listed LAN devices
   can be acted on too).
4. Rehearsal on the merged dashboard branch (`docs/LIVE_DEMO_CHECKLIST.md`),
   then PR `varshini-dashboard` -> `main` and a new tag.
5. **After the project:** remove `DisableStealthMode` from the three Windows
   Firewall profiles (then reboot) and delete any `IDS_TEST_allow_scanner`
   rule.

---

## 6. Open Team Decisions

1. **Project title**: it promises "IoT-based Data Collection and Cloud
   Deployment"; neither is built. Change the title or explain the scope.
2. **Whether the dashboard shows the MU-IoT model** or only CICIDS2017.
3. **IPv6 in the live demo**: on (default; honest coverage, 7.6% of browsing
   windows recommend actions that have no target) or off
   (`IDS_LIVE_IPV6=0`; cleaner screen, but 98% of hotspot packets ignored).

---

## 7. Where Things Are

| What | Where |
|---|---|
| Models, scalers, labels | `model/artifacts/` · `model/MODEL_INTERFACE.md`, `model/MU_IOT_MODEL_INTERFACE.md` |
| Flow extractor | `model/flow_features.py` (CLI: `python model/flow_features.py capture.pcapng -o flows.csv`) |
| Live engine | `backend/live_capture.py` (`list_interfaces`, `start`, `poll`, `stop`, `start_replay`) |
| Prevention | `model/prevention_executor.py`, `model/class_action_mapping.py`, `model/target_selection.py` |
| Results | `model/results/` (start with `extractor_validation.md`, `hotspot_live_results.md`) |
| Report sections | `docs/report/person_a_report.md`, `person_b_report.md`, `live_data_sources.md` |
| Tests | `python model/test_prevention.py`, `model/test_flow_features.py`, `model/test_target_selection.py`, `model/test_validate_against_cicids.py`, `backend/test_live_capture.py` |

---

## 8. Integration Gotchas

- **Npcap** must be installed (Wireshark's installer offers it); the backend
  must run **as Administrator** for real blocking.
- **Windows stealth mode** makes the laptop answer nothing to a scan, and a
  2017-trained model does not recognise a scan without replies. The demo
  needs stealth mode off and a temporary allow rule for the scanning device.
- **ExpressVPN** (or any VPN) must be off during live tests.
- Captures contain personal traffic: `captures/`, `*.pcap`, `*.pcapng` are
  git-ignored; never commit them.
- On this laptop (about 0.7 GB free RAM) set `OPENBLAS_NUM_THREADS=1` before
  running tests that import scikit-learn or TensorFlow.
- Load the MU-IoT model with `keras.models.load_model(path, compile=False)`.
- Resolve artifact paths from the repository root, not the working directory.
