# Girder Overturning Check

Desktop tool for the launching-girder overturning check on a pivot — back span (left) holds the system down, girder span + launching nose (right) try to tip it over. Replicates `GIRDER OVERTURNING CHECK (1).xlsx` formulas verbatim and adds a modern GUI with a free-body diagram, cross-section panel, and moments bar chart.

Developed by **Albert Pamonag and Camille Pajarillaga**.

---

## 1. Quick start (the easy way)

```powershell
py main.py
```

That launches the desktop UI. All input fields come pre-populated with the workbook example values, so the form opens already showing a result. Edit any field and click **Calculate** (or press **Enter**) to refresh.

If `py` doesn't work on your machine, `python main.py` is equivalent.

---

## 2. One-time setup

You only do this once.

### a. Confirm Python is installed

Open **PowerShell** (press `Win + X` → "Terminal" or "Windows PowerShell") and run:

```powershell
python --version
```

You should see something like `Python 3.14.x`. If you get a Microsoft Store popup or "Python was not found", use the full path that *is* installed:

```powershell
& "C:\Users\Camille\AppData\Local\Python\bin\python.exe" --version
```

If even that fails, install Python from <https://www.python.org/downloads/windows/> and tick **"Add python.exe to PATH"** during install.

### b. Install dependencies

```powershell
py -m pip install matplotlib sv_ttk openpyxl
```

| package    | needed for                                                       |
|------------|------------------------------------------------------------------|
| matplotlib | the UI's embedded figures (free-body diagram, bar chart, result) |
| sv_ttk     | optional — Sun Valley (Win 11 fluent) theme; falls back to `clam` if missing |
| openpyxl   | only the legacy CLI script (`girder_overturning_check.py`)       |

---

## 3. Using the desktop UI

```powershell
py main.py
```

The window has three things going on:

- **Inputs (left)** — six fields with mathtext labels: `L_left`, `L_total`, `w_girder`, `W_LN`, `a_LN,end`, `SF_req`. Defaults match the workbook example. Press **Enter** in any field or click **Calculate** to refresh; **Reset defaults** restores them.
- **Free-body schematic (top right)** — beam, pivot wedge, scaled load arrows (green = stabilizing `W_left`; red = overturning `W_right`, `W_LN`), lever-arm dimensions. A side panel shows the girder cross-section with its computed area.
- **Moments bar chart (bottom right)** — Stabilizing vs Overturning vs Required (`M_over × SF_req`), with a dashed threshold and a coloured PASS/FAIL title.

The numeric result panel under the inputs is rendered with mathtext too, so the variable names look like proper math (`$L_\mathrm{left}$`, `$M_\mathrm{stab}$`, etc.).

A coloured banner above the result shows **PASS** (green) or **FAIL** (red) along with the computed safety factor.

---

## 4. Legacy CLI script

[`girder_overturning_check.py`](girder_overturning_check.py) reads every parameter from `GIRDER OVERTURNING CHECK (1).xlsx` and prompts only for `L_left`. Useful when you want to feed the workbook value through unchanged.

```powershell
py girder_overturning_check.py
```

When prompted:

```
Enter left girder length L_left (m): 14.97
```

Type the value, press **Enter**, and the report prints to the screen.

### Example session

```
============================================================
  GIRDER OVERTURNING CHECK
  Developed by Albert Pamonag and Camille Pajarillaga
============================================================
  Input
    L_left              : 14.97 m

  Loads
    W_left              : 514.69 kN  @ 7.49 m from pin
    W_right             : 624.89 kN  @ 9.09 m from pin
    W_LN                :  80.00 kN  @ 20.84 m from pin

  Moments about pin
    Stabilizing (left)  : 3852.48 kN·m
    Overturning (right) : 7345.99 kN·m

  Result
    Safety Factor       : 0.524
    Required SF         : 2.00
    Status              : ❌ FAIL
    Deficit             : 10839.51 kN·m (moment deficit)
============================================================
```

### Pointing at a different workbook

The path is hard-coded at the top of [`girder_overturning_check.py`](girder_overturning_check.py):

```python
XLSX_PATH = Path(r"C:\Users\Camille\Downloads\GIRDER OVERTURNING CHECK (1).xlsx")
```

If the workbook moves, edit that one line (keep the `r"..."` prefix so backslashes work), save, and re-run.

> **Tip:** after editing the workbook in Excel, **save and close it** before running the CLI script. `openpyxl` reads the cached values that Excel writes on save, so unsaved edits won't be picked up.

### One-liner (skip the prompt)

```powershell
"14.97" | py girder_overturning_check.py
```

Useful for batch-running several values:

```powershell
foreach ($L in 12.0, 13.5, 14.97, 16.0) {
    "$L" | py girder_overturning_check.py
}
```

---

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'matplotlib'` | Run the install command in section 2b. |
| `ModuleNotFoundError: No module named 'openpyxl'` | Same — `openpyxl` is only needed by the CLI script. |
| UI looks chunky / Win 98-style | `sv_ttk` isn't installed; `pip install sv_ttk` for the modern theme. The UI still runs without it (using `clam`). |
| Blurry text on a hi-DPI display | The UI sets DPI awareness automatically on Windows; if it still looks soft, check Windows display scaling. |
| `FileNotFoundError: ... GIRDER OVERTURNING CHECK ...` | CLI script only — Excel file isn't where `XLSX_PATH` points. Fix the path (section 4). |
| `TypeError` from CLI on `None` values | The workbook was edited but never saved. Open in Excel, **Ctrl + S**, close, and re-run. |
| Garbled `kN·m` or `❌` in CLI output | Console isn't using UTF-8. Run `chcp 65001` once in PowerShell before launching, or pipe to a file: `py girder_overturning_check.py > report.txt`. |
| `L_left must be in (0, 33.145) m` | Value outside the valid range — `L_left` must be positive and shorter than `L_total`. |
