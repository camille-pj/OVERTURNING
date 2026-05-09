"""
Girder Overturning Check — Tkinter UI
=====================================
Same calculation as girder_overturning_check.py, in a modern desktop form
with two embedded figures so the moment balance is visual, not just numeric:

    1. Free-body schematic — beam + pin + downward load arrows scaled by
       magnitude, with the moment arms about the pin annotated.
    2. Moments bar chart — stabilizing vs overturning vs the required
       capacity (overturning x SF_required), so PASS/FAIL is obvious at
       a glance.

Theming uses Sun Valley (`sv_ttk`) for a Windows 11 fluent look; if not
installed, falls back to the cleaner built-in `clam` theme. Matplotlib
is required for the figures.

    pip install sv_ttk matplotlib

Inputs (defaults derived from the workbook example in README.md):
    L_left            14.97  m       back-span length (over the pin)
    L_total           33.145 m       girder + nose total length
    w_girder_per_m    34.38  kN/m    girder self-weight per metre
    W_LN              80.00  kN      total launching-nose weight
    arm_LN_from_end   2.667  m       nose centroid from girder end (L_LN/3)
    SF_required       2.00   -       overturning safety factor

Workbook formulas, reproduced verbatim from girder_overturning_check.py:
    L_right = L_total - L_left
    W_left  = L_left  * w_per_m
    W_right = L_right * w_per_m
    M_stab  = W_left  * L_left  / 2
    M_over  = W_right * L_right / 2 + W_LN * (L_right + arm_LN_from_end)
    SF      = M_stab / M_over
    deficit = M_over * SF_required - M_stab
"""

from __future__ import annotations

import base64
import io
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Segoe UI Variable", "Segoe UI", "Helvetica", "DejaVu Sans",
]

try:
    import sv_ttk
    HAS_SVTTK = True
except ImportError:  # graceful degradation
    HAS_SVTTK = False

# Make the window crisp on high-DPI Windows displays.
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


DEFAULTS = {
    "L_left":          "14.97",
    "L_total":         "33.145",
    "w_girder_per_m":  "34.38",
    "W_LN":            "80.00",
    "arm_LN_from_end": "2.667",
    "SF_required":     "2.00",
}

# Each row: (key, mathtext-label, plain-text help, unit)
FIELD_LABELS = [
    ("L_left",          r"$L_\mathrm{left}$",       "back-span length over pin", "m"),
    ("L_total",         r"$L_\mathrm{total}$",      "girder + nose total",       "m"),
    ("w_girder_per_m",  r"$w_\mathrm{girder}$",     "self-weight per metre",     "kN/m"),
    ("W_LN",            r"$W_\mathrm{LN}$",         "launching-nose weight",     "kN"),
    ("arm_LN_from_end", r"$a_\mathrm{LN,end}$",     "nose centroid ($L_{LN}/3$)","m"),
    ("SF_required",     r"$\mathrm{SF}_\mathrm{req}$", "required safety factor", "-"),
]

# Mathtext expressions used in figure annotations and the formulas card.
MATH = {
    "L_left":   r"$L_\mathrm{left}$",
    "L_right":  r"$L_\mathrm{right}$",
    "L_total":  r"$L_\mathrm{total}$",
    "W_left":   r"$W_\mathrm{left}$",
    "W_right":  r"$W_\mathrm{right}$",
    "W_LN":     r"$W_\mathrm{LN}$",
    "arm_LN":   r"$a_\mathrm{LN}$",
    "M_stab":   r"$M_\mathrm{stab}$",
    "M_over":   r"$M_\mathrm{over}$",
    "SF":       r"$\mathrm{SF}$",
    "SF_req":   r"$\mathrm{SF}_\mathrm{req}$",
}

FORMULAS = [
    r"$M_\mathrm{stab} = W_\mathrm{left}\,L_\mathrm{left}/2$",
    r"$M_\mathrm{over} = W_\mathrm{right}\,L_\mathrm{right}/2 + W_\mathrm{LN}\,a_\mathrm{LN}$",
    r"$\mathrm{SF} = M_\mathrm{stab}/M_\mathrm{over}$",
    r"$\mathrm{deficit} = M_\mathrm{over}\cdot\mathrm{SF}_\mathrm{req} - M_\mathrm{stab}$",
]

