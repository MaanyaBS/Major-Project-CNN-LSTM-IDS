# Report Master Checklist

One consolidated list of everything needed before the final report can be
drafted. Each task lists every report section that depends on it. Status
values: **Done** (evidence exists and is verified), **Ready** (information
available, artefact/text still to produce), **Partial**, **Missing**,
**Verify** (needs confirmation). Priority: **P1** blocks the report or
submission; **P2** needed for a complete chapter; **P3** polish.
Evidence paths are on `main` (tag `v2-live`) unless noted.

## A. Identity, institution, academic details

| ID | Information / artefact | Section(s) | Exists? | Evidence | Missing | Pri | Next action | Status |
|---|---|---|---|---|---|---|---|---|
| A01 | Final project title | Title sheet, Certificate, Declaration, Abstract, Ch 1, slide 1 | 4 variants | README, Review 2 & 4 decks, paper | Agreed final title | P1 | Answer Q1 with the guide | Verify |
| A02 | Student names + USNs | Title, Certificate, Declaration, Acknowledgement, slide 1 | Yes | Review 2 deck (outside repo) | Confirmation | P1 | Q2 | Verify |
| A03 | Guide name + designation | Title, Certificate, Acknowledgement, slide 1 | Yes (Dr. Madhu B R, Professor & Head) | Review 2 deck | Whether guide = HOD | P1 | Q3 | Verify |
| A04 | HOD name + designation | Certificate, Acknowledgement | Yes (template) | Certificate template | Confirmation | P1 | Q3 | Verify |
| A05 | Principal name | Acknowledgement | Template only | Acknowledgement template | Confirmation | P2 | Q4 | Verify |
| A06 | Project coordinator | Acknowledgement | Template only | Acknowledgement template | Confirmation | P2 | Q4 | Verify |
| A07 | Academic year, batch, batch number | Certificate, Declaration, Title, slides | Conflicting | Templates, decks | Official values; batch number | P1 | Q5 | Missing |
| A08 | Degree name (B.E. vs B.Tech) | Title, Certificate, Declaration | Conflicting | Templates | Official wording | P1 | Q6 | Verify |
| A09 | Other genuine acknowledgements | Acknowledgement | No | — | Names, if any | P3 | Q7 | Missing |
| A10 | Signatures, dates, examiners | Certificate, Declaration, Acknowledgement | No (placeholders) | — | At submission | P1 | Leave placeholders until signing | Missing |

## B. Content

| ID | Information / artefact | Section(s) | Exists? | Evidence | Missing | Pri | Next action | Status |
|---|---|---|---|---|---|---|---|---|
| C01 | Abstract (one page) | Abstract, slide 3 | Draft exists | `docs/report/ieee_paper_content.md` (person-b-model) | Final title framing | P1 | Adapt to one page, TNR 12, justified, 1.5 | Ready |
| C02 | Background, problem statement, motivation, scope | Ch 1 | Yes | Paper §I; `docs/PROJECT_STATUS_CURRENT.md`; README | Scope wording vs title (Q8) | P1 | Draft Ch 1 | Ready |
| C03 | Objectives | Ch 3.1, slide 3 | Yes | Review 4 deck slide 3; paper §I | — | P1 | Copy and expand | Ready |
| C04 | Literature survey (+ Table 2.1) | Ch 2, slide 4 | Partial | Paper §II (9 works) | Phase-1 papers (Q11), count (Q10) | P1 | Collect, verify, tabulate | Partial |
| C05 | Methodology text (data, evaluation, model, SHAP, prevention, live capture, dashboard) | Ch 3.2, slides 5–8 | Yes | `docs/report/person_a_report.md`, `person_b_report.md`, `person_c_report.md`; `model/*_INTERFACE.md` | Fig. 3.1 | P1 | Draft from person reports | Ready |
| C06 | System architecture diagram | Ch 4.1 | No | Components in `backend/`, `model/`, `frontend/` | Diagram | P1 | Create Fig. 4.1 (see artefact inventory) | Missing |
| C07 | Use case diagram | Ch 4.2 | No | Dashboard routes, API | Diagram | P1 | Create Fig. 4.2 | Missing |
| C08 | Data flow diagrams (Level 0, Level 1) | Ch 4.3 | No | Pipeline code | Diagrams | P1 | Create Fig. 4.3(a)(b) | Missing |
| C09 | Sequence diagrams (live block; upload; explain; revoke) | Ch 4.4 | No | `backend/live_capture.py`, `backend/app.py` | Diagrams | P1 | Create Fig. 4.4(a)–(d) | Missing |
| C10 | Algorithms used (pseudo-code, explanations) | Ch 4.5 | Yes | `model/flow_features.py`, `class_action_mapping.py`, `target_selection.py`, `prevention_executor.py`, `backend/shap_service.py`, `cnn_lstm_architecture.py` | Pseudo-code text | P1 | Write algorithm boxes | Ready |
| C11 | Hardware requirement | Ch 5.1 | Mostly | `model/results/inference_benchmark.txt`, `hotspot_live_results.md` | v2 training GPU (Q13), used vs minimum (Q14) | P1 | Table 5.1 | Partial |
| C12 | Software requirement (with versions) | Ch 5.2 | Yes | `backend/requirements.txt`, `frontend/package.json`, benchmark header | Confirm Node/npm version on final machine | P1 | Table 5.2 | Ready |
| C13 | Results (CICIDS2017, MU-IoT, SHAP, policy, extractor, live run, speed) | Ch 6 [VERIFY Q9], slide 10 | Yes | `model/results/*`, `person_b_report.md` §5–9 | Chapter placement (Q9) | P1 | Build result tables | Ready |
| C14 | Testing and validation | Ch 6 [VERIFY] | Mostly | `model/test_*.py`, `backend/test_live_capture.py`, `model/results/prevention_live_check.txt`, `extractor_validation.md` | Backend API/stream/smoke logs (Q16) | P2 | Test summary table | Partial |
| C15 | Screenshots / demo stills | Ch 6 [VERIFY], Ch 4 support, slides 8, 11 | Outside repo only | Team's screenshots and today's recording | Clean set in the repo (Q15) | P1 | Capture and store under `docs/report_assets/` | Missing |
| C16 | Conclusion and future enhancements | Conclusion | Yes | Paper §IX; `person_b_report.md` §10 | Guide's view on "future work" (optional) | P2 | Draft | Ready |
| C17 | Nomenclature table | Preliminary | Can be compiled | See list below | — | P2 | Build table | Ready |
| C18 | Limitations statement | Ch 1 scope / Ch 6 / Conclusion | Yes | `person_b_report.md` §10; `hotspot_live_results.md` | — | P2 | Include honestly | Ready |
| C19 | Verified references | References, Ch 2 | Partial | Paper references (10) | Verification against sources; style (Q17) | P1 | Verify every entry | Partial |
| C20 | MU-IoT dataset citation | References, Ch 3 | No | — | Citation (Q12) | P1 | Obtain from data teammate | Missing |
| C21 | Equations (CNN, LSTM gates, softmax, weighted cross-entropy, √-balanced weights, StandardScaler, F1/macro-F1, SHAP additivity) | Ch 4.5 | Recommended | `person_b_report.md` §2–4; `person_c_report.md` §1 | Typeset equations | P3 | Write numbered equations (only those used) | Ready |
| C22 | README inconsistency ("recommended/simulated responses") | Source of truth for writers | Found | `README.md` | Correction | P3 | Update README after the report is drafted (doc-only change) | Verify |

