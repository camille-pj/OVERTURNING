# OVERTURNING — Project notes for Claude

A small Python project that performs the **launching-girder overturning check**
on a pin support: back span (left of pin) holds the system down; girder span +
launching nose (right of pin) try to tip it over.

## Layout

- [girder_overturning_check.py](girder_overturning_check.py) — CLI script.
  Reads every parameter from `GIRDER OVERTURNING CHECK (1).xlsx` (path hard-coded
  near the top, `XLSX_PATH`), prompts for `L_left`, prints the report.
  Depends on `openpyxl`.
- [girder_overturning_ui.py](girder_overturning_ui.py) — Tkinter desktop UI.
  Self-contained (no Excel). All input fields are pre-populated with defaults
  derived from the workbook example in the README; edit & click Calculate.
  Two embedded matplotlib figures: free-body schematic (beam, pivot wedge,
  scaled load arrows, lever-arm dimensions, cross-section panel) and a
  moments bar chart with the required-capacity threshold. Variables are
  rendered as mathtext throughout (form labels, formulas card, figure
  annotations). Theme is Sun Valley (Win 11 fluent) when
  `sv_ttk` is installed, else `clam`.

  Deps: `pip install matplotlib sv_ttk` — `matplotlib` is required for the
  figures, `sv_ttk` is optional (graceful fallback to `clam`).
- [README.md](README.md) — end-user instructions for the CLI script
  (Python install, `openpyxl`, how to run, troubleshooting).

## Single source of truth

The workbook `GIRDER OVERTURNING CHECK (1).xlsx` is canonical. The CLI script
mirrors its formulas verbatim — see the source-cell map in the
[script docstring](girder_overturning_check.py). The UI mirrors the same
formulas but takes parameters from the form instead of the workbook.

If a formula or parameter changes in the workbook:
1. Update the cell map / formulas in `girder_overturning_check.py`.
2. Update `compute()` and `DEFAULTS` in `girder_overturning_ui.py` to match.
3. Refresh the example session in `README.md` if the numbers shift.

## Conventions

- Units are SI throughout: lengths in metres, weights in kN, moments in kN·m,
  area in mm², density in kN/m³.
- Sign convention for `deficit`: positive = moment shortfall (FAIL),
  negative = excess capacity (PASS).
- Both scripts assume `0 < L_left < L_total`; outside that range the system
  isn't on the pin and the check is undefined.
- Console output uses UTF-8 (`kN·m`, ✅/❌); the CLI script reconfigures
  stdout on Windows. The UI sticks to plain ASCII (`kN-m`, PASS/FAIL) to
  avoid Tk font-fallback issues.

## Running

```powershell
python girder_overturning_check.py    # CLI, needs openpyxl + the .xlsx
python girder_overturning_ui.py       # GUI, stdlib only
```