# Girder cross-section polygon (m). Closed implicitly: last vertex links
# back to the first. User-supplied; treated as canonical geometry of the
# girder under analysis.
CROSS_SECTION = [
    (0.3125, 0.0000), (1.0375, 0.0000),
    (1.0375, 0.2000), (0.8000, 0.4000),
    (0.8000, 1.7000), (0.8750, 1.8500),
    (1.3500, 1.8500), (1.3500, 2.0000),
    (0.0000, 2.0000), (0.0000, 1.8500),
    (0.4750, 1.8500), (0.5500, 1.7000),
    (0.5500, 0.4000), (0.3125, 0.2000),
]


def polygon_area(verts):
    """Shoelace area of a closed polygon (vertices in any winding order)."""
    n = len(verts)
    s = 0.0
    for i in range(n):
        x1, y1 = verts[i]
        x2, y2 = verts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0

# Palette
C_BG       = "#fafafa"
C_BEAM     = "#374151"
C_PIN      = "#1d4ed8"
C_STAB     = "#16a34a"   # stabilizing / pass
C_OVER     = "#dc2626"   # overturning / fail
C_REQ      = "#7c3aed"   # required moment threshold
C_DIM      = "#6b7280"
C_TXT      = "#111827"


def compute(L_left, L_total, w_per_m, W_LN, arm_LN_from_end, SF_required):
    L_right   = L_total - L_left
    W_left    = L_left  * w_per_m
    W_right   = L_right * w_per_m

    arm_left  = L_left  / 2.0
    arm_right = L_right / 2.0
    arm_LN    = L_right + arm_LN_from_end

    M_stab = W_left  * arm_left
    M_over = W_right * arm_right + W_LN * arm_LN

    SF      = M_stab / M_over if M_over else float("inf")
    deficit = M_over * SF_required - M_stab

    return dict(
        L_right=L_right, W_left=W_left, W_right=W_right, W_LN=W_LN,
        arm_left=arm_left, arm_right=arm_right, arm_LN=arm_LN,
        M_stab=M_stab, M_over=M_over,
        SF=SF, SF_required=SF_required, deficit=deficit,
    )


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #

def draw_schematic(ax, L_left, r):
    """Free-body diagram: beam centred on the pin (x = 0).
    Left of pin = stabilizing, right of pin = overturning."""
    ax.clear()
    ax.set_facecolor(C_BG)

    L_right   = r["L_right"]
    arm_left  = r["arm_left"]
    arm_right = r["arm_right"]
    arm_LN    = r["arm_LN"]
    W_left    = r["W_left"]
    W_right   = r["W_right"]
    W_LN      = r["W_LN"]

    pin       = 0.0
    left_end  = -L_left
    right_end = L_right
    far       = max(right_end, arm_LN) + 1.5

    # Girder beam
    ax.plot([left_end, right_end], [0, 0],
            lw=12, color=C_BEAM, solid_capstyle="butt", zorder=2)

    # Lever-arm extension if W_LN sits past the girder end (workbook geometry)
    if arm_LN > right_end:
        ax.plot([right_end, arm_LN], [0, 0],
                lw=2, color=C_DIM, linestyle=(0, (4, 3)), zorder=1)

    # Pivot — wedge / fulcrum, apex at the pivot point. No hatched ground:
    # the girder pivots about a launching saddle, not a fixed pin support.
    ph = 0.55
    ax.fill([pin, pin - 0.55, pin + 0.55], [0, -ph, -ph],
            color=C_PIN, zorder=3)
    ax.text(pin, -ph - 0.18, "pivot", ha="center", va="top",
            fontsize=10, color=C_PIN, fontweight="bold")

    # Load arrows — length proportional to magnitude
    max_w = max(W_left, W_right, W_LN, 1.0)
    arr_max = 1.7

    def arrow(x, w, color, label):
        h = arr_max * w / max_w
        ax.annotate(
            "", xy=(x, 0.05), xytext=(x, h + 0.05),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2,
                            mutation_scale=18),
        )
        ax.text(x, h + 0.18, f"{label}\n{w:,.1f} kN",
                ha="center", va="bottom", fontsize=10, color=color)

    arrow(-arm_left, W_left,  C_STAB, MATH["W_left"])
    arrow(arm_right, W_right, C_OVER, MATH["W_right"])
    arrow(arm_LN,    W_LN,    C_OVER, MATH["W_LN"])

    # Lever-arm dimensions below the beam — stacked rows so labels don't collide
    def dim(x1, x2, y, label, color=C_DIM):
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.2))
        ax.text((x1 + x2) / 2, y - 0.22, label,
                ha="center", va="top", fontsize=8.5, color=C_TXT)

    dim(left_end, pin,        -1.55, f"{MATH['L_left']} = {L_left:.2f} m",   C_STAB)
    dim(pin,      right_end,  -1.55, f"{MATH['L_right']} = {L_right:.2f} m", C_OVER)
    dim(pin,      arm_LN,     -2.30, f"{MATH['arm_LN']} = {arm_LN:.2f} m",   C_DIM)

    ax.set_xlim(left_end - 1.5, far)
    ax.set_ylim(-3.2, arr_max + 1.4)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("Free-body diagram  ·  loads & moment arms about pivot",
                 fontsize=10.5, color=C_TXT, pad=10)