## C. Front matter generation and formatting

| ID | Information / artefact | Section(s) | Exists? | Evidence | Missing | Pri | Next action | Status |
|---|---|---|---|---|---|---|---|---|
| F01 | Table of Contents | Preliminary | No | — | Final document | P1 | Generate from Word headings | Missing |
| F02 | List of Figures | Preliminary | No | Artefact inventory | Final numbering | P1 | Generate from captions | Missing |
| F03 | List of Tables | Preliminary | No | Artefact inventory | Final numbering | P1 | Generate from captions | Missing |
| F04 | Apply template styles (TNR 18/16/14/12 B; body TNR 12, 1.5, justified, no hyphenation; captions TNR 12 centred) | Whole report | Specified | `REPORT_TEMPLATE_SPECIFICATION.md` §4 | Margins etc. (Q18) | P1 | Use the template's Word styles | Ready |
| F05 | Page settings (paper, margins, binding, headers/footers, numbering) | Whole report | No | — | Q18 | P1 | Confirm, then set | Missing |
| F06 | Extra submission items (similarity report etc.) | Submission | Unknown | — | Q19 | P2 | Confirm | Missing |
| F07 | Length target | Whole report | Unknown | — | Q20 | P3 | Confirm | Missing |

## D. Presentation (Phase 2 Review 4)

| ID | Information / artefact | Exists? | Evidence | Missing | Pri | Next action | Status |
|---|---|---|---|---|---|---|---|
| P01 | 12-slide deck on the college template | Yes | `PROJECTS/Report format AIML 8th sem/.../Phase 2 Review 4 - CNN-LSTM IDS Presentation.pptx` (outside repo) | — | P1 | Review with team | Done |
| P02 | Batch number on slide 1 | No | — | Q5 | P1 | Fill in | Missing |
| P03 | Title on slide 1 matches the final title | Verify | Slide 1 uses the paper title | Q1 | P1 | Update after Q1 | Verify |
| P04 | Each presenter reviews own methodology slide (6/7/8) | — | — | Team check | P2 | Review | Missing |
| P05 | Demo stills / recording for slide 11 or live demo backup | Partial | Live-run screenshot used | Today's recording | P2 | Optional update | Partial |

See `PHASE_2_REVIEW_4_CHECKLIST.md` for slide-by-slide detail.

## Nomenclature — terms actually used by the project (for C17)

AI, AIML, API, BN (Batch Normalisation), CERT-In (Indian Computer Emergency
Response Team), CICFlowMeter, CICIDS2017 (Canadian Institute for
Cybersecurity Intrusion Detection System dataset 2017), CNN (Convolutional
Neural Network), Conv1D, CORS (Cross-Origin Resource Sharing), CPU, CSV,
DDoS (Distributed Denial of Service), DoS, F1 (F1-score), FIN / RST / SYN /
ACK (TCP flags), FTP, GPU, HTTP, IAT (Inter-Arrival Time), IDS (Intrusion
Detection System), IoT, IP, IPS (Intrusion Prevention System), IPv4, IPv6,
JSON, JSONL (JSON Lines), LAN, LSTM (Long Short-Term Memory), MiTM
(Man-in-the-Middle), ML, MQTT, MU-IoT, nmap (Network Mapper), Npcap, pcap /
pcapng (packet capture formats), QUIC, ReLU (Rectified Linear Unit), REST,
RF (Random Forest), SHAP (SHapley Additive exPlanations), SQL, SQLi, SSDP,
SSH, TCP, TEST-NET (RFC 5737 documentation address ranges), TLS, UDP, UI,
VLAN, VTU, XAI (Explainable AI), XSS (Cross-Site Scripting). Verify each
expansion when writing; include only terms that appear in the final text.
