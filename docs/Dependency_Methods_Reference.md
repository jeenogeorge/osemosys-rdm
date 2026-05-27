# Dependency Methods Reference — Uncertainty_Table

## Overview

The **Dependency** column in the `Uncertainty_Table` (sheet of `Interface_RDM.xlsx`) controls
how rows relate to each other during the experimental sampling process.

When a parameter's uncertainty is not independent — its variation should follow the change
of another parameter — we use the dependency mechanism.  The **primary** row is sampled
normally (via LHS + interpolation), and one or more **dependent** rows derive their new
values from the primary's change.

---

## Dependency Flags

| Flag | Role | Description |
|------|------|-------------|
| `NO` | Independent | The row is sampled independently via LHS. No dependency. |
| `YES_ADD` | Primary | This row is the primary. All subsequent `DEP` rows use **additive** dependency. |
| `YES_PROP` | Primary | This row is the primary. All subsequent `DEP` rows use **proportional** dependency. |
| `YES_ELAST` | Primary | This row is the primary. All subsequent `DEP` rows use **elastic** dependency. |
| `DEP` | Dependent | This row's values are **computed** from the nearest previous `YES_*` row. It is not sampled independently. |

> **Legacy aliases:** `YES` and `SI` are treated as `YES_ADD` for backward compatibility.

---

## Row Structure and Rules

### Basic pattern

```
Row N  :  YES_ADD / YES_PROP / YES_ELAST   <-- primary (sampled via LHS)
Row N+1:  DEP                               <-- dependent (computed from Row N)
```

### Multiple dependent rows

Multiple consecutive `DEP` rows all depend on the **same** primary row.
The search goes **backwards** until it finds the nearest `YES_*` row.

```
Row 1:  YES_PROP     <-- primary
Row 2:  DEP          <-- depends on Row 1
Row 3:  DEP          <-- depends on Row 1
Row 4:  DEP          <-- depends on Row 1
Row 5:  NO           <-- independent (breaks the chain)
Row 6:  YES_ELAST    <-- new primary
Row 7:  DEP          <-- depends on Row 6
Row 8:  NO           <-- independent
```

### Constraint: one set per dependency row

Each row involved in a dependency relationship (both `YES_*` and `DEP`) must have
**exactly one value** in `Involved_First_Sets_in_Osemosys`.

This means you cannot list multiple technologies or commodities in a single dependency
row.  If you need to apply the same dependency to multiple sets, use one `DEP` row
per set:

```
Row 2:  YES_ELAST  |  AccumulatedAnnualDemand       |  TRAMTR          <-- primary
Row 3:  DEP        |  TechActivityIncreaseByModeLimit|  TRAELCMTRCUR    <-- 1 set only
Row 4:  DEP        |  TechActivityIncreaseByModeLimit|  TRADSLMTRCUR    <-- 1 set only
```

**Why?** The dependency computation matches indices between the primary and dependent
parameters.  Having multiple sets in a single row would create ambiguity about which
primary set maps to which dependent set.

---

## Method 1: YES_ADD (Additive Dependency)

### Formula

```
new_dep(t) = baseline_dep(t) + [ new_pri(t) - baseline_pri(t) ]
```

Where:
- `baseline_dep(t)` — the dependent parameter's original value at year `t` (from the scenario file)
- `baseline_pri(t)` — the primary parameter's original value at year `t` (from the scenario file)
- `new_pri(t)` — the primary parameter's new value at year `t` (after LHS sampling + interpolation)

### What it does

The **absolute change** (delta) in the primary is added directly to the dependent.
All `DEP` rows receive the **same absolute increment**.

### Example

**Primary (Row 2, YES_ADD):** `AccumulatedAnnualDemand` for `TRAMTR`

| | baseline_pri(2030) | new_pri(2030) |
|---|---|---|
| Value | 1.46437 | 1.54446 |

Delta = 1.54446 - 1.46437 = **+0.08009**

**Dependent (Row 3, DEP):** `TechnologyActivityIncreaseByModeLimit` for `TRAELCMTRCUR`, mode `1`

