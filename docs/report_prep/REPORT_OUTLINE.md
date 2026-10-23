# Report Outline — Hybrid CNN-LSTM IDS/IPS Project (VTU AIML, 8th semester)

Headings marked **[OFFICIAL]** come from the template (see
`REPORT_TEMPLATE_SPECIFICATION.md`) and must be kept as written. Sub-items
marked *[REC]* are recommended subsections derived from what the project
actually contains; they may be renamed or merged with the guide's approval.
Items marked **[VERIFY]** depend on an answer in
`MISSING_INFORMATION_QUESTIONNAIRE.md`. Task IDs (e.g. `A01`, `C06`) refer to
`REPORT_MASTER_CHECKLIST.md`.

---

## Preliminary pages (Roman numerals) [OFFICIAL]

| Page | Heading | Depends on |
|---|---|---|
| i | Title sheet / cover — "A Project Report on" "<TITLE>" | A01, A02, A03, A07, A09 |
| ii | Certificate | A01–A04, A07, A10 |
| iii | Declaration | A01, A02, A07, A10 |
| iv | Acknowledgement | A03–A06 |
| v | Abstract (one page; TNR 12, justified, 1.5 spacing) | C01 |
| vi | Table of Contents | F01 |
| vii | List of Figures | F02 |
| viii | List of Tables | F03 |
| ix | Nomenclature Used | C17 |

(Page numbers above are indicative; the template sample shows vii and viii for
the lists. [VERIFY] final numbering after layout.)

---

## Chapter 1 — Introduction [OFFICIAL]

**1.1 Introduction [OFFICIAL]**
- *[REC] 1.1.1 Background* — network intrusion detection, flow-based IDS,
  deep learning for IDS, why live operation matters.
- *[REC] 1.1.2 Problem statement* — benchmark accuracy ≠ a system that acts;
  random splits reward memorisation; benign-dominated data hides rare-class
  failures; models are rarely run on live traffic.
- *[REC] 1.1.3 Motivation* — the guide's review: input must be live and from
  real (Wireshark) captures; detection must lead to prevention.
- *[REC] 1.1.4 Scope and limitations of the project* — IPS-lite (listed
  devices / TEST-NET only, kill switch); one live attack type demonstrated;
  no cloud deployment; MU-IoT model not in the dashboard. [VERIFY title scope, Q1]
- *[REC] 1.1.5 Organisation of the report*

## Chapter 2 — Literature Survey [OFFICIAL]

**2.1 Literature Survey [OFFICIAL]**
- *[REC] 2.1.1 Datasets and flow features* (CICIDS2017, CICFlowMeter)
- *[REC] 2.1.2 Deep learning for intrusion detection* (CNN, LSTM, hybrids)
- *[REC] 2.1.3 Pitfalls in ML-based IDS evaluation* (closed-world gap,
  data snooping, CICIDS2017 artefacts)
- *[REC] 2.1.4 Explainable AI for IDS* (SHAP)
- *[REC] 2.1.5 Summary table of surveyed papers* (Table 2.1)
- *[REC] 2.1.6 Research gap addressed by this project*

## Chapter 3 — Objective and Methodology [OFFICIAL]

**3.1 Objective [OFFICIAL]**
- Detect 14 attack types from windows of flows with a hybrid CNN-LSTM;
  evaluate with leakage control and a fair baseline; explain with SHAP;
  prevent through a per-class policy and the host firewall; operate on live
  traffic and Wireshark captures.

**3.2 Methodology [OFFICIAL]**
- *[REC] 3.2.1 Datasets* — CICIDS2017 (15 classes, 2,655,060 cleaned rows, 20
  features); MU-IoT (7 classes, 3,936,753 rows × 38 features).
- *[REC] 3.2.2 Data preprocessing and feature selection* (Person A)
- *[REC] 3.2.3 Evaluation design: chronological split, held-out recordings,
  unseen-only rescoring, baseline on identical examples*
- *[REC] 3.2.4 CNN-LSTM model and training* (Person B)
- *[REC] 3.2.5 Explainability: SHAP KernelExplainer in the dashboard;
  expected-gradient SHAP for the MU-IoT error analysis* (Persons C and B)
- *[REC] 3.2.6 Prevention policy and execution engine* (Person B)
- *[REC] 3.2.7 Live capture and packet-to-flow extraction* (Person B)
- *[REC] 3.2.8 Backend API and dashboard* (Person C)

## Chapter 4 — System Design [OFFICIAL]

- **4.1 System Architecture [OFFICIAL]** — Fig. 4.1 (to be created, C06)
- **4.2 Use Case Diagram [OFFICIAL]** — Fig. 4.2 (to be created, C07)
- **4.3 Data Flow Diagram [OFFICIAL]** — Fig. 4.3(a) Level 0, Fig. 4.3(b)
  Level 1 (to be created, C08)
- **4.4 Sequence Diagram [OFFICIAL]** — Fig. 4.4(a) live detect-and-block,
  4.4(b) capture/CSV upload, 4.4(c) SHAP explanation, 4.4(d) revoke (to be
  created, C09)
- **4.5 Algorithms Used [OFFICIAL]**
  - *[REC] 4.5.1 Packet-to-flow extraction (CICFlowMeter-V3 rules)*
  - *[REC] 4.5.2 Sliding-window sequence construction*
  - *[REC] 4.5.3 Hybrid CNN-LSTM classifier* (with equations, C21)
  - *[REC] 4.5.4 Random-forest baseline*
  - *[REC] 4.5.5 SHAP (KernelExplainer; expected gradients)*
  - *[REC] 4.5.6 Prevention policy: F1-derived thresholds and review locks*
  - *[REC] 4.5.7 Target selection and firewall execution (safety checks)*

## Chapter 5 — Hardware and Software Requirement [OFFICIAL]

- **5.1 Hardware Requirement [OFFICIAL]** (C11)
- **5.2 Software Requirement [OFFICIAL]** (C12)

## [VERIFY] Chapter 6 — Implementation, Testing and Results

Not named in the supplied content structure, but the template's sample List
of Figures references Chapter 6, and the project's main evidence (results,
tests, live run) needs a home. **Ask the guide (Q9)** whether to add this
chapter or place the material elsewhere. If approved:
- *6.1 Implementation details and screenshots* (C15)
- *6.2 Testing and validation* (C14)
- *6.3 Results: CICIDS2017, MU-IoT, SHAP error analysis, prevention policy*
- *6.4 Live capture validation and the real-network live run*
- *6.5 Discussion and limitations*

## Conclusion [OFFICIAL]
- *[REC] Future enhancements* (retraining on present-day IPv6/QUIC traffic;
  isolated lab for further attack types; calibration set; repeated runs;
  MU-IoT in the dashboard) — include only if the guide agrees.

## References [OFFICIAL]
- Numbered list; style [VERIFY]; see C19, C20.

## [VERIFY] Appendices
Not required by the supplied specification. Candidates if the guide wants
them: API endpoint reference, test summary, demo checklist.
