"""Drawing helpers for the report figures (see make_diagrams.py).

Every figure is 6.6 in wide so it fits the report's text block (A4, 1.25 in
left and 1 in right margin) at about 90 %, and every coordinate is in units
of 1 % of the figure width, so x and y have the same scale.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Polygon, Rectangle

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 7.5,
    "savefig.dpi": 300,
})

NAVY, INK, GREY = "#1F3864", "#1A1A1A", "#5B6472"
BLUE, TEAL, AMBER, ROSE, PALE, WHITE = "#E3ECF8", "#DDF0F1", "#FBEFD5", "#F8E1E1", "#F3F5F8", "#FFFFFF"
WIDTH_IN = 6.6


class Canvas:
    def __init__(self, height_in):
        self.fig = plt.figure(figsize=(WIDTH_IN, height_in))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.top = 100 * height_in / WIDTH_IN
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, self.top)
        self.ax.axis("off")

    def box(self, x, y, w, h, text="", fc=BLUE, ec=NAVY, fs=7.5, bold=False, lw=0.9, rounding=1.0,
            ls="-", tc=INK, valign="center", italic=False):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rounding}",
                                         fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
        if text:
            ty = {"center": y + h / 2, "top": y + h - 1.2}[valign]
            self.text(x + w / 2, ty, text, fs=fs, bold=bold, color=tc, va="center" if valign == "center" else "top",
                      italic=italic)
        return (x, y, w, h)

    def text(self, x, y, s, fs=7.5, ha="center", va="center", bold=False, color=INK, italic=False, bg=False, z=5):
        kw = dict(bbox=dict(fc="white", ec="none", pad=0.7)) if bg else {}
        self.ax.text(x, y, s, fontsize=fs, ha=ha, va=va, color=color, zorder=z, linespacing=1.15,
                     fontweight="bold" if bold else "normal", fontstyle="italic" if italic else "normal", **kw)

    def arrow(self, p1, p2, label=None, both=False, ls="-", color=INK, lab=None, lw=0.8, fs=6.3, ha="center", rad=0.0):
        self.ax.annotate("", xy=p2, xytext=p1, zorder=3, arrowprops=dict(
            arrowstyle="<|-|>" if both else "-|>", color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0,
            mutation_scale=7, connectionstyle=f"arc3,rad={rad}"))
        if label:
            lx, ly = lab or ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            self.text(lx, ly, label, fs=fs, bg=True, ha=ha, italic=True)

    def poly(self, pts, label=None, ls="-", color=INK, lab=None, lw=0.8, fs=6.3, both=False, ha="center"):
        xs, ys = [p[0] for p in pts[:-1]], [p[1] for p in pts[:-1]]
        if len(pts) > 2:
            self.ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=3, solid_capstyle="butt")
        self.arrow(pts[-2], pts[-1], both=both, ls=ls, color=color, lw=lw)
        if label:
            lx, ly = lab or ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
            self.text(lx, ly, label, fs=fs, bg=True, ha=ha, italic=True)

    def ellipse(self, cx, cy, w, h, text="", fc=BLUE, ec=NAVY, fs=7, lw=0.9):
        self.ax.add_patch(Ellipse((cx, cy), w, h, fc=fc, ec=ec, lw=lw, zorder=2))
        if text:
            self.text(cx, cy, text, fs=fs)

    def circle(self, cx, cy, r, text="", fc=TEAL, ec=NAVY, fs=7, lw=0.9):
        self.ax.add_patch(Circle((cx, cy), r, fc=fc, ec=ec, lw=lw, zorder=2))
        if text:
            self.text(cx, cy, text, fs=fs)

    def diamond(self, cx, cy, w, h, text, fc=AMBER, fs=6.8):
        self.ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)],
                                  closed=True, fc=fc, ec=NAVY, lw=0.9, zorder=2))
        self.text(cx, cy, text, fs=fs)

    def store(self, x, y, w, h, text, fc=PALE, fs=7):
        """Data store: open-ended rectangle (two parallel lines)."""
        self.ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="none", zorder=2))
        self.ax.plot([x, x + w], [y, y], color=NAVY, lw=1.1, zorder=3)
        self.ax.plot([x, x + w], [y + h, y + h], color=NAVY, lw=1.1, zorder=3)
        self.ax.plot([x, x], [y, y + h], color=NAVY, lw=0.9, zorder=3)
        self.text(x + w / 2, y + h / 2, text, fs=fs)

    def actor(self, cx, cy, label, fs=7.5):
        """Stick figure with its head centred above (cx, cy)."""
        self.ax.add_patch(Circle((cx, cy + 6.6), 1.6, fc=WHITE, ec=INK, lw=0.9, zorder=3))
        for xs, ys in (([cx, cx], [cy + 5, cy + 0.6]), ([cx - 2.6, cx + 2.6], [cy + 3.6, cy + 3.6]),
                       ([cx, cx - 2.2], [cy + 0.6, cy - 2.4]), ([cx, cx + 2.2], [cy + 0.6, cy - 2.4])):
            self.ax.plot(xs, ys, color=INK, lw=0.9, zorder=3)
        self.text(cx, cy - 5.2, label, fs=fs)

    def save(self, path):
        self.fig.savefig(path, facecolor="white")
        plt.close(self.fig)


def sequence(path, parties, steps, height_in=None, title_h=6.4, step=5.3, first_gap=2.0, note=None):
    """UML-style sequence diagram.

    parties: lifeline headings; steps: (src, dst, text, kind) with kind in
    "call", "ret" (dashed) or "self" (src == dst). Messages are numbered.
    Without height_in, the height is just enough for the messages.
    """
    if height_in is None:
        units = 1.2 + title_h + first_gap + sum(step + text.count("\n") * 2.4 for _, _, text, _ in steps)
        height_in = (units + (5.5 if note else 3.5)) * WIDTH_IN / 100
    c = Canvas(height_in)
    n = len(parties)
    left, right = 100 / n / 2, 100 - 100 / n / 2
    xs = [left + i * (right - left) / (n - 1) for i in range(n)] if n > 1 else [50]
    head_w = min(100 / n - 1.6, 17)
    ytop = c.top - 1.2
    for x, name in zip(xs, parties):
        c.box(x - head_w / 2, ytop - title_h, head_w, title_h, name, fc=BLUE, fs=6.8, bold=True)
        c.ax.plot([x, x], [ytop - title_h, 3.6 if note else 1.5], color=GREY, lw=0.7, ls=(0, (4, 3)), zorder=1)
    y = ytop - title_h - first_gap
    for i, (a, b, text, kind) in enumerate(steps, 1):
        label = f"{i}. {text}"
        lines = label.count("\n") + 1
        y -= step + (lines - 1) * 2.4
        if kind == "self":
            x = xs[a]
            d = -1 if x > 70 else 1          # loop and label point inwards from the right-hand lifelines
            c.ax.plot([x, x + 3.4 * d, x + 3.4 * d], [y + 1.2, y + 1.2, y - 1.6], color=INK, lw=0.8, zorder=3)
            c.arrow((x + 3.4 * d, y - 1.6), (x + 0.3 * d, y - 1.6))
            c.text(x + 4.4 * d, y - 0.2, label, fs=6.3, ha="left" if d > 0 else "right", bg=True)
        else:
            x1, x2 = xs[a], xs[b]
            c.arrow((x1, y), (x2, y), ls="--" if kind == "ret" else "-")
            c.text((x1 + x2) / 2, y + 1.3 + (lines - 1) * 1.2, label, fs=6.3, va="bottom", bg=True)
    if note:
        c.text(50, 1.5, note, fs=6.3, italic=True, color=GREY)
    c.save(path)
    return y