def draw_cross_section(ax, verts):
    """Filled outline of the girder cross-section, with computed area."""
    ax.clear()
    ax.set_facecolor(C_BG)

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]

    ax.fill(xs, ys, color="#cbd5e1", edgecolor="#334155",
            lw=1.4, zorder=2)

    A  = polygon_area(verts)
    w  = max(xs) - min(xs)
    h  = max(ys) - min(ys)

    pad = 0.15
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - 0.35, max(ys) + 0.20)
    ax.set_aspect("equal")
    ax.axis("off")

    # Width & depth dim arrows
    y_dim = min(ys) - 0.20
    ax.annotate("", xy=(max(xs), y_dim), xytext=(min(xs), y_dim),
                arrowprops=dict(arrowstyle="<->", color=C_DIM, lw=1.0))
    ax.text((min(xs) + max(xs)) / 2, y_dim - 0.05,
            f"{w:.2f} m", ha="center", va="top",
            fontsize=8, color=C_TXT)

    x_dim = max(xs) + 0.10
    ax.annotate("", xy=(x_dim, max(ys)), xytext=(x_dim, min(ys)),
                arrowprops=dict(arrowstyle="<->", color=C_DIM, lw=1.0))
    ax.text(x_dim + 0.04, (min(ys) + max(ys)) / 2,
            f"{h:.2f} m", ha="left", va="center",
            fontsize=8, color=C_TXT, rotation=90)

    ax.set_title(
        f"Cross-section\n$A$ = {A:.3f} m²",
        fontsize=10, color=C_TXT, pad=6,
    )


def draw_result(fig, L_left, r, bg_color):
    """Numeric result panel rendered as mathtext lines in a Figure.
    Replaces a Text widget so the variable names look like math and
    the labels can't wrap mid-value."""
    fig.clf()
    fig.set_facecolor(bg_color)

    deficit_label = ("excess capacity" if r["deficit"] < 0
                     else "moment deficit")

    knm = r"\,\mathrm{kN}\!\cdot\!\mathrm{m}"
    kn  = r"\,\mathrm{kN}"
    m_  = r"\,\mathrm{m}"

    # Format with thousands separators, then escape commas as {,} so
    # mathtext doesn't insert a thin-space after each one.
    def fn(v, dec=2):
        return f"{v:,.{dec}f}".replace(",", "{,}")

    rows = [
        (r"$L_\mathrm{left}$",  fr"${fn(L_left, 3)}{m_}$"),
        (r"$L_\mathrm{right}$", fr"${fn(r['L_right'], 3)}{m_}$"),
        None,
        ("HEAD", "Loads"),
        (r"$W_\mathrm{left}$",  fr"${fn(r['W_left'])}{kn}$   at  ${fn(r['arm_left'])}{m_}$"),
        (r"$W_\mathrm{right}$", fr"${fn(r['W_right'])}{kn}$   at  ${fn(r['arm_right'])}{m_}$"),
        (r"$W_\mathrm{LN}$",    fr"${fn(r['W_LN'])}{kn}$   at  ${fn(r['arm_LN'])}{m_}$"),
        None,
        ("HEAD", "Moments about pivot"),
        (r"$M_\mathrm{stab}$",  fr"${fn(r['M_stab'])}{knm}$"),
        (r"$M_\mathrm{over}$",  fr"${fn(r['M_over'])}{knm}$"),
        None,
        (r"$\mathrm{deficit}$", fr"${fn(abs(r['deficit']))}{knm}$   ({deficit_label})"),
    ]

    n = len(rows)
    y_top, y_bot = 0.96, 0.04
    y_step = (y_top - y_bot) / max(n - 1, 1)
    x_eq_left  = 0.34   # right-edge x for labels
    x_eq_right = 0.36   # left-edge x for "= value"

    for i, row in enumerate(rows):
        if row is None:
            continue
        y = y_top - i * y_step
        if isinstance(row, tuple) and row[0] == "HEAD":
            fig.text(0.04, y, row[1], fontsize=11.5, color=C_TXT,
                     va="center", fontweight="bold")
        else:
            label, value = row
            fig.text(x_eq_left, y, label, fontsize=11, color=C_TXT,
                     va="center", ha="right")
            fig.text(x_eq_right, y, "= " + value, fontsize=11,
                     color=C_TXT, va="center", ha="left")