```
new_dep(2030) = baseline_dep(2030) + delta
              = 0.01 + 0.08009
              = 0.09009
```

**Dependent (Row 4, DEP):** `TechnologyActivityIncreaseByModeLimit` for `TRADSLMTRCUR`, mode `1`

```
new_dep(2030) = baseline_dep(2030) + delta
              = 0.05 + 0.08009
              = 0.13009
```

### Characteristics

- All `DEP` rows receive the **same absolute delta**, regardless of their baseline scale.
- Best suited when the dependent parameter has the **same units and scale** as the primary.
- **Risk:** A large primary delta can overwhelm a small dependent baseline (e.g., adding
  0.08 to a baseline of 0.01 means an 800% increase).

---

## Method 2: YES_PROP (Proportional Dependency)

### Formula

```
new_dep(t) = baseline_dep(t) * [ new_pri(t) / baseline_pri(t) ]
```

Where:
- `baseline_dep(t)` — the dependent parameter's original value at year `t`
- `baseline_pri(t)` — the primary parameter's original value at year `t`
- `new_pri(t)` — the primary parameter's new value at year `t` (after LHS sampling)

### What it does

The **ratio** of the primary's change is applied multiplicatively to the dependent.
All `DEP` rows receive the **same percentage change**.

### Example

**Primary (Row 2, YES_PROP):** `AccumulatedAnnualDemand` for `TRAMTR`

| | baseline_pri(2030) | new_pri(2030) |
|---|---|---|
| Value | 1.46437 | 1.54446 |

Ratio = 1.54446 / 1.46437 = **1.05469** (+5.47%)

**Dependent (Row 3, DEP):** `TechnologyActivityIncreaseByModeLimit` for `TRAELCMTRCUR`, mode `1`

```
new_dep(2030) = baseline_dep(2030) * ratio
              = 0.01 * 1.05469
              = 0.01055    (+5.47%)
```

**Dependent (Row 4, DEP):** `TechnologyActivityIncreaseByModeLimit` for `TRADSLMTRCUR`, mode `1`

```
new_dep(2030) = baseline_dep(2030) * ratio
              = 0.05 * 1.05469
              = 0.05273    (+5.47%)
```

### Characteristics

- All `DEP` rows change by the **same percentage**.
- **Scale is preserved:** small baselines get small absolute changes, large baselines get
  large absolute changes.
- Equivalent to `YES_ELAST` with elasticity = 1.0.
- Best suited when the dependent should **grow or shrink at the same rate** as the primary.
- **Edge case:** If `baseline_pri(t) = 0`, the dependent retains its baseline value
  (division by zero is avoided).

---

## Method 3: YES_ELAST (Elastic Dependency)

### Formula

```
new_dep(t) = baseline_dep(t) * [ 1 + e * (new_pri(t) - baseline_pri(t)) / baseline_pri(t) ]
```

Where:
- `baseline_dep(t)` — the dependent parameter's original value at year `t`
- `baseline_pri(t)` — the primary parameter's original value at year `t`
- `new_pri(t)` — the primary parameter's new value at year `t` (after LHS sampling)
- `e` (epsilon) — LHS-sampled elasticity from the **dependent row's own** `[Min_Value, Max_Value]` range

### What it does

Like `YES_PROP`, but each `DEP` row has its **own elasticity** that controls how
strongly it responds to the primary's change.  The elasticity is sampled independently
for each future via LHS from the `DEP` row's `Min_Value` / `Max_Value` columns.

### How the elasticity is determined

The `Min_Value` and `Max_Value` columns of a `DEP` row under `YES_ELAST` do **not**
define the dependent parameter's range directly.  Instead, they define the
**elasticity range**:

| DEP row's column | Meaning under YES_ELAST |
|---|---|
| `Min_Value` | Minimum elasticity (e.g., 0.5 = half response) |
| `Max_Value` | Maximum elasticity (e.g., 2.0 = double response) |

The LHS samples a value between these bounds for each future, giving each future
a different elasticity.

### Example

**Primary (Row 2, YES_ELAST):** `AccumulatedAnnualDemand` for `TRAMTR`

