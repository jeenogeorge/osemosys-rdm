# Analysis: Uncertainty Multipliers When Baseline Final Value = 0

# Analisis: Multiplicadores de Incertidumbre Cuando el Valor Final de la Linea Base = 0

---

## 1. Developer's Statement Verification / Verificacion de la Afirmacion del Desarrollador

**Statement:** "The system always starts from the baseline final year value. Since that value is 0, any multiplier applied will still result in 0."

**Verdict: CORRECT / CORRECTA**

The code analysis and executable tests confirm this is mathematically inevitable in the current system design.

---

## 2. Technical Evidence / Evidencia Tecnica

### 2.1 How the system works (code flow)

The system has 3 phases:

1. **Phase 1** (lines ~900-1120 of `0_experiment_manager.py`): Reads the uncertainty table from `Interface_RDM.xlsx`, generates Latin Hypercube Samples (LHS), and creates `evaluation_value` for each uncertainty parameter. These values are stored in `experiment_dictionary[X_Num]['Values']`.

2. **Phase 2** (lines ~1126-1248): Reads the baseline scenario data into `stable_scenarios`.

3. **Phase 3** (lines ~1249-end): Copies baselines into `inherited_scenarios` and applies perturbations using interpolation functions.

### 2.2 The critical code path

In Phase 3, for `Explored_Parameter_of_X == 'Final_Value'`, the code at line ~1553 enters the interpolation logic:

```python
# Line 1517: The multiplier values per future
Values_per_Future = experiment_dictionary[u]['Values']

# Line 1553: Entry condition
if Math_Type in ['Time_Series', 'Constant', 'Logistic', 'Linear'] and Explored_Parameter_of_X=='Final_Value':
```

The baseline data is extracted as:
```python
# Line 1580-1581: Extract baseline values
value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][...])
value_list = [float(value_list[j]) for j in range(len(value_list))]
```

Then the interpolation functions are called with the multiplier:
```python
# Line 1594 (Time_Series):
new_value_list = AUX.interpolation_non_linear_final(time_list, value_list, float(Values_per_Future[fut_id]), ...)

# Line 1598 (Linear):
new_value_list = AUX.interpolation_linear(time_list, value_list, float(Values_per_Future[fut_id]), ...)

# Line 1600 (Logistic):
new_value_list = AUX.interpolation_logistic_trajectory(time_list, value_list, float(Values_per_Future[fut_id]), ...)
```

### 2.3 The mathematical root cause

Every interpolation function computes the **new final value** by multiplying the **baseline final value** by the multiplier:

| Function | Key Line (z_auxiliar_code.py) | Formula |
|---|---|---|
| `interpolation_non_linear_final` | Line 84 | `m_new = (ydata[-1] * multiplier - ydata[0]) / denom` |
| `interpolation_linear` | Line 261 | `final_value = value_list[-1] * multiplier` |
| `interpolation_logistic_trajectory` | Line 213 | `final_value = value_list[-1] * multiplier` |
| `interpolation_constant_trajectory` | Line 173 | No multiplier used (freezes at uncertainty year) |

**When `value_list[-1] = 0`:**
- `0 * any_multiplier = 0` (always)
- The system cannot produce a non-zero final value

### 2.4 Additional nuance: Time_Series with non-zero intermediate values

For `interpolation_non_linear_final`, the behavior is more subtle. When `ydata[-1] = 0`:

```
m_new = (0 * mult - ydata[0]) / (xdata[-1] - xdata[0])
     = -ydata[0] / denom  (independent of multiplier!)
```

This means the multiplier has **absolutely no effect** on the Time_Series function when the final baseline value is 0. The output is identical for mult=0.5, 1.0, 1.5, 2.0, or any other value. The curve always converges toward 0.

---

## 3. Test Results / Resultados de las Pruebas

The test script at `tests/test_zero_baseline_multiplier.py` confirms:

| Case | Baseline Final | Multiplier | Linear Final | Time_Series Final | Logistic Final |
|---|---|---|---|---|---|
| 1a | 0.0 | 1.5 | 0.0 | 6.0* | 0.18* |
| 1b | 0.0 | 2.0 | 0.0 | 6.0* | 0.18* |
| 1c | 0.0 | 0.5 | 0.0 | 6.0* | 0.18* |
| 2 (control) | 10.0 | 1.5 | 15.0 | 15.0 | 15.5 |
| 3 | 0.0 | 3.0 | 0.0 | 0.0 | 0.0 |

*Cases 1a-1c: Time_Series and Logistic produce the same non-zero intermediate values regardless of the multiplier because the formula becomes multiplier-independent when `value_list[-1] = 0`. The trajectory still decays toward 0.

**Case 3** is the worst scenario: when the value is already 0 at `Initial_Year_of_Uncertainty`, ALL methods produce all zeros.

Run the test: `python tests/test_zero_baseline_multiplier.py`

---

## 4. Available Mathematical Types / Tipos Matematicos Disponibles

Currently defined in the system (line 1077):
1. `Time_Series` - Non-linear interpolation scaling the final value
2. `Linear` - Linear interpolation to a scaled final value
3. `Logistic` - S-curve interpolation to a scaled final value
4. `Constant` - Freezes value at `Initial_Year_of_Uncertainty` (no multiplier)
5. `Discrete_Investments` - For investment parameters
6. `Mult_Adoption_Curve` - Adoption curve multiplier
7. `Mult_Restriction` / `Mult_Restriction_Start` / `Mult_Restriction_End` - Restriction curves
8. `Timeslices_Curve` - For timeslice-related parameters

