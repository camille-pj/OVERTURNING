# Girder Overturning Check — Terminal Usage

How to run [`girder_overturning_check.py`](girder_overturning_check.py) from a Windows terminal.

---

## 1. One-time setup

You only do this once.

### a. Confirm Python is installed

Open **PowerShell** (press `Win + X` → "Terminal" or "Windows PowerShell") and run:

```powershell
python --version
```

You should see something like `Python 3.14.x`. If instead you get a Microsoft Store popup or "Python was not found", use the full path that *is* installed on this machine:

```powershell
& "C:\Users\Camille\AppData\Local\Python\bin\python.exe" --version
```

If even that fails, install Python from <https://www.python.org/downloads/windows/> and tick **"Add python.exe to PATH"** during install.

### b. Install the one dependency

The script needs `openpyxl` to read `.xlsx` files. Install it once:

```powershell
& "C:\Users\Camille\AppData\Local\Python\bin\python.exe" -m pip install openpyxl
```

(If `python` is already on your PATH, `python -m pip install openpyxl` works too.)

---

## 2. Running the script

### a. Move into the project folder

```powershell
cd "C:\Users\Camille\Documents\GitHub\OVERTURNING"
```

### b. Run it

```powershell
python girder_overturning_check.py
```

or, if `python` is not on PATH:

```powershell
& "C:\Users\Camille\AppData\Local\Python\bin\python.exe" girder_overturning_check.py
```

### c. Enter the back-span length when prompted

```
Enter left girder length L_left (m): 14.97
```

Type the value, press **Enter**, and the report prints to the screen.

---

## 3. Example session

```
PS C:\Users\Camille\Documents\GitHub\OVERTURNING> python girder_overturning_check.py
Enter left girder length L_left (m): 14.97

============================================================
  GIRDER OVERTURNING CHECK
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

To run a different scenario, just run the script again and type a different `L_left`.

---

## 4. Pointing at a different workbook

The script reads parameters from the Excel file referenced at the top of the script:

```python
XLSX_PATH = Path(r"C:\Users\Camille\Downloads\GIRDER OVERTURNING CHECK (1).xlsx")
```

If the workbook moves, open `girder_overturning_check.py` in any text editor (Notepad, VS Code, etc.), edit that one line to the new absolute path (keep the `r"..."` raw-string prefix so backslashes work), save, and run the script again.

> **Tip:** after editing the workbook in Excel, **save and close it** before running the script. `openpyxl` reads the cached values that Excel writes on save, so unsaved edits won't be picked up.

---

## 5. One-liner (skip the prompt)

If you want to feed `L_left` straight in without typing it:

```powershell
"14.97" | python girder_overturning_check.py
```

Useful for batch-running several values:

```powershell
foreach ($L in 12.0, 13.5, 14.97, 16.0) {
    "$L" | python girder_overturning_check.py
}
```

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'openpyxl'` | Run the `pip install openpyxl` command from step 1b. |
| `FileNotFoundError: ... GIRDER OVERTURNING CHECK ...` | Excel file isn't where `XLSX_PATH` points — fix the path in the script (section 4). |
| `TypeError` on multiplication or `None` values | The workbook was edited but never saved. Open it in Excel, press **Ctrl + S**, close, and re-run. |
| Garbled `kN·m` or `❌` characters in output | The console isn't using UTF-8. Run `chcp 65001` once in PowerShell before launching the script, or read the report from a file via `python girder_overturning_check.py > report.txt`. |
| `L_left must be in (0, 33.145) m` | You entered a value outside the valid range — `L_left` must be positive and shorter than the total system length. |
