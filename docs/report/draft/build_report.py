"""Builds the project report (Word) from the chapter files in content/.

    python -I docs/report/draft/build_report.py

Needs python-docx and docxcompose. The front sheets are the department's own
template (template/0_front_sheets.docx: title page, certificate, declaration,
acknowledgement) and the abstract template (5_abstract.docx), filled in from
the constants below; everything after them uses the styles of the college report template
(template/7_report_styles.docx: CHNO, CHTITLE, HEAD1-3, MAINPARA, FIGLEGEND,
TABLE*). Writes output/Project_Report_Draft.docx. Word fills the contents and
the figure and table lists when the fields are updated (it asks on opening).

Chapter-file syntax, one block per blank-line-separated paragraph:
    # 1 | Introduction            chapter (CHNO + CHTITLE); "# - | Title" unnumbered,
                                  "# A | Title" appendix
    ## 1.1 Heading / ### / ####   HEAD1 / HEAD2 / HEAD3
    - item, 1. item               bullet and numbered lists
    ::table 6.1 | Caption         followed by a pipe table
    ::figure path | 4.1 | Caption | width-in-inches
    ::equation name | 4.1         docs/report_assets/equations/<name>.png
    ::algorithm 4.1 | Caption     followed by a ``` fenced block (::listing E.1 | ... likewise)
    ::toc, ::lof, ::lot, ::references, ::pagebreak, ::frontend
Inline: **bold**, *italic*, `code`, [@K8] or [@K8, K26] (numbered in order of
first citation, IEEE style, from docs/report_prep/VERIFIED_REFERENCES.md).
"""

import copy
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docxcompose.composer import Composer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TEMPLATE = os.path.join(HERE, "template")
CONTENT = os.path.join(HERE, "content")
OUT = os.path.join(HERE, "output", "Project_Report_Draft.docx")
REFS = os.path.join(ROOT, "docs", "report_prep", "VERIFIED_REFERENCES.md")
EQUATIONS = os.path.join(ROOT, "docs", "report_assets", "equations")

TITLE = ("Intrusion Detection System using Hybrid CNN-LSTM with Explainable AI (SHAP) "
         "for Indian Network Databases")
STUDENTS = [("Maanya B S", "1JT23AI030"), ("Ruthwik Sai Ganesh", "1JT23AI042"), ("Varshini D N", "1JT23AI060")]
GUIDE = "Dr. Madhu B R"
GUIDE_DESIGNATION = "Professor and Head"
RUNNING_TITLE = "Intrusion Detection System using Hybrid CNN-LSTM with Explainable AI"
KEYWORDS = ("intrusion detection, intrusion prevention, CNN-LSTM, deep learning, explainable AI, SHAP, "
            "CICIDS2017, MU-IoT, live packet capture.")
TEXT_WIDTH_IN = 6.0     # A4 minus the template's 1.25 in left and 1 in right margins

INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|\[@[^\]]+\])")


# ---------------------------------------------------------------- references

def load_references():
    refs = {}
    with open(REFS, encoding="utf8") as f:
        for line in f:
            m = re.match(r"^(K\d+)\. (.+)$", line.strip())
            if m:
                text = re.sub(r"\s*\[(pages|page)[^\]]*\]\s*$", "", m.group(2))
                text = re.sub(r"\s*\(The CICFlowMeter reference\.\)\s*$", "", text)
                refs[m.group(1)] = text
    return refs


def citation_order(files):
    order = []
    for path in files:
        with open(path, encoding="utf8") as f:
            for group in re.findall(r"\[@([^\]]+)\]", f.read()):
                for key in (k.strip().lstrip("@") for k in group.split(",")):
                    if key not in order:
                        order.append(key)
    return {key: i + 1 for i, key in enumerate(order)}


# ---------------------------------------------------------------- low-level helpers

def text_runs(p):
    return [r for r in p.runs if not r._r.xpath(".//w:drawing|.//w:pict|.//w:object")]


