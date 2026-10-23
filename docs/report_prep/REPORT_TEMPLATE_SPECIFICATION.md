# Report Template Specification — VTU AIML 8th-Semester Project Report

Self-contained summary of the official report requirements, as supplied by the
team in the task specification (the original template ZIP was not available
to the analysing agent; this file is the reference). **[OFFICIAL]** marks a
requirement stated by the templates; **[VERIFY]** marks a template
inconsistency or an unstated parameter that must be confirmed with the guide
or department before the final report is produced. Nothing here is the
project's technical content.

> **Answers received 2026-10-23:** title unchanged (registered title); guide
> = HOD (Dr. Madhu B R); B.E.; academic year/batch 2023-27; Principal Dr. K.
> Gopalakrishna; Chapter 6 allowed. Assumed defaults for citation style and
> page settings are listed in `MISSING_INFORMATION_QUESTIONNAIRE.md`.

## 1. Institutional context [OFFICIAL]

| Item | Value in the specification |
|---|---|
| University | Visvesvaraya Technological University (VTU), Belagavi |
| College | Jyothy Institute of Technology, Bengaluru (Jyothy Charitable Trust; Tataguni, off Kanakapura Road, Bengaluru-560082; AICTE-approved; VTU-affiliated) |
| Department | Artificial Intelligence and Machine Learning (AIML) |
| Level | Eighth-semester project; report submitted in partial fulfilment of the degree |

**[VERIFY] Template inconsistencies (do not copy blindly):**
- Degree: "Bachelor of Engineering" (title sheet) vs "B.Tech" (declaration).
- Academic year / batch: 2020-24 (presentation slide 1), 2024-26 (presentation
  slide 2); the team's earlier Review 2 deck says "YEAR: 2026-2027", and the
  team's USNs (1JT23…) and the Review 4 deck use "Batch 2023-27".
- Student count: the title sheet has space for up to four students; the team
  has three.
- Department typo in the presentation template ("machinr").

## 2. Preliminary pages (Roman page numbers, e.g. vii, viii) [OFFICIAL]

| # | Page | Required content |
|---|---|---|
| 1 | Title sheet / cover | VTU identification; "A Project Report on"; project title (prominent, in quotation marks); partial-fulfilment statement; degree "Bachelor of Engineering in Artificial Intelligence and Machine Learning" [VERIFY]; student names + USNs (up to 4); guide (Dr./Prof. name, designation: Professor / Associate Professor / Assistant Professor); Department of AIML; Jyothy Institute of Technology |
| 2 | Certificate | Department heading; "Certificate"; title; student names + USNs; statement that the project was carried out by the students at JIT in partial fulfilment; institution and degree; academic year; guide signature + designation; HOD signature + designation (template: Dr. Madhu B R, Professor and Head, AIML); date fields; examiner section for two examiners (name, signature) |
| 3 | Declaration | Heading; student names + USNs; 8th-semester AIML identification; JIT and VTU; title; originality statement (not previously submitted for a degree/diploma elsewhere); academic year; signature space for every student; place and date |
| 4 | Acknowledgement | Formal thanks to JIT and VTU; the Principal (template: Dr. Gopalkrishnan) [VERIFY]; the HOD (Dr. Madhu B R); the project guide; the Project Coordinator (template: Dr. Soumya K N) [VERIFY]; AIML staff; family and friends; everyone who helped; ends with "Signature of Students". Do not credit help that did not happen |
| 5 | Abstract | Concise summary on **one page**; Times New Roman 12 pt; justified; 1.5 line spacing |
| 6 | Table of Contents | Chapters, sections, page numbers |
| 7 | List of Figures | Columns: Figure Number · Description of the Figure · Page Number |
| 8 | List of Tables | Columns: Table Number · Description of the Table · Page Number |
| 9 | Nomenclature Used | Table: abbreviation → expansion. The template's examples (LCD, GPRS, AT, GUI, USB, SIM, LF, CR, PHP, MySQL) belong to another project: **do not copy them**; list only terms our report uses |

## 3. Chapter structure (from the Content document) [OFFICIAL]

```
Chapter 1  Introduction
           Introduction
Chapter 2  Literature Survey
           Literature Survey
Chapter 3  Objective and Methodology
           Objective
           Methodology
Chapter 4  System Design
           System Architecture
           Use Case Diagram
           Data Flow Diagram
           Sequence Diagram
           Algorithms Used
Chapter 5  Hardware and Software Requirement
           Hardware Requirement
           Software Requirement
Conclusion
References
```

**[VERIFY]** The template's sample List of Figures contains entries "from
Chapters 5 and 6", which suggests a Chapter 6 (often implementation / results)
exists in the full template, but the supplied content structure does not name
it. Do not invent it as mandatory; ask the guide whether an implementation /
results / testing chapter is expected (see questionnaire).

## 4. Formatting [OFFICIAL unless marked]

| Element | Rule |
|---|---|
| Chapter heading | Times New Roman 18 pt bold (style "TNR 18 B") |
| Main section heading | TNR 16 pt bold |
| Subsection heading | TNR 14 pt bold |
| Lower-level heading | TNR 12 pt bold |
| Body text | Times New Roman 12 pt, 1.5 line spacing, justified both sides, hyphenation off |
| Figure caption | "Fig. X.Y. Description" — TNR 12 pt, centred (sample: "Fig. 1.1. A sample figure / illustration.") |
| Table caption | "Table X.Y. Description" — TNR 12 pt, centred (sample: "Table 1.1. A sample table.") |
| Equations | Numbered "(X.Y)", number aligned separately from the equation; only where the content needs them |
| Styles | Apply the template's Word styles (the angle-bracketed labels are style names, not text) |
| Numbering | Chapter-based figure/table numbers (sample: 3.1, 4.1(a), 4.1(b), 4.2(a)…) |
| Page numbers | Roman for preliminary pages; [VERIFY] Arabic for chapters |
| Margins, binding, headers/footers, paper size | **[VERIFY]** not stated in the extracted specification |

The main report template's sample text (Word styles, Home/Insert tabs, sample
figure/table/equation) is formatting demonstration only — **never copy it**.

## 5. References [OFFICIAL examples; style VERIFY]

The template shows examples of journal papers, conference papers, books and
edited volumes, with: authors; title; journal/conference; volume and issue;
pages; month and year; conference location; publisher, edition, volume for
books. Some examples are duplicated (remove accidental duplicates). **[VERIFY]**
the exact citation style (the examples resemble IEEE-style numbered entries;
confirm before formatting). Every reference must be verified against the
original source; nothing may be invented.

## 6. Phase 2 Review 4 presentation [OFFICIAL, two-slide template]

- **Slide 1:** Department of AIML; "Project Presentation on"; project title;
  batch number; student names and USNs; guide name and designation; department
  and batch line; Jyothy Charitable Trust / JIT identification, address,
  AICTE approval, VTU affiliation; logo.
- **Slide 2 (Contents):** Abstract; Objective; Literature Survey; Proposed
  Methodology; Implementation and Result Analysis; Demonstration; References.
- Batch text in the template (2024-26 / 2020-24) **[VERIFY]**.

## 7. Global rules

1. Preserve the official structure and headings; flag (do not silently fix)
   discrepancies.
2. No invented functionality, datasets, results, references, people or
   institutional details.
3. Separate official requirements from recommendations.
4. Signatures, dates and certification text stay placeholders until provided.
