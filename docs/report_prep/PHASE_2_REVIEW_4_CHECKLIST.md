# Phase 2 Review 4 — Presentation Checklist

Kept separate from the report checklist (figures may be reused in both).
Template: `Phase 2  Review 4 Presntaion format.pptx` (two slides). The team's
built deck: `PROJECTS/Report format AIML 8th sem/Report format AIML 8th sem/
Phase 2 Review 4 - CNN-LSTM IDS Presentation.pptx` (12 slides, on the
template; outside the repository).

## 1. Template slide 1 — title and team [OFFICIAL]

| Element | Required | In the built deck | Status / action |
|---|---|---|---|
| JIT logo, Jyothy Charitable Trust, JIT name, address, AICTE approval, VTU affiliation | Yes | Kept from the template | Done |
| "Department of Artificial Intelligence and Machine Learning" | Yes | Yes (template typo "machinr" fixed) | Done |
| "Project Presentation on" | Yes | Yes | Done |
| Project title | Yes | Paper title "A Hybrid CNN-LSTM Intrusion Detection and Prevention System with Live Packet Capture" | **Verify against the final title (Q1)** |
| Batch number | Yes | Blank ("Batch Number:") | **Missing — fill in (Q5)** |
| Student names and USNs | Yes | Maanya B S 1JT23AI030; Ruthwik Sai Ganesh 1JT23AI042; Varshini D N 1JT23AI060 | Verify (Q2) |
| Guide name | Yes | Dr. Madhu B R | Verify (Q3) |
| Guide designation | Yes | Professor & Head, Department of AIML | Verify (Q3) |
| Department and batch line (footer) | Yes | "Dept of AIML, Batch 2023-27" | **Verify (Q5)**; template showed 2020-24 / 2024-26 |

## 2. Template slide 2 — contents [OFFICIAL]

Required topics, in order: Abstract · Objective · Literature Survey ·
Proposed Methodology · Implementation and Result Analysis · Demonstration ·
References. The built deck keeps this list unchanged.

## 3. Project content per topic

| Topic | Built deck slide(s) | Content and assets (source) | Status |
|---|---|---|---|
| Abstract | 3 | Summary of system and headline results (`docs/report/ieee_paper_content.md`) | Done |
| Objective | 3 | Five objectives: detect, evaluate honestly, explain, prevent, go live | Done |
| Literature Survey | 4 | 5 works with key idea and relevance (Sharafaldin 2018, Vinayakumar 2019, Engelen 2021, Sommer & Paxson 2010, Lundberg & Lee 2017) | Done; verify references (C19) |
| Proposed Methodology | 5 (pipeline), 6 (Data — Maanya B S), 7 (Model and Prevention — Ruthwik Sai Ganesh), 8 (Backend and Dashboard — Varshini D N) | Person reports; dashboard screenshot on slide 8 | Done; each presenter to review own slide (P04) |
| Attack types (team requirement) | 9 | All 14 CICIDS2017 attack classes with category, prevention action, auto threshold or human review, and demo mode; MU-IoT classes (`model/class_action_mapping.py`) | Done |
| Implementation and Result Analysis | 10 | CICIDS2017 and MU-IoT tables vs random forest; 99.8% extractor agreement; 96.6% / 0.33% policy; ~2 s live block; 1.48 ms per prediction (`model/results/*`) | Done |
| Demonstration | 11 | Six demo steps; live-run screenshot (PortScan executed, repeats already blocked); safety note | Done; optionally replace with a still from the latest recording (P05) |
| References | 12 | 7 IEEE-style references | Done; verify (C19) |

## 4. Demonstration readiness (if presented live)

| Item | Source | Status |
|---|---|---|
| Live demo steps and clean-up | `docs/LIVE_DEMO_CHECKLIST.md` | Ready |
| Demo code | `main` / tag `v2-live`; local folder `ids-demo` | Ready |
| Fallback: Wireshark upload of the scan capture | `captures/Capture2.pcapng` (local, not committed) | Ready |
| All-attack demonstration | `demo/demo_cicids_test.csv` | Ready |
| Recorded demo video | team recording | Confirm (Q15) |

## 5. Do-not-claim list (not implemented)

Cloud deployment; IoT data collection hardware; Indian network datasets;
live demonstration of attacks other than a port scan; MU-IoT model inside the
dashboard; true bandwidth rate limiting (it is a temporary block).
