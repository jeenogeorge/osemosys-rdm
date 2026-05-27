# Verification Guide — RDM Fixes 2026-05

> **Audience:** any team member who needs to verify that the fixes applied to
> the RDM pipeline work on their machine.
>
> **Source plan:** [RDM_Remaining_Fixes_Plan.md](RDM_Remaining_Fixes_Plan.md)
>
> **Estimated effort to run all verifications:** ~25 min if the RDM experiment
> has already been executed; ~45 min if it has to be run from scratch.

---

## Summary of changes

Six fixes were applied to the RDM pipeline. The first four are cleanup of
`Uncertainty_Table`/`Setup`. The last two are functional:

| ID | What changed | Risk if wrong |
|----|------------|---------------------|
| **4A** | `DEP` rows added for `LVSGOACU` and `LVSSHPCU` (they were orphan `YES_PROP`) | Goats/sheep CU don't move correlated with CF |
| **4B** | `Setup.Region`: `BWA` → `RE1` (aligned with `set REGION` from `Scenario1.txt`) | Output CSV gets mislabeled |
| **4C** | Cleanup: `Involved_Scenarios` from `"Scenario1 ; Scenario2"` → `"Scenario1"` | Log noise |
| **4D** | X_Num 2-4 descriptions fixed (other/goat/sheep, previously all said cattle) | Cosmetic only |
| **P2** | Added `YES_PROP`/`DEP` pair for `CapitalCost`/`FixedCost` covering 6 renewable techs grouped in a single multi-value row. Required **relaxing a validation** in `0_experiment_manager.py` that forbade multi-value. | FixedCost/CapitalCost ratio not preserved per technology |
| **VAL** | Second relaxation of the length validation: now allows `len(primary) != len(dependent)` with warning. Enables the UDC RE/non-RE shares case with asymmetric lists (e.g. 8 RE vs 13 non-RE). Safe when baselines are uniform per side. | If the primary baselines are NOT uniform, dep rows with index >= len(pri) inherit from the last primary, which may not be what's expected. |

**Refactors 4E.1/4E.2/4E.3 were NOT applied** (per plan recommendation: each
one is a separate PR/sprint).

**RE/non-RE coupling (UDC sum-to-constant)** is implemented **entirely in
`Uncertainty_Table`**, with two available paths (see dedicated section at the
end): (A) per-row opt-in columns `RE_Techs` / `NonRE_Techs` / `Sum_To_Value`
(recommended), or (B) paired multi-value `YES_ADD`/`DEP` rows.
**There is no global configuration in `Setup`** for this.

---

## Pre-requisites

```powershell
# From the repo root
python -c "import openpyxl, pandas; print('OK deps')"
```

If it fails, install with `pip install openpyxl pandas`.

For full functional verification you also need a solver installed (CPLEX by
default in `Setup.Solver`).

---

## Quick verification — all fixes at once

```powershell
python verify_rdm_fixes.py
python verify_problem2_ratios.py
```

If both exit with code 0 and a positive final message → everything is OK. To
understand **what** each one verifies or to diagnose failures, see the sections
below.

---

## Problem 4A — DEP rows for LVSGOACU and LVSSHPCU

**What was broken before?** Rows 12 (`LVSGOACF`) and 13 (`LVSSHPCF`) declared
`Dependency=YES_PROP` but had no following `DEP` row. Result: the CU
(non-climatic) versions of goat and sheep **were not perturbed in correlation**
with their CF counterpart, breaking the symmetry that does exist for rows 8-9
(LVSOTHCF/CU) and 10-11 (LVSCTLCF/CU).

**What should happen now?** For each perturbed future, the ratio
`perturbed_CU/perturbed_CF` must equal `baseline_CU/baseline_CF` per
(Region, AGRWAT1, Year), because `YES_PROP` applies
`new_dep = baseline_dep * (new_pri / baseline_pri)`.

### Verification

**Step 1 — Excel structure:**

```powershell
python verify_rdm_fixes.py
```

Look for the line: `OK no orphan YES_PROP`. If it says `Orphan YES_PROP: [...]`
→ check the cited row.

**Step 2 — experiment logs:**

In the stdout of `RUN_RDM.py`, look for:
```
Dependency (YES_PROP): Row 13 dependent on Row 12 | Scenario Scenario1 Future 1
Dependency (YES_PROP): Row 15 dependent on Row 14 | Scenario Scenario1 Future 1
```