def set_text(p, text):
    """Replaces a paragraph's text, keeping the formatting of its first text run."""
    runs = text_runs(p)
    if not runs:
        p.add_run(text)
        return
    keep = next((r for r in runs if r.text.strip()), runs[0])
    keep.text = text
    for r in runs:
        if r is not keep:
            r._r.getparent().remove(r._r)


def delete(p):
    p._p.getparent().remove(p._p)


def insert_after(p, text):
    new = copy.deepcopy(p._p)
    p._p.addnext(new)
    from docx.text.paragraph import Paragraph
    para = Paragraph(new, p._parent)
    set_text(para, text)
    return para


def add_field(paragraph, instruction, placeholder=""):
    run = paragraph.add_run()
    for tag, attrs in (("w:fldChar", {"w:fldCharType": "begin"}),):
        el = OxmlElement(tag)
        for k, v in attrs.items():
            el.set(qn(k), v)
        run._r.append(el)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    run._r.append(instr)
    if placeholder:
        sep = OxmlElement("w:fldChar")
        sep.set(qn("w:fldCharType"), "separate")
        run._r.append(sep)
        t = OxmlElement("w:t")
        t.text = placeholder
        run._r.append(t)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(end)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def add_inline(p, text, cites, size=None, bold=False, italic=False):
    for part in INLINE.split(text):
        if not part:
            continue
        b, i, mono = bold, italic, False
        if part.startswith("**") and part.endswith("**"):
            part, b = part[2:-2], True
        elif part.startswith("`") and part.endswith("`"):
            part, mono = part[1:-1], True
        elif part.startswith("[@"):
            keys = [k.strip().lstrip("@") for k in part[2:-1].split(",")]
            part = ", ".join(f"[{cites[k]}]" for k in keys)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, i = part[1:-1], True
        run = p.add_run(part)
        run.bold, run.italic = b or None, i or None
        if mono:
            run.font.name = "Courier New"
            run.font.size = Pt(10.5 if size is None else size - 1)
        elif size:
            run.font.size = Pt(size)
    return p


# ---------------------------------------------------------------- front pages

def _runs(p, changes):
    """Sets the text of runs by index ({index: text}); other runs keep their text and formatting."""
    runs = p.runs
    for i, text in changes.items():
        runs[i].text = text


def fill_front_sheets(d):
    """The department's front sheets (template/0_front_sheets.docx): title page, certificate,
    declaration and acknowledgement. Placeholders are replaced run by run, so the template's
    fonts, colours, page borders and logos stay as they are. Department wording is kept."""
    ps = d.paragraphs
    (n1, u1), (n2, u2), (n3, u3) = STUDENTS

    # title page
    _runs(ps[4], {0: TITLE})
    for p, (name, usn) in zip((ps[10], ps[11], ps[12]), STUDENTS):
        _runs(p, {0: usn, 2: name})
        for r in p.runs[3:]:
            r._r.getparent().remove(r._r)
    _runs(ps[14], {7: "\n" + GUIDE, 8: "", 9: "", 10: "", 11: "", 12: ""})
    _runs(ps[15], {0: GUIDE_DESIGNATION, 1: "", 2: "", 3: "\nDept of "})

    # certificate
    _runs(ps[26], {1: TITLE, 3: n1, 4: f" [{u1}], ", 5: n2, 6: " ", 7: f"[{u2}", 8: "] and ", 9: n3, 10: " ",
                   11: f"[{u3}], ", 12: "", 13: "", 14: "", 15: ""})
    _runs(ps[34], {0: GUIDE, 1: "", 12: GUIDE_DESIGNATION})

    # declaration
    _runs(ps[47], {22: TITLE, 25: GUIDE, 26: "", 27: "", 28: ", ", 29: GUIDE_DESIGNATION, 30: "", 31: "",
                   32: ", Department of "})

    # acknowledgement (no pronouns for the people named)
    _runs(ps[56], {5: "for providing us an opportunity and for the valuable support."})
    _runs(ps[58], {1: GUIDE, 2: "", 3: "", 4: "", 5: "", 6: "", 8: GUIDE_DESIGNATION,
                   9: ", Department of ", 12: "for the keen interest and boundless encouragement in completing this work."})
    insert_after(ps[59], "We thank the University of New Brunswick and Manipur University for the CICIDS2017 and "
                         "MU-IoT datasets, and the owner of the network used for the live test for permission to "
                         "use it.")

    # name tables of the declaration and the acknowledgement: three students, so the fourth row goes
    for table in d.tables:
        name_col = 1 if len(table.columns) == 3 else 0
        for row, (name, usn) in zip(table.rows, STUDENTS):
            set_text(row.cells[name_col].paragraphs[0], name)
            set_text(row.cells[name_col + 1].paragraphs[0], f"[{usn}]")
            row.cells[name_col].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        last = table.rows[3]
        if name_col == 1 and last.cells[0].text.strip():
            continue
        last._tr.getparent().remove(last._tr)

    # the template ends with an empty page in its own section: drop everything after the
    # acknowledgement's section break (the body's final properties are not merged anyway)
    body = d.element.body
    ack_end = ps[63]._p
    remove = False
    for el in list(body):
        if remove and el.tag != qn("w:sectPr"):
            body.remove(el)
        if el is ack_end:
            remove = True