| | baseline_pri(2030) | new_pri(2030) |
|---|---|---|
| Value | 1.46437 | 1.54446 |

Percentage change in primary = (1.54446 - 1.46437) / 1.46437 = **+5.47%**

**Dependent (Row 3, DEP):** `TechnologyActivityIncreaseByModeLimit` for `TRAELCMTRCUR`, mode `1`
- Elasticity range: [Min=1.0, Max=2.0]
- LHS-sampled elasticity for this future: **e = 1.4521**

```
new_dep(2030) = baseline_dep(2030) * [ 1 + e * pct_change_pri ]
              = 0.01 * [ 1 + 1.4521 * 0.0547 ]
              = 0.01 * 1.07942
              = 0.0107942
```

**Dependent (Row 4, DEP):** `TechnologyActivityIncreaseByModeLimit` for `TRADSLMTRCUR`, mode `1`
- Elasticity range: [Min=0.5, Max=1.0]
- LHS-sampled elasticity for this future: **e = 0.80**

```
new_dep(2030) = baseline_dep(2030) * [ 1 + e * pct_change_pri ]
              = 0.05 * [ 1 + 0.80 * 0.0547 ]
              = 0.05 * 1.04376
              = 0.05219
```

### Special elasticity values

| Elasticity (e) | Behavior |
|---|---|
| `e = 0` | Dependent does not change at all |
| `e = 1` | Equivalent to `YES_PROP` (full proportional response) |
| `0 < e < 1` | Partial response (dampened) |
| `e > 1` | Amplified response |
| `e < 0` | Inverse response (dependent moves opposite to primary) |

### Characteristics

- Each `DEP` row responds **differently** to the same primary change, controlled by
  its own elasticity.
- **Most flexible** method — subsumes both `YES_ADD` (with appropriate scaling) and
  `YES_PROP` (when e=1).
- **Scale is preserved** (multiplicative formula).
- Best suited when different dependent parameters should have **different sensitivities**
  to the same primary driver.
- **Edge case:** If `baseline_pri(t) = 0`, the dependent retains its baseline value.

---

## Comparison Table

| | YES_ADD | YES_PROP | YES_ELAST |
|---|---|---|---|
| **Formula** | `base_dep + delta` | `base_dep * ratio` | `base_dep * (1 + e * pct)` |
| **What DEP rows share** | Same absolute delta | Same % change | Same primary % change |
| **What each DEP row has** | Own baseline | Own baseline | Own baseline + own elasticity |
| **Scale preserved?** | No | Yes | Yes |
| **Multiple DEP behavior** | All shift equally | All scale equally | Each scales differently |
| **Use when** | Same units/scale | Same growth rate | Different sensitivities |

---

## Uncertainty_Table Configuration Example

| X_Num | X_Category | Exact_Parameters | Dependency | Involved_First_Sets | Min | Max |
|---|---|---|---|---|---|---|
| 2 | Demand Growth | AccumulatedAnnualDemand | YES_ELAST | TRAMTR | 0.5 | 1.5 |
| 3 | Demand Growth | TechActivityIncreaseByModeLimit | DEP | TRAELCMTRCUR | 1.0 | 2.0 |
| 4 | Demand Growth | TechActivityIncreaseByModeLimit | DEP | TRADSLMTRCUR | 0.5 | 1.0 |
| 5 | Fuel Cost | VariableCost | NO | IMPFOB | 0.8 | 1.2 |

- **Row 2:** Primary — `AccumulatedAnnualDemand` for `TRAMTR` is sampled via LHS
  (multiplier between 0.5 and 1.5 applied to the final value, then interpolated).
- **Row 3:** Dependent — `TechActivityIncreaseByModeLimit` for `TRAELCMTRCUR` is computed
  from Row 2's change using elastic dependency.  Min=1.0 / Max=2.0 define the
  **elasticity range** (not the parameter range).  Only one set (`TRAELCMTRCUR`).
- **Row 4:** Dependent — Same parameter but for `TRADSLMTRCUR`.  Its own elasticity
  range [0.5, 1.0] means it responds less strongly than Row 3.
- **Row 5:** Independent — No dependency.  Sampled normally via LHS.