If it doesn't appear for `Row 13` and `Row 15`, the dependency isn't being
processed.

**Step 3 — numerical comparison (optional, requires outputs):**

Open `src/workflow/1_Experiment/Experimental_Platform/Futures/Scenario1/Scenario1_1/Scenario1_1.txt`
and `src/workflow/1_Experiment/Executables/Scenario1_0/Scenario1_0.txt`. Locate
the rows `LVSGOACF` and `LVSGOACU` within the `param InputActivityRatio` block.
Compute for the same (Region, AGRWAT1, Year):

```
ratio_CF = perturbed_LVSGOACF / baseline_LVSGOACF
ratio_CU = perturbed_LVSGOACU / baseline_LVSGOACU
```

`ratio_CF` must be ≈ `ratio_CU` (same perturbation factor).

---

## Problem 4B — Region BWA → RE1

**What was broken before?** `Setup.Region = 'BWA'` but `Scenario1.txt` uses
`set REGION := RE1`. The variable is only used to name the output CSV
(`OSEMOSYS_BWA_Energy_Input.csv`), it doesn't affect the model itself — but
the files were mislabeled.

### Verification

**Step 1 — static alignment:**

```powershell
python verify_rdm_fixes.py
```

Look for: `OK Setup.Region='RE1' aligned with Scenario1.txt`.

**Step 2 — output CSV name:**

```powershell
Get-ChildItem -Recurse -Filter "OSEMOSYS_*_Energy_Input.csv" | Select-Object Name
```

`OSEMOSYS_RE1_Energy_Input.csv` should appear. **No** `OSEMOSYS_BWA_*` should
exist. If it does, it's from an old run — delete it manually.

---

## Problem 4C — Cleanup of Scenario2 references

**What was broken before?** The 13 rows of `Uncertainty_Table` said
`"Scenario1 ; Scenario2"` but `src/workflow/0_Scenarios/` only contains
`Scenario1.txt`. It didn't cause an error but generated conceptual noise.

### Verification

```powershell
python verify_rdm_fixes.py
```

Look for: `OK no references to Scenario2 in Involved_Scenarios`.

If you need `Scenario2` again, see `RDM_Remaining_Fixes_Plan.md`
section **4C-Option 2**.

---

## Problem 4D — Descriptions for rows 2-4

**What was broken before?** The first four rows said
`"Demand Growth - livestock cattle"` even though they applied to LVSCTL (cattle),
LVSOTH (other), LVSGOA (goat), LVSSHP (sheep). Confusing when reviewing results.

### Verification

```powershell
python verify_rdm_fixes.py
```

Look for: `OK descriptions for rows 1-4 corrected`. If it fails, it prints
which row is wrong and what was expected.

---

## Problem 2 — Grouped CapitalCost ↔ FixedCost **[the most important]**

**What was broken before?** There was no correlated perturbation for the costs
of renewable technologies. Re-adding it "row per technology" would have needed
12 rows (6 YES_PROP + 6 DEP). The plan proposed a better pattern: **a single
multi-value row** YES_PROP + one DEP, covering all 6 technologies grouped via
index-by-index alignment.

When implementing it, we discovered that `0_experiment_manager.py` had a
**too strict validation** (`When using dependency, each row must have exactly
1 value...`) that blocked multi-value usage, **even though the iteration code
did support it**. We relaxed the validation to "primary and dependent must
have equal length" (which is the actual requirement).

**Invariant to verify:** For each technology in
`{PWRSOL001, PWRWND001, PWRBIO001, PWRGEO, PWRCSP001, PWRCSP002}`,
every perturbed future and every year, the following must hold:

```
FixedCost_perturbed[tech, y]     FixedCost_baseline[tech, y]
─────────────────────────────  =  ────────────────────────────
CapitalCost_perturbed[tech, y]   CapitalCost_baseline[tech, y]
```

### Verification

**Step 1 — Excel:**

```powershell
python verify_rdm_fixes.py
```

Look for:
```
OK Problem 2: X_Num 16↔17 aligned (PWRSOL001 ; PWRWND001 ; ...)
```

**Step 2 — functional (requires `Results/` populated by a recent run):**

```powershell
python verify_problem2_ratios.py
```

Expected output:
```
OK Scenario1_1: 216 cells compared, max ratio diff = X.XXe-14
OK Scenario1_2: 216 cells compared, max ratio diff = X.XXe-14
...
RESULT: ALL RATIOS PRESERVED (Problem 2 functional)
```