def fill_abstract(d, paragraphs):
    first = d.paragraphs[1]
    set_text(first, paragraphs[0])
    last = first
    for text in paragraphs[1:]:
        last = insert_after(last, text)


def page_break(d):
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _style_value(style, get):
    while style is not None:
        v = get(style)
        if v is not None:
            return v
        style = style.base_style
    return None


def _doc_defaults(d):
    """Line spacing, spacing after/before (twips) and font size of the docDefaults."""
    el = d.styles.element.find(qn("w:docDefaults"))
    out = {"line": None, "after": None, "before": None, "size": None, "font": None}
    if el is None:
        return out
    sp = el.find(".//" + qn("w:pPrDefault") + "//" + qn("w:spacing"))
    if sp is not None:
        if sp.get(qn("w:line")):
            out["line"] = int(sp.get(qn("w:line"))) / 240
        for k in ("after", "before"):
            if sp.get(qn("w:" + k)):
                out[k] = Pt(int(sp.get(qn("w:" + k))) / 20)
    sz = el.find(".//" + qn("w:rPrDefault") + "//" + qn("w:sz"))
    if sz is not None:
        out["size"] = Pt(int(sz.get(qn("w:val"))) / 2)
    return out


def freeze_formatting(d):
    """Writes each paragraph's and run's formatting from its own document's styles as
    direct formatting, so that merging into the report (whose Normal style has 1.5 line
    spacing) does not change the college front pages' layout."""
    defaults = _doc_defaults(d)
    paragraphs = list(d.paragraphs)
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    for p in paragraphs:
        style, pf = p.style, p.paragraph_format
        if pf.line_spacing is None:
            pf.line_spacing = _style_value(style, lambda s: s.paragraph_format.line_spacing) or defaults["line"] or 1.0
        if pf.space_after is None:
            pf.space_after = _style_value(style, lambda s: s.paragraph_format.space_after) or defaults["after"] or Pt(0)
        if pf.space_before is None:
            pf.space_before = _style_value(style, lambda s: s.paragraph_format.space_before) or defaults["before"] or Pt(0)
        if pf.alignment is None:
            align = _style_value(style, lambda s: s.paragraph_format.alignment)
            if align is not None:
                pf.alignment = align
        for r in p.runs:
            if r.font.size is None:
                r.font.size = _style_value(style, lambda s: s.font.size) or defaults["size"] or Pt(12)
            if r.font.name is None:
                r.font.name = _style_value(style, lambda s: s.font.name) or "Times New Roman"
            if r.font.bold is None:
                b = _style_value(style, lambda s: s.font.bold)
                if b:
                    r.font.bold = True
            rpr = r._r.get_or_add_rPr()          # the report's Normal style widens letter spacing
            if rpr.find(qn("w:spacing")) is None:
                sp = OxmlElement("w:spacing")
                sp.set(qn("w:val"), "0")
                rpr.append(sp)
        # the report's Heading styles are numbered; the front pages' headings must not be
        p._p.get_or_add_pPr()
        if p.style.name.startswith("Heading") and p._p.pPr.find(qn("w:numPr")) is None:
            num = OxmlElement("w:numPr")
            for tag in ("w:ilvl", "w:numId"):
                el = OxmlElement(tag)
                el.set(qn("w:val"), "0")
                num.append(el)
            p._p.pPr.insert(0, num) if p._p.pPr.find(qn("w:pStyle")) is None else \
                p._p.pPr.find(qn("w:pStyle")).addnext(num)