def draw_moments(ax, r):
    """Bar chart: stabilizing vs overturning vs required capacity."""
    ax.clear()
    ax.set_facecolor(C_BG)

    M_stab = r["M_stab"]
    M_over = r["M_over"]
    SF     = r["SF"]
    SF_req = r["SF_required"]
    M_req  = M_over * SF_req

    cats   = [f"Stabilizing\n({MATH['W_left']})",
              f"Overturning\n({MATH['W_right']} + {MATH['W_LN']})",
              f"Required\n({MATH['M_over']}$\\cdot${SF_req:.2f})"]
    vals   = [M_stab, M_over, M_req]
    colors = [C_STAB, C_OVER, C_REQ]

    bars = ax.bar(cats, vals, color=colors, width=0.55, edgecolor="none")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.015,
                f"{v:,.0f}", ha="center", va="bottom",
                fontsize=9, color=C_TXT)

    # Threshold line at the required moment
    ax.axhline(M_req, color=C_REQ, lw=1.0, linestyle=(0, (5, 3)), alpha=0.55)

    passed = SF >= SF_req
    status_color = C_STAB if passed else C_OVER
    ax.set_ylabel(r"Moment, $M$  (kN$\cdot$m)", fontsize=10, color=C_TXT)
    ax.set_title(
        f"{MATH['SF']} = {SF:.3f}   {'PASS' if passed else 'FAIL'}   "
        f"(required {SF_req:.2f})",
        fontsize=12, color=status_color, fontweight="bold", pad=10,
    )
    ax.tick_params(colors=C_TXT, labelsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#d1d5db")
    ax.grid(axis="y", alpha=0.25, linestyle="-", color="#d1d5db")
    ax.set_axisbelow(True)


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Girder Overturning Check")
        self.minsize(1100, 760)
        self.geometry("1280x820")
        self._tex_cache: dict[tuple, tk.PhotoImage] = {}
        self._apply_theme()
        self._build()
        self._calculate()

    # Render a mathtext expression to a transparent PNG and wrap it as a
    # PhotoImage. Cached because PhotoImage instances must be kept alive
    # by something Python-side or Tk garbage-collects them.
    def _tex_image(self, expr: str, fontsize: int = 12,
                   color: str = C_TXT) -> tk.PhotoImage:
        key = (expr, fontsize, color)
        if key in self._tex_cache:
            return self._tex_cache[key]
        fig = Figure(figsize=(2, 0.5), dpi=120)
        fig.patch.set_alpha(0)
        fig.text(0, 0, expr, fontsize=fontsize, color=color,
                 ha="left", va="bottom")
        FigureCanvasAgg(fig)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True,
                    bbox_inches="tight", pad_inches=0.04)
        data = base64.b64encode(buf.getvalue()).decode("ascii")
        img = tk.PhotoImage(data=data)
        self._tex_cache[key] = img
        return img

    def _apply_theme(self):
        # Default font — Segoe UI Variable on Win 11, Segoe UI elsewhere.
        for name in ("Segoe UI Variable", "Segoe UI", "Helvetica"):
            try:
                test = tkfont.Font(family=name, size=10)
                if test.actual("family"):
                    family = name
                    break
            except tk.TclError:
                continue
        else:
            family = "TkDefaultFont"

        for fname in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                      "TkHeadingFont"):
            try:
                tkfont.nametofont(fname).configure(family=family, size=10)
            except tk.TclError:
                pass

        if HAS_SVTTK:
            sv_ttk.set_theme("light")
        else:
            ttk.Style().theme_use("clam")

        self.configure(bg=C_BG)

        style = ttk.Style()
        style.configure("Heading.TLabel", font=(family, 16, "bold"),
                        foreground=C_TXT, background=C_BG)
        style.configure("Sub.TLabel", font=(family, 10),
                        foreground=C_DIM, background=C_BG)
        style.configure("FieldName.TLabel", font=(family, 10, "bold"),
                        foreground=C_TXT)
        style.configure("FieldHelp.TLabel", font=(family, 9),
                        foreground=C_DIM)
        style.configure("Result.TLabel", font=("Consolas", 10),
                        foreground=C_TXT)
        style.configure("Status.TLabel", font=(family, 14, "bold"))
        style.configure("Accent.TButton", font=(family, 10, "bold"))
        style.configure("Card.TFrame", background="#ffffff", relief="flat")

    def _build(self):
        # Title bar
        header = ttk.Frame(self, padding=(20, 16, 20, 8))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(header, text="Girder Overturning Check",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(header,
                  text="Launching girder on a pin — back span vs girder + nose",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        # Two-column body
        body = ttk.Frame(self, padding=(16, 4, 16, 16))
        body.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        body.columnconfigure(0, weight=0, minsize=360)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ---- Left column: inputs + numeric result -----------------------
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        inputs = ttk.LabelFrame(left, text="  Inputs  ", padding=14)
        inputs.pack(fill="x")
        self.entries: dict[str, ttk.Entry] = {}
        for i, (key, math_label, helptxt, unit) in enumerate(FIELD_LABELS):
            img = self._tex_image(math_label, fontsize=13)
            lbl = ttk.Label(inputs, image=img, background=C_BG)
            lbl.image = img  # keep ref
            lbl.grid(row=i * 2, column=0, sticky="w", padx=(0, 12),
                     pady=(8, 0))
            e = ttk.Entry(inputs, width=12, justify="right")
            e.insert(0, DEFAULTS[key])
            e.grid(row=i * 2, column=1, sticky="ew", pady=(8, 0))
            e.bind("<Return>", lambda _e: self._calculate())
            ttk.Label(inputs, text=unit, style="FieldHelp.TLabel").grid(
                row=i * 2, column=2, sticky="w", padx=(8, 0), pady=(8, 0)
            )
            if "$" in helptxt:
                # Render mathtext-bearing help lines so $L_{LN}/3$ etc. look right
                himg = self._tex_image(helptxt, fontsize=10, color=C_DIM)
                hlbl = ttk.Label(inputs, image=himg, background=C_BG)
                hlbl.image = himg
                hlbl.grid(row=i * 2 + 1, column=0, columnspan=3,
                          sticky="w", pady=(0, 4))
            else:
                ttk.Label(inputs, text=helptxt,
                          style="FieldHelp.TLabel").grid(
                    row=i * 2 + 1, column=0, columnspan=3,
                    sticky="w", pady=(0, 4),
                )
            self.entries[key] = e
        inputs.columnconfigure(1, weight=1)

        # Buttons
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(12, 12))
        ttk.Button(btns, text="Calculate", style="Accent.TButton",
                   command=self._calculate).pack(side="left", padx=(0, 8),
                                                 ipadx=8, ipady=2)
        ttk.Button(btns, text="Reset defaults",
                   command=self._reset).pack(side="left")

        # Formulas card — equations rendered as math
        formulas = ttk.LabelFrame(left, text="  Formulas  ", padding=12)
        formulas.pack(fill="x", pady=(0, 12))
        for expr in FORMULAS:
            fimg = self._tex_image(expr, fontsize=12)
            fl = ttk.Label(formulas, image=fimg, background=C_BG)
            fl.image = fimg
            fl.pack(anchor="w", pady=2)

        # Status banner
        self.status_var = tk.StringVar(value="")
        self.status_lbl = ttk.Label(left, textvariable=self.status_var,
                                    style="Status.TLabel", anchor="center",
                                    padding=(0, 10))
        self.status_lbl.pack(fill="x", pady=(0, 8))

        # Numeric result — rendered as mathtext lines in a matplotlib figure
        # so the variable names look like math and lines can't wrap mid-value.
        out = ttk.LabelFrame(left, text="  Numeric result  ", padding=4)
        out.pack(fill="both", expand=True)
        self._result_bg = "#ffffff" if HAS_SVTTK else "#f3f4f6"
        self.fig_result = Figure(figsize=(4.4, 4.6), dpi=110,
                                 facecolor=self._result_bg)
        self.canvas_result = FigureCanvasTkAgg(self.fig_result, master=out)
        self.canvas_result.get_tk_widget().pack(fill="both", expand=True,
                                                padx=4, pady=4)

        # ---- Right column: figures --------------------------------------
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=4)
        right.rowconfigure(1, weight=5)
        right.columnconfigure(0, weight=1)

        # Schematic + cross-section side-by-side in one figure
        self.fig_schem = Figure(figsize=(8.4, 3.6), dpi=100, facecolor=C_BG)
        gs = self.fig_schem.add_gridspec(1, 6, wspace=0.05)
        self.ax_schem = self.fig_schem.add_subplot(gs[0, :5])
        self.ax_cs    = self.fig_schem.add_subplot(gs[0, 5])
        self.fig_schem.subplots_adjust(left=0.02, right=0.98,
                                       top=0.90, bottom=0.06)
        self.canvas_schem = FigureCanvasTkAgg(self.fig_schem, master=right)
        self.canvas_schem.get_tk_widget().grid(row=0, column=0, sticky="nsew",
                                               pady=(0, 8))

        # Moments bar chart
        self.fig_bars = Figure(figsize=(7.4, 3.6), dpi=100, facecolor=C_BG)
        self.ax_bars  = self.fig_bars.add_subplot(111)
        self.fig_bars.subplots_adjust(left=0.10, right=0.98,
                                      top=0.88, bottom=0.18)
        self.canvas_bars = FigureCanvasTkAgg(self.fig_bars, master=right)
        self.canvas_bars.get_tk_widget().grid(row=1, column=0, sticky="nsew")

    # ---- Actions --------------------------------------------------------

    def _read_inputs(self):
        try:
            return {k: float(self.entries[k].get()) for k, _, _, _ in FIELD_LABELS}
        except ValueError as exc:
            messagebox.showerror("Invalid input",
                                 f"All fields must be numeric.\n{exc}")
            return None

    def _reset(self):
        for k, _, _, _ in FIELD_LABELS:
            self.entries[k].delete(0, "end")
            self.entries[k].insert(0, DEFAULTS[k])
        self._calculate()

    def _calculate(self):
        vals = self._read_inputs()
        if vals is None:
            return
        if vals["L_left"] <= 0 or vals["L_left"] >= vals["L_total"]:
            messagebox.showerror(
                "Out of range",
                f"L_left must be in (0, {vals['L_total']:.3f}) m "
                f"to keep the system on the pivot.",
            )
            return

        r = compute(
            vals["L_left"], vals["L_total"], vals["w_girder_per_m"],
            vals["W_LN"], vals["arm_LN_from_end"], vals["SF_required"],
        )
        self._render_status(r)

        draw_schematic(self.ax_schem, vals["L_left"], r)
        draw_cross_section(self.ax_cs, CROSS_SECTION)
        draw_moments(self.ax_bars, r)
        draw_result(self.fig_result, vals["L_left"], r, self._result_bg)
        self.canvas_schem.draw_idle()
        self.canvas_bars.draw_idle()
        self.canvas_result.draw_idle()

    def _render_status(self, r):
        passed = r["SF"] >= r["SF_required"]
        if passed:
            self.status_var.set(f"PASS    SF = {r['SF']:.3f}  ≥  {r['SF_required']:.2f}")
            self.status_lbl.configure(foreground=C_STAB)
        else:
            self.status_var.set(f"FAIL    SF = {r['SF']:.3f}  <  {r['SF_required']:.2f}")
            self.status_lbl.configure(foreground=C_OVER)



if __name__ == "__main__":
    App().mainloop()
