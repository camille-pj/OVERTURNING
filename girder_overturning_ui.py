"""
Girder Overturning Check — Tkinter UI
=====================================
Same calculation as girder_overturning_check.py, but as a desktop form so
parameters can be tweaked without re-running the script. All input fields
are pre-populated with defaults derived from the source workbook example
(see README.md "Example session"); edit any field and click Calculate.

Inputs (with defaults):
    L_left            14.97  m       back-span length (over the pin support)
    L_total           33.145 m       girder + nose total length
    w_girder_per_m    34.38  kN/m    girder self-weight per metre
    W_LN              80.00  kN      total launching-nose weight
    arm_LN_from_end   2.667  m       nose centroid from girder end (= L_LN/3)
    SF_required       2.00   -       overturning safety factor

Same workbook formulas as the CLI script:
    L_right       = L_total - L_left
    W_left        = L_left  * w_per_m
    W_right       = L_right * w_per_m
    M_stab        = W_left  * L_left  / 2
    M_over        = W_right * L_right / 2 + W_LN * (L_right + arm_LN_from_end)
    SF            = M_stab / M_over
    deficit       = M_over * SF_required - M_stab
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

DEFAULTS = {
    "L_left":          "14.97",
    "L_total":         "33.145",
    "w_girder_per_m":  "34.38",
    "W_LN":            "80.00",
    "arm_LN_from_end": "2.667",
    "SF_required":     "2.00",
}

FIELD_LABELS = [
    ("L_left",          "L_left  (back-span length)",        "m"),
    ("L_total",         "L_total  (girder + nose)",          "m"),
    ("w_girder_per_m",  "w_girder_per_m  (self-weight)",     "kN/m"),
    ("W_LN",            "W_LN  (launching-nose weight)",     "kN"),
    ("arm_LN_from_end", "arm_LN_from_end  (nose centroid)",  "m"),
    ("SF_required",     "SF_required",                       "-"),
]


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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Girder Overturning Check")
        self.resizable(False, False)
        self._build()
        self._calculate()  # show defaults' result on launch

    def _build(self):
        pad = dict(padx=8, pady=4)

        # Inputs frame
        inp = ttk.LabelFrame(self, text="Inputs")
        inp.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 6))

        self.entries: dict[str, ttk.Entry] = {}
        for i, (key, label, unit) in enumerate(FIELD_LABELS):
            ttk.Label(inp, text=label).grid(row=i, column=0, sticky="w", **pad)
            e = ttk.Entry(inp, width=12, justify="right")
            e.insert(0, DEFAULTS[key])
            e.grid(row=i, column=1, **pad)
            ttk.Label(inp, text=unit, foreground="#666").grid(
                row=i, column=2, sticky="w", **pad
            )
            self.entries[key] = e

        # Buttons
        btns = ttk.Frame(self)
        btns.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        ttk.Button(btns, text="Calculate",  command=self._calculate).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(btns, text="Reset defaults", command=self._reset).pack(side="left")

        # Output frame
        out = ttk.LabelFrame(self, text="Result")
        out.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.txt = tk.Text(
            out, width=58, height=20, font=("Consolas", 10),
            relief="flat", background="#f7f7f7",
        )
        self.txt.pack(padx=8, pady=8)
        self.txt.configure(state="disabled")

    def _read_inputs(self):
        try:
            return {k: float(self.entries[k].get()) for k, _, _ in FIELD_LABELS}
        except ValueError as exc:
            messagebox.showerror("Invalid input", f"All fields must be numeric.\n{exc}")
            return None

    def _reset(self):
        for k, _, _ in FIELD_LABELS:
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
                f"L_left must be in (0, {vals['L_total']:.3f}) m to keep the system on the pin.",
            )
            return

        r = compute(
            vals["L_left"], vals["L_total"], vals["w_girder_per_m"],
            vals["W_LN"], vals["arm_LN_from_end"], vals["SF_required"],
        )
        self._render(vals["L_left"], r)

    def _render(self, L_left, r):
        passed = r["SF"] >= r["SF_required"]
        status = "PASS" if passed else "FAIL"
        deficit_label = "(excess capacity)" if r["deficit"] < 0 else "(moment deficit)"

        lines = [
            f"  L_left              : {L_left:>9.3f} m",
            f"  L_right             : {r['L_right']:>9.3f} m",
            "",
            "  Loads",
            f"    W_left            : {r['W_left']:>9.2f} kN  @ {r['arm_left']:>6.2f} m from pin",
            f"    W_right           : {r['W_right']:>9.2f} kN  @ {r['arm_right']:>6.2f} m from pin",
            f"    W_LN              : {r['W_LN']:>9.2f} kN  @ {r['arm_LN']:>6.2f} m from pin",
            "",
            "  Moments about pin",
            f"    Stabilizing (left): {r['M_stab']:>9.2f} kN-m",
            f"    Overturning (rt)  : {r['M_over']:>9.2f} kN-m",
            "",
            "  Result",
            f"    Safety Factor     : {r['SF']:>9.3f}",
            f"    Required SF       : {r['SF_required']:>9.2f}",
            f"    Status            :    {status}",
            f"    Deficit           : {abs(r['deficit']):>9.2f} kN-m {deficit_label}",
        ]

        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(lines))

        # Colour the status line (last block) green/red
        self.txt.tag_configure("pass", foreground="#117a3d", font=("Consolas", 10, "bold"))
        self.txt.tag_configure("fail", foreground="#b00020", font=("Consolas", 10, "bold"))
        # Find the Status line and tag the word PASS/FAIL
        for idx, line in enumerate(lines, start=1):
            if line.lstrip().startswith("Status"):
                start = f"{idx}.0"
                end   = f"{idx}.end"
                self.txt.tag_add("pass" if passed else "fail", start, end)
                break

        self.txt.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()