def unlink_header_footer(sections):
    """Gives each front-sheet section its own new, empty header and footer: no running title or page
    number. Their old references are dropped, not cleared: the parts may be shared with the report."""
    for section in sections:
        sectPr = section._sectPr
        for tag in ("w:headerReference", "w:footerReference"):
            for ref in sectPr.findall(qn(tag)):
                sectPr.remove(ref)
        for part in (section.header, section.footer):
            part.is_linked_to_previous = False           # creates a fresh, empty part
            for p in part.paragraphs:
                p.style = "Normal"                       # the Header style draws a rule line


def format_abstract(d):
    """Template rule for the abstract: Times New Roman 12, justified, 1.5 line spacing."""
    for p in d.paragraphs[1:]:
        if not p.text.strip():
            continue
        pf = p.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.line_spacing, pf.space_after, pf.space_before = 1.5, Pt(6), Pt(0)
        for r in p.runs:
            r.font.name, r.font.size = "Times New Roman", Pt(12)
        if p.text.startswith("Keywords:"):
            set_text(p, "")
            p.add_run("Keywords: ").bold = True
            p.add_run(KEYWORDS)
            for r in p.runs:
                r.font.name, r.font.size = "Times New Roman", Pt(12)


def column_widths(rows, size_pt):
    """Column widths in inches: each column at least as wide as its longest word at this font
    size, the rest of the text width shared in proportion to the columns' text length."""
    shown = lambda c: re.sub(r"[*`]", "", re.sub(r"\[@[^\]]+\]", lambda m: "[00], " * m.group(0).count("K"), c))
    n = len(rows[0])
    char_in = size_pt * 0.62 / 72                       # width of a bold Times character, with margin
    floor = [max(len(w) for r in rows for w in (shown(r[j]).split() or [""])) * char_in + 0.3 for j in range(n)]
    weight = [min(38, max(len(shown(r[j])) for r in rows)) + 3 for j in range(n)]
    widths, fixed = list(floor), set()
    for _ in range(n):                                  # columns held at their floor leave the rest to share
        free = [j for j in range(n) if j not in fixed]
        room = TEXT_WIDTH_IN - sum(floor[j] for j in fixed)
        share = {j: room * weight[j] / sum(weight[k] for k in free) for j in free}
        below = [j for j in free if share[j] < floor[j]]
        if not below:
            for j in free:
                widths[j] = share[j]
            break
        fixed.update(below)
    return widths


def add_toc_styles(styles):
    """Compact styles for the contents, figure and table lists (Word's 'toc 1'-'toc 3'):
    single spacing with a dotted right tab, instead of the body text's 1.5 lines."""
    from docx.oxml import parse_xml
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    tab = int(TEXT_WIDTH_IN * 1440) - 10
    # level 4 (no indent, not bold) is used for the figure and table lists
    for level, indent, bold, before in ((1, 0, True, 80), (2, 280, False, 20), (3, 560, False, 0), (4, 0, False, 30)):
        sid = f"TOC{level}"
        old = styles.element.find(f'{qn("w:style")}[@{qn("w:styleId")}="{sid}"]')
        if old is not None:
            styles.element.remove(old)
        styles.element.append(parse_xml(
            f'<w:style {ns} w:type="paragraph" w:styleId="{sid}"><w:name w:val="toc {level}"/>'
            f'<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/>'
            f'<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{tab}"/></w:tabs>'
            f'<w:spacing w:before="{before}" w:after="20" w:line="264" w:lineRule="auto"/>'
            f'<w:ind w:left="{indent}"/><w:jc w:val="left"/></w:pPr>'
            f'<w:rPr>{"<w:b/>" if bold else ""}<w:spacing w:val="0"/></w:rPr></w:style>'))