`216 cells` = 6 technologies × 36 years. The ratio difference must be on the
order of `1e-13` (double-precision floating-point accuracy). If it's greater
than `1e-6`, something is wrong.

**Step 3 — effective perturbation sanity check:**

If the output shows `⚠️ NO PERTURBATION OCCURRED`, the perturbed value is
identical to the baseline. This may be legitimate (LHS sampled close to 1.0)
if it only happens in one or two futures, but if all futures show it → check
that rows X_Num 16-17 are being processed (look for
`Dependency (YES_PROP): Row 17 dependent on Row 16` in stdout).

---

## RE/non-RE share configuration (in-band in Uncertainty_Table)

**Design decision:** RE/non-RE coupling configuration lives **per row** in
`Uncertainty_Table`, not in global `Setup` columns. Each uncertainty that
requires coupling defines its RE and non-RE technology lists in its own opt-in
columns, alongside its LHS range, initial year, etc.

There are **two paths** that are functionally equivalent; choose one based on
preference:

### Path A — Opt-in columns `RE_Techs` / `NonRE_Techs` / `Sum_To_Value` (recommended)

**A single row** explicitly declares both lists and the sum target:

| Column | Meaning |
|---|---|
| `RE_Techs` | `;`-separated list of renewable technologies. The row perturbs them normally (via `Involved_First_Sets_in_Osemosys`). |
| `NonRE_Techs` | `;`-separated list of non-renewable technologies to adjust. |
| `Sum_To_Value` | Target value of the sum (defaults to `1.0` if the cell is empty but `RE_Techs`/`NonRE_Techs` are populated). |

**Activation**: the fixer runs **only** if a row has both lists populated.
Rows with empty `RE_Techs` or `NonRE_Techs` are not affected. The fixer:

