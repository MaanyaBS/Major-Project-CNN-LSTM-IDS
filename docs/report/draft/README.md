# Project Report Draft

The project report, built as a Word document on the college templates.

| Path | Contents |
|---|---|
| `output/Project_Report_Draft.docx`, `.pdf` | The built report (open the .docx in Word and accept "update fields") |
| `content/*.md` | The text, one file per chapter; edit these, not the .docx |
| `template/` | The college templates: front pages (1-5) and report styles (7, converted from `7.REPORT.doc`) |
| `build_report.py` | Builds the .docx from `content/`, the templates and `docs/report_prep/VERIFIED_REFERENCES.md` |
| `../../report_assets/` | Figures, equations, screenshots, and the scripts that draw them |

## Rebuilding

```
pip install python-docx docxcompose
python docs/report_assets/diagrams/make_diagrams.py     # only if a diagram changed
python docs/report_assets/diagrams/make_equations.py    # only if an equation changed
python docs/report/draft/build_report.py
```

Then open the .docx in Word and update fields (Ctrl+A, F9) to refresh the
contents, the figure and table lists, and their page numbers.

## Conventions

- Citations are written `[@K8]` with the keys of `VERIFIED_REFERENCES.md`;
  the builder numbers them in order of first citation (IEEE).
- Figures, tables and equations are numbered by chapter in the text
  (`::figure ... | 4.1 | ...`); keep the numbers in order when adding one.
- Every number in the report comes from a file in `model/results/` or a team
  report; do not add figures that are not in the repository.
- Marked *[To confirm ...]* in the text: open questions for the team.