def strip_trailing_empty(d):
    body = d.element.body
    for el in reversed(list(body)):
        if el.tag == qn("w:p") and not "".join(el.itertext()).strip() and not el.xpath(".//w:drawing|.//w:pict"):
            body.remove(el)
        elif el.tag == qn("w:sectPr"):
            continue
        else:
            break


# ---------------------------------------------------------------- report body

class Builder:
    def __init__(self, doc, cites, refs):
        self.doc, self.cites, self.refs = doc, cites, refs
        self.counts = {"figures": 0, "tables": 0, "equations": 0, "words": 0}
        styles = doc.styles
        # The template's heading styles carry automatic list numbering; the chapter files
        # number headings themselves (and some headings are unnumbered), so it is removed.
        for sid in ("CHNO", "CHTITLE", "HEAD1", "HEAD2", "HEAD3"):
            el = styles.element.find(f'{qn("w:style")}[@{qn("w:styleId")}="{sid}"]')
            if el is not None:
                for num in el.findall(".//" + qn("w:numPr")):
                    num.getparent().remove(num)
        add_toc_styles(styles)
        if "TABLEGEND" not in [s.name for s in styles]:
            st = styles.add_style("TABLEGEND", 1)
            st.base_style = styles["FIGLEGEND"]
            st.paragraph_format.keep_with_next = True
            st.paragraph_format.space_before = Pt(6)

    def para(self, text, style="MAINPARA", align=None):
        p = self.doc.add_paragraph(style=style)
        if align is not None:
            p.alignment = align
        add_inline(p, text, self.cites)
        self.counts["words"] += len(text.split())
        return p

    def chapter(self, num, title):
        if num == "-":
            p = self.doc.add_paragraph(style="CHTITLE")
            p.paragraph_format.page_break_before = True
            p.add_run(title)
            add_field(p, f'TC "{title}" \\l 1')
            return
        label = f"Appendix {num}" if num.isalpha() else f"Chapter {num}"
        p = self.doc.add_paragraph(style="CHNO")
        p.add_run(label)
        add_field(p, f'TC "{label}   {title}" \\l 1')
        self.doc.add_paragraph(title, style="CHTITLE")

    def heading(self, level, text):
        self.doc.add_paragraph(text, style={2: "HEAD1", 3: "HEAD2", 4: "HEAD3"}[level])

    def listing(self, items, numbered):
        for i, item in enumerate(items, 1):
            p = self.doc.add_paragraph(style="MAINPARA")
            pf = p.paragraph_format
            pf.left_indent, pf.first_line_indent = Inches(0.35), Inches(-0.25)
            pf.space_after = Pt(3)
            pf.tab_stops.add_tab_stop(Inches(0.35))
            add_inline(p, (f"{i}.\t" if numbered else "•\t") + item, self.cites)
            self.counts["words"] += len(item.split())

    def caption(self, kind, number, text):
        style = "FIGLEGEND" if kind == "Fig." else "TABLEGEND"
        p = self.doc.add_paragraph(style=style)
        r = p.add_run(f"{kind} {number}. ")
        r.bold = True
        add_inline(p, text, self.cites)
        return p

    def table(self, number, caption, lines):
        rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
        aligns = None
        if len(rows) > 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in rows[1]):
            aligns = ["right" if c.endswith(":") and not c.startswith(":") else
                      "left" if c.startswith(":") and not c.endswith(":") else None for c in rows[1]]
            rows = [rows[0]] + rows[2:]
        n = len(rows[0])
        if number != "-":                               # "::table - | ..." is an uncaptioned table
            self.caption("Table", number, caption)
        t = self.doc.add_table(rows=len(rows), cols=n)
        t.style = self.doc.styles["Table Grid"]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        size = 10 if number == "-" else 11 if n <= 4 else 10 if n <= 6 else 9
        widths = column_widths(rows, size)
        for j, col in enumerate(t.columns):                # Word lays the table out from its grid
            col.width = Inches(widths[j])
        for i, row in enumerate(rows):
            for j in range(n):
                cell = t.cell(i, j)
                cell.width = Inches(widths[j])
                p = cell.paragraphs[0]
                left = j == 0 or (aligns and aligns[j] == "left") or len(row[j]) > 28
                p.style = self.doc.styles["TABLELt" if left else "TABLECt"]
                p.paragraph_format.first_line_indent = Inches(0)
                # the template's table styles keep every row with the next, which pushes
                # whole tables onto a new page; only the header row is kept with the body
                p.paragraph_format.keep_with_next = i == 0
                add_inline(p, row[j] if j < len(row) else "", self.cites, size=size, bold=(i == 0))
                if i == 0:
                    shade(cell, "D9E2F3")
        for row in t.rows:                               # a row never breaks across pages
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        trPr = t.rows[0]._tr.get_or_add_trPr()
        hdr = OxmlElement("w:tblHeader")
        hdr.set(qn("w:val"), "true")
        trPr.append(hdr)
        self.doc.add_paragraph(style="MAINPARA").paragraph_format.space_after = Pt(2)
        self.counts["tables"] += 1

    def figure(self, path, number, caption, width):
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            raise FileNotFoundError(full)
        p = self.doc.add_paragraph(style="MAINPARA")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.first_line_indent = Inches(0)
        p.add_run().add_picture(full, width=Inches(float(width)))
        self.caption("Fig.", number, caption)
        self.counts["figures"] += 1

    def equation(self, name, number):
        full = os.path.join(EQUATIONS, name + ".png")
        if not os.path.exists(full):
            raise FileNotFoundError(full)
        from PIL import Image
        with Image.open(full) as im:
            w_px, h_px = im.size
        p = self.doc.add_paragraph(style="MAINPARA")
        pf = p.paragraph_format
        pf.tab_stops.add_tab_stop(Inches(TEXT_WIDTH_IN / 2), WD_TAB_ALIGNMENT.CENTER)
        pf.tab_stops.add_tab_stop(Inches(TEXT_WIDTH_IN), WD_TAB_ALIGNMENT.RIGHT)
        pf.space_before, pf.space_after = Pt(4), Pt(6)
        width_in = min(w_px / 300, TEXT_WIDTH_IN - 0.9)
        height_pt = h_px / w_px * width_in * 72
        p.add_run("\t")
        p.add_run().add_picture(full, width=Inches(width_in))
        num = p.add_run(f"\t({number})")
        # raise the number to the middle of the equation (w:position is in half-points)
        pos = OxmlElement("w:position")
        pos.set(qn("w:val"), str(max(0, int(height_pt - 9))))
        num._r.get_or_add_rPr().append(pos)
        self.counts["equations"] += 1

    def code(self, caption, lines, label="Algorithm"):
        if caption:
            num, text = [s.strip() for s in caption.split("|", 1)]
            p = self.doc.add_paragraph(style="MAINPARA")
            p.paragraph_format.keep_with_next = True
            r = p.add_run(f"{label} {num}. ")
            r.bold = True
            p.add_run(text).bold = True
        t = self.doc.add_table(rows=1, cols=1)
        t.style = self.doc.styles["Table Grid"]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.cell(0, 0)
        shade(cell, "F2F2F2")
        first = True
        for ln in lines:
            p = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            p.style = self.doc.styles["TABLELt"]
            pf = p.paragraph_format
            pf.space_after, pf.space_before, pf.line_spacing = Pt(0), Pt(0), 1.0
            r = p.add_run(ln.rstrip("\n") or " ")
            r.font.name, r.font.size = "Courier New", Pt(8.5)
        self.doc.add_paragraph(style="MAINPARA").paragraph_format.space_after = Pt(2)

    def special_heading(self, text):
        p = self.doc.add_paragraph(style="CHTITLE")
        p.paragraph_format.page_break_before = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(text)

    def field_page(self, title, instruction):
        self.special_heading(title)
        p = self.doc.add_paragraph(style="MAINPARA")
        add_field(p, instruction, "Update this field (right-click, Update Field) to fill this list.")

    def references(self):
        for key, n in sorted(self.cites.items(), key=lambda kv: kv[1]):
            if key not in self.refs:
                raise KeyError(f"citation {key} is not in {REFS}")
            p = self.doc.add_paragraph(style="MAINPARA")
            pf = p.paragraph_format
            pf.left_indent, pf.first_line_indent = Inches(0.45), Inches(-0.45)
            pf.tab_stops.add_tab_stop(Inches(0.45))
            pf.space_after = Pt(4)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline(p, f"[{n}]\t" + self.refs[key], {})

    def render(self, path):
        with open(path, encoding="utf8") as f:
            lines = f.read().splitlines()
        i = 0
        while i < len(lines):
            ln = lines[i]
            s = ln.strip()
            if not s or s.startswith("<!--"):
                i += 1
                continue
            if s.startswith("::"):
                cmd, _, arg = s[2:].partition(" ")
                if cmd == "table":
                    num, cap = [x.strip() for x in arg.split("|", 1)]
                    j = i + 1
                    block = []
                    while j < len(lines) and lines[j].strip().startswith("|"):
                        block.append(lines[j])
                        j += 1
                    self.table(num, cap, block)
                    i = j
                    continue
                if cmd == "figure":
                    path_, num, cap, width = [x.strip() for x in arg.split("|")]
                    self.figure(path_, num, cap, width)
                elif cmd == "equation":
                    name, num = [x.strip() for x in arg.split("|")]
                    self.equation(name, num)
                elif cmd in ("algorithm", "listing"):
                    j = i + 2                          # next line must open a ``` fence
                    block = []
                    while not lines[j].strip().startswith("```"):
                        block.append(lines[j])
                        j += 1
                    self.code(arg, block, label=cmd.capitalize())
                    i = j + 1
                    continue
                elif cmd == "toc":             # TOC \t takes style names (HEAD_1), not ids (HEAD1)
                    self.field_page("TABLE OF CONTENTS", 'TOC \\f \\h \\z \\t "HEAD_1,2,HEAD_2,3"')
                elif cmd == "lof":
                    self.field_page("LIST OF FIGURES", 'TOC \\h \\z \\t "FIG_LEGEND,4"')
                elif cmd == "lot":
                    self.field_page("LIST OF TABLES", 'TOC \\h \\z \\t "TABLEGEND,4"')
                elif cmd == "heading":
                    self.special_heading(arg)
                elif cmd == "references":
                    self.references()
                elif cmd == "pagebreak":
                    page_break(self.doc)
                elif cmd == "frontend":
                    end_front_section(self.doc)
                else:
                    raise ValueError(f"{path}: unknown directive {s}")
                i += 1
                continue
            if s.startswith("```"):
                j = i + 1
                block = []
                while not lines[j].strip().startswith("```"):
                    block.append(lines[j])
                    j += 1
                self.code(None, block)
                i = j + 1
                continue
            m = re.match(r"^(#{1,4}) (.+)$", s)
            if m:
                level, text = len(m.group(1)), m.group(2)
                if level == 1:
                    num, title = [x.strip() for x in text.split("|", 1)]
                    self.chapter(num, title)
                else:
                    self.heading(level, text)
                i += 1
                continue
            if re.match(r"^(- |\d+\. )", s):
                numbered = bool(re.match(r"^\d+\. ", s))
                items = []
                while i < len(lines) and lines[i].strip():
                    t = lines[i].strip()
                    if re.match(r"^(- |\d+\. )", t):
                        items.append(re.sub(r"^(- |\d+\. )", "", t))
                    else:
                        items[-1] += " " + t
                    i += 1
                self.listing(items, numbered)
                continue
            block = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("::", "#", "```", "|")):
                block.append(lines[i].strip())
                i += 1
            self.para(" ".join(block))