1. Reads the **already-perturbed** values of each technology in `RE_Techs` per
   `(Region, Year)` (from the row's `Initial_Year_of_Uncertainty`).
2. Computes `target_nonre_total = Sum_To_Value - sum(RE_values_in_(R,Y))`.
3. Rewrites **each** technology in `NonRE_Techs` to the uniform value
   `target_nonre_total / len(NonRE_Techs)`.

Auditable logs in `Experimental_Platform/Logs/RE_NonRE_Share_Corrections/re_nonre_share_corrections.log`.

### Path B — Multi-value YES_ADD/DEP pair (mathematical alternative)

**Two paired rows** (`Dependency=YES_ADD` + `Dependency=DEP`) mathematically
implement constant sum by construction:

```
new_dep + new_pri = baseline_dep + baseline_pri   (invariant per row pair)
```

If baselines are uniform on each side (typical for shares), perturbing the RE
side to `-X'` propagates delta `(-X' - (-X))` to all non-RE → they end up at
`1-X'`. **No additional columns required**; it relies on the existing manager
and the length relaxation (commit `837aa51`).

### When to use each one

- **Path A** if you want a single row per uncertainty, with declarative
  configuration and explicit target (`Sum_To_Value`). Better for uncertainties
  that are clearly "shares" and you want to make the intention visible.
- **Path B** if you already have the YES_ADD/DEP pattern in other uncertainties
  and prefer consistency, or if you need each side to have its own distinct
  LHS range.

### Pre-requisite in the base model

The inputs to perturb **must exist** in `src/workflow/0_Scenarios/Scenario1.txt`.
For the UDC `PWRREN` case, that means populating `param UDCMultiplierActivity`
with slices of the form:

```
[RE1,PWRSOL001,*,*]:
2020 ... 2055 :=
PWRREN -0.3 -0.3 ... -0.3
[RE1,PWRCBM001,*,*]:
2020 ... 2055 :=
PWRREN  0.7  0.7 ...  0.7
... (one slice per tech)
```

And activate the UDC: `UDCTag[RE1, PWRREN] = 1` (not `0`). Without this, the
RDM rows will attempt to perturb indices that don't exist → **silently with no
effect**.

### Configuration (Path A, example with UDC PWRREN)

In `Uncertainty_Table`, **a single** opt-in row:

| Field | Value |
|---|---|
| `X_Category` | `UDC Renewable Share` |
| `X_Mathematical_Type` | `Step` |
| `Explored_Parameter_of_X` | `Final_Value` |
| `Initial_Year_of_Uncertainty` | `2030` |
| `Min_Value` / `Max_Value` | `-0.5` / `-0.3` |
| `Exact_Parameters_Involved_in_Osemosys` | `UDCMultiplierActivity` |
| `Dependency` | `NO` |
| `Involved_First_Sets_in_Osemosys` | RE techs list (same as `RE_Techs`) |
| `Involved_Second_Sets_in_Osemosys` | `PWRREN` |
| `RE_Techs` | `PWRSOL001 ; PWRBIO001 ; PWRWND001 ; PWRWND001S ; PWRCSP002 ; PWRCSP001 ; PWRSOL001S ; PWRGEO` |
| `NonRE_Techs` | `PWRCBM001 ; PWRCOA003 ; PWRCOA_CCS ; PWRBIO_CCS ; PWRNGS001 ; PWRCOA001 ; PWRNGS002 ; PWROHC002 ; PWROHC003 ; PWRNUC ; PWRDSL ; PWRLFG001 ; PWRCOA002` |
| `Sum_To_Value` | `1.0` (or leave empty for default 1.0) |

When running `RUN_RDM.py`, the manager will print:
```
RE/NonRE Fix [X_Num=N]: parameter=UDCMultiplierActivity, second_set='PWRREN',
  |RE|=8, |NonRE|=13, Sum_To_Value=1.0, from_year=2030
RE/NonRE Fix: applied K correction(s) across all futures.
```

### Configuration (Path B, equivalent example with YES_ADD/DEP)

Two paired rows (no need for the RE_Techs/NonRE_Techs/Sum_To_Value columns):

| Field | Primary row (RE) | Dependent row (non-RE) |
|---|---|---|
| `X_Mathematical_Type` | `Step` | `Step` |
| `Exact_Parameters_Involved_in_Osemosys` | `UDCMultiplierActivity` | `UDCMultiplierActivity` |
| `Dependency` | `YES_ADD` | `DEP` |
| `Involved_First_Sets_in_Osemosys` | RE techs (8) | non-RE techs (13) |
| `Involved_Second_Sets_in_Osemosys` | `PWRREN` | `PWRREN` |

An informative WARNING will appear in stdout about different lengths (8 vs 13);
it's safe if the baselines are uniform.

### Verification

**Step 1 — confirm Setup does NOT have RE_Param/NonRE_Param columns**
(this mechanism was intentionally removed):

```python
import openpyxl
wb = openpyxl.load_workbook('src/Interface_RDM.xlsx', data_only=True)
ws = wb['Setup']
headers = [c.value for c in ws[1]]
assert 'RE_Param' not in headers and 'NonRE_Param' not in headers, \
    "Setup has RE_Param/NonRE_Param columns — the Setup-based mechanism was removed"
print('OK: Setup without RE_Param/NonRE_Param columns')
```

**Step 2 — confirm Uncertainty_Table HAS the opt-in columns:**

```python
import openpyxl
wb = openpyxl.load_workbook('src/Interface_RDM.xlsx', data_only=True)
ws = wb['Uncertainty_Table']
headers = [c.value for c in ws[1]]
for col in ('RE_Techs', 'NonRE_Techs', 'Sum_To_Value'):
    assert col in headers, f"Missing column {col}"
print('OK: Uncertainty_Table has the 3 opt-in columns')
```

**Step 3 — unit tests of the per-row fixer:**

```powershell
python tests/test_re_nonre_share_per_row.py
```

Expected output: 7 tests OK (basic, default sum, custom sum, year filter,
opt-in, no-op, log).

**Step 4 — when running `RUN_RDM.py`, one of these two lines must appear:**

```
RE/NonRE Fix: no rows opt-in to this fix (columns RE_Techs/NonRE_Techs both empty).
```
(if no row uses the feature — default behavior)

or

```
RE/NonRE Fix [X_Num=N]: parameter=..., |RE|=..., |NonRE|=..., Sum_To_Value=...
RE/NonRE Fix: applied K correction(s) across all futures.
```
(if a row has RE_Techs and NonRE_Techs populated)

**Step 5 — functional verification**: for each `(R, Y) >= Initial_Year_of_Uncertainty`,
confirm that `sum(RE_values_perturbed) + sum(NonRE_values_perturbed) == Sum_To_Value`:

```python
# Pseudocode
for (r, y) in regions_x_years:
    re_sum  = sum(UDC[r, t, PWRREN, y] for t in RE_Techs)   # perturbed
    nonre_sum = sum(UDC[r, t, PWRREN, y] for t in NonRE_Techs)  # perturbed
    assert abs((re_sum + nonre_sum) - sum_to_value) < 1e-9
```

---

## End-to-end verification: run the full experiment

If you want to redo everything from scratch:

```powershell
cd src
python RUN_RDM.py
```

Expected time: ~20 min with `Number_of_Runs=8` and CPLEX on 16 threads.
Expected output at the end:
```
5 futures processed: 5 optimal, 0 infeasible
Processing completed successfully.
```

If it fails, look at stdout — recent dependency validation errors print a
clear message with `Row N (primary/dependent) ...`.

---

## Inventory of added scripts

| File | Purpose | Idempotent |
|---------|-----------|-------------|
| `apply_rdm_cleanup.py` | Applies 4A/4B/4C/4D to the Excel | ✓ |
| `apply_rdm_problem2.py` | Adds rows X_Num 16/17 (Problem 2) to the Excel | ✓ |
| `add_re_nonre_columns.py` | Adds RE_Techs / NonRE_Techs / Sum_To_Value columns to Uncertainty_Table | ✓ |
| `verify_rdm_fixes.py` | Static verification of the Excel | ✓ |
| `verify_problem2_ratios.py` | Functional verification of CapitalCost/FixedCost ratios | ✓ |
| `tests/test_re_nonre_share_per_row.py` | Unit tests of the per-row RE/NonRE fixer | ✓ |

The scripts at the root (`apply_*`, `add_*`, `verify_*`) are operational tools.
They can be kept versioned or deleted according to team preference; the actual
changes live in the Excel and in `0_experiment_manager.py`.

---

## Modified files (summary for PR review)

- `src/Interface_RDM.xlsx` — `Uncertainty_Table` sheet (17 rows, previously 13)
  with 3 new opt-in columns (`RE_Techs`, `NonRE_Techs`, `Sum_To_Value`); `Setup`
  sheet same as before; `Region=RE1`.
- `src/workflow/1_Experiment/0_experiment_manager.py`:
  - Multi-value dependency validation relaxed in two steps
    (see appendix). Allows any configuration with at least
    one value on each side; different lengths emit a warning.
  - New `fix_re_nonre_share_per_row` function + post-perturbation wiring.
    Reads the 3 opt-in columns from `Uncertainty_Table` and applies the fixer
    only to rows that populate them.

Backup of the original Excel: `src/Interface_RDM.xlsx.bak`.

---

## Appendix — About length validation in dependency rows

The validation in `0_experiment_manager.py:1889-1903` evolved in two steps during this session:

**Original state (rejected):**
```python
if len(pri_first_sets) > 1 or len(dep_first_sets) > 1:
    sys.exit(1)  # "must have exactly 1 value"
```
Blocked any dependency row that had multi-value. It was falsely strict: the
underlying iteration code does handle multi-value.

**First relaxation (intermediate):**
```python
if len(pri_first_sets) != len(dep_first_sets):
    sys.exit(1)
```
Allowed multi-value but required symmetry. Covers P2 (6=6 renewable
technologies) but blocks Jeeno's UDC case (8 RE vs 13 non-RE).

**Current state (definitive):**
```python
if len(pri_first_sets) == 0 or len(dep_first_sets) == 0:
    sys.exit(1)
elif len(pri_first_sets) != len(dep_first_sets):
    print("WARNING: ...lengths differ, dep[i>=len(pri)] paired with last pri...")
```

Allows any configuration with at least 1 value on each side. When lengths
differ, the iteration code uses
`pri_first_sets[min(idx, len(pri)-1)]`, that is, dependents with index greater
than or equal to `len(pri)` are paired with the last primary.

### When it's safe to use different lengths

**Safe** — all pri techs share the same baseline and move to the same new
value. Typical case: UDC shares (RE/non-RE summing to constant).
Example: RE baselines = -0.3 for all 8 RE techs, LHS samples -0.5, all 8 RE go
to -0.5, uniform delta = -0.2. YES_ADD propagates -0.2 to all 13 dep
correctly.

**Not safe** — pri techs with different baselines. The last dep rows would
inherit the delta from the last specific pri, which is typically not what's
expected. In that case use strict equality or the 3b fixer via
`Setup.RE_Param/NonRE_Param`.

### How to verify after running an experiment

Look in the experiment stdout for lines like:
```
WARNING: Dependency rows N (primary) and M (dependent) have different lengths...
```

If it appears and you did NOT expect different lengths → check the cited row.
If it appears and is intentional → confirm that the primary baselines are
uniform by inspecting the parameter block in `Scenario1.txt`.