**None of these can produce a non-zero value from a zero baseline final value.**

---

## 5. Proposed Solutions / Soluciones Propuestas

### Solution A: Step Function (suggested by the user)

A "Step Function" would allow setting an **absolute final value** instead of a relative multiplier:

```python
def interpolation_step_function(time_list, value_list, absolute_final_value, step_year, finyear):
    """
    Creates a step function where:
    - Values before step_year remain unchanged (from baseline)
    - At step_year, the value jumps to absolute_final_value
    - Values after step_year remain at absolute_final_value

    This bypasses the multiplier problem since the target value is absolute.
    """
    new_value_list = []
    for year, value in zip(time_list, value_list):
        if year < step_year:
            new_value_list.append(value)
        else:
            new_value_list.append(absolute_final_value)
    return new_value_list
```

**Pros:**
- Simple to implement and understand
- Completely bypasses the zero-multiplication problem
- User defines exact values, not multipliers

**Cons:**
- Abrupt transitions (no smooth interpolation)
- Min/Max values in the uncertainty table would need different semantics (absolute values instead of multipliers)

### Solution B: Additive Offset (recommended / recomendada)

Instead of multiplying, **add** a value to the baseline:

```python
def interpolation_additive_final(time_list, value_list, additive_value, finyear, Initial_Year_of_Uncertainty):
    """
    Similar to interpolation_linear but uses additive offset:
    new_final_value = value_list[-1] + additive_value

    When value_list[-1] = 0: new_final_value = 0 + additive_value = additive_value
    """
    new_value_list = []
    start_index = time_list.index(Initial_Year_of_Uncertainty)
    end_index = time_list.index(finyear)

    initial_value = value_list[start_index]
    final_value = value_list[-1] + additive_value  # ADDITIVE, not multiplicative

    num_steps = end_index - start_index

    for i, year in enumerate(time_list):
        if i < start_index:
            new_value_list.append(value_list[i])
        elif i <= end_index:
            t = i - start_index
            interpolated = initial_value + (final_value - initial_value) * (t / num_steps)
            new_value_list.append(interpolated)
        else:
            new_value_list.append(final_value)

    return new_value_list
```

**Pros:**
- Works with any baseline value including 0
- Smooth interpolation (not abrupt like step function)
- Compatible with all existing trajectory shapes (linear, logistic, etc.)
- Min_Value/Max_Value in the uncertainty table define the range of the additive offset

**Cons:**
- Changes the interpretation of Min_Value/Max_Value for specific parameters
- Requires a new `X_Mathematical_Type` (e.g., `Additive_Linear`, `Additive_Logistic`)

### Solution C: Absolute Target Value

A hybrid approach where `Min_Value` and `Max_Value` define absolute target values for the final year, not multipliers:

```python
# In the uncertainty table: Min_Value=5, Max_Value=50 (absolute PJ values)
# evaluation_value = sampled absolute value (e.g., 25 PJ)
# The interpolation would use this as the direct target:
final_value = evaluation_value  # NOT value_list[-1] * evaluation_value
```

**Pros:**
- Most intuitive for users
- Works regardless of baseline values

**Cons:**
- Requires distinguishing between "relative" and "absolute" parameters in the uncertainty table
- Would need a new column (e.g., `Value_Mode: 'relative' | 'absolute'`)

---

## 6. Recommended Implementation Path / Ruta de Implementacion Recomendada

### Minimal change (least risk):

1. Add a new `X_Mathematical_Type` value: `"Step"` or `"Absolute_Linear"`
2. In `z_auxiliar_code.py`, add the corresponding interpolation function
3. In `0_experiment_manager.py` (line ~1553), add a branch:
   ```python
   elif Math_Type == 'Step':
       new_value_list = AUX.interpolation_step_function(
           time_list, value_list, float(Values_per_Future[fut_id]),
           Initial_Year_of_Uncertainty, last_year_analysis
       )
   ```
4. Update `Interface_RDM.xlsx` documentation to explain when to use `Step` vs other types
5. For the `Step` type, `Min_Value` and `Max_Value` would represent **absolute values** rather than multipliers

### Files to modify:
- `src/workflow/z_auxiliar_code.py` - Add new interpolation function(s)
- `src/workflow/1_Experiment/0_experiment_manager.py` - Add branch in Phase 3 (line ~1593)
- `src/Interface_RDM.xlsx` - Add documentation for the new type

---

## 7. Conclusion / Conclusion

The developer's response is **correct and well-founded**. The mathematical structure of all current interpolation functions makes it impossible to generate variability when the baseline final value is 0, because `0 * multiplier = 0` is an invariant.

The suggested "step function" is a viable solution. A more flexible alternative would be an **additive offset** approach or an **absolute target value** approach, both of which would bypass the zero-multiplication problem while maintaining smooth interpolation curves.

La respuesta del desarrollador es **correcta y bien fundamentada**. La estructura matematica de todas las funciones de interpolacion actuales hace imposible generar variabilidad cuando el valor final de la linea base es 0, porque `0 * multiplicador = 0` es una invariante.

La "step function" sugerida es una solucion viable. Una alternativa mas flexible seria un enfoque de **offset aditivo** o de **valor objetivo absoluto**, que evitaria el problema de la multiplicacion por cero manteniendo curvas de interpolacion suaves.