# ---------------------------------------------------------------- sections

def _page_numbers(sectPr, fmt, start=None):
    for old in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(old)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))
    cols = sectPr.find(qn("w:cols"))
    (cols.addprevious if cols is not None else sectPr.append)(pg)


def end_front_section(doc):
    """Ends the preliminary section (abstract to nomenclature): Roman page numbers from i.
    The front sheets before it are their own, unnumbered sections."""
    final = doc.element.body.find(qn("w:sectPr"))
    sect = copy.deepcopy(final)
    _page_numbers(sect, "lowerRoman", 1)
    for tp in sect.findall(qn("w:titlePg")):
        sect.remove(tp)
    p = doc.add_paragraph()
    p._p.get_or_add_pPr().append(sect)


def finish_sections(doc):
    final = doc.element.body.find(qn("w:sectPr"))
    _page_numbers(final, "decimal", 1)
    for tp in final.findall(qn("w:titlePg")):
        final.remove(tp)
    settings = doc.settings.element
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    settings.append(upd)


# ---------------------------------------------------------------- main

def main():
    files = sorted(os.path.join(CONTENT, f) for f in os.listdir(CONTENT) if f.endswith(".md"))
    abstract_file = next(f for f in files if os.path.basename(f).startswith("00_abstract"))
    body_files = [f for f in files if f != abstract_file]
    cites = citation_order(body_files)
    refs = load_references()
    missing = [k for k in cites if k not in refs]
    if missing:
        sys.exit(f"Cited but not in VERIFIED_REFERENCES.md: {missing}")

    with open(abstract_file, encoding="utf8") as f:
        abstract = [p.strip().replace("\n", " ") for p in f.read().split("\n\n") if p.strip()
                    and not p.strip().startswith("<!--")]

    sheets = Document(os.path.join(TEMPLATE, "0_front_sheets.docx"))   # ends with its own section break
    fill_front_sheets(sheets)
    freeze_formatting(sheets)
    front = [sheets]
    d = Document(os.path.join(TEMPLATE, "5_abstract.docx"))
    fill_abstract(d, abstract)
    freeze_formatting(d)
    format_abstract(d)
    strip_trailing_empty(d)
    front.append(d)

    master = Document(os.path.join(TEMPLATE, "7_report_styles.docx"))
    body = master.element.body
    for el in list(body):
        if el.tag != qn("w:sectPr"):
            body.remove(el)
    front_sections = sum(1 for p in sheets.paragraphs if p._p.find(".//" + qn("w:sectPr")) is not None)
    composer = Composer(master)
    for d in front:
        composer.append(d)
    doc = composer.doc
    unlink_header_footer(doc.sections[:front_sections])

    b = Builder(doc, cites, refs)
    for path in body_files:
        b.render(path)
    finish_sections(doc)
    for section in doc.sections:
        for p in section.header.paragraphs:
            if "Your Project Title" in p.text:
                set_text(p, p.text.replace("<Your Project Title>", RUNNING_TITLE))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    unused = [k for k in refs if k not in cites]
    print(f"wrote {OUT}")
    print(f"body words ~{b.counts['words']:,}; figures {b.counts['figures']}; tables {b.counts['tables']}; "
          f"equations {b.counts['equations']}; references cited {len(cites)} (not cited: {unused or 'none'})")


if __name__ == "__main__":
    main()
