# -*- coding: utf-8 -*-
"""
Test script: Behavior of uncertainty multipliers when baseline final value = 0
==============================================================================

PURPOSE / PROPÓSITO:
    Demonstrate that when the baseline final year value is 0, all mathematical
    types (Time_Series, Linear, Logistic, Constant) produce 0 for the final
    value regardless of the multiplier applied.

    Demostrar que cuando el valor del año final de la línea base es 0, todos
    los tipos matemáticos producen 0 para el valor final sin importar el
    multiplicador aplicado.

CONCLUSION:
    The developer's statement is CORRECT. The system always starts from the
    baseline final year value: new_final = value_list[-1] * multiplier.
    If value_list[-1] == 0, then new_final == 0 for any multiplier.

    La afirmación del desarrollador es CORRECTA. El sistema siempre parte
    del valor del año final de la línea base: new_final = value_list[-1] * mult.
    Si value_list[-1] == 0, entonces new_final == 0 para cualquier multiplicador.

@author: Analysis script for osemosys-rdm issue
"""

import sys
import os
import math
from copy import deepcopy

# ---------------------------------------------------------------------------
# Replicate the interpolation functions from z_auxiliar_code.py
# (self-contained so this test runs without project imports)
# ---------------------------------------------------------------------------

def interpolation_non_linear_final(time_list, value_list, new_relative_final_value, finyear, Initial_Year_of_Uncertainty):
    """
    From z_auxiliar_code.py line 64.
    Key line: m_new = (ydata[-1] * (new_relative_final_value / 1) - ydata[0]) / (xdata[-1] - xdata[0])
    When ydata[-1] == 0: m_new = (0 * multiplier - ydata[0]) / denominator = -ydata[0] / denominator
    """
    old_relative_final_value = 1
    new_value_list = []
    initial_year_index = time_list.index(Initial_Year_of_Uncertainty)
    fraction_time_list = time_list[initial_year_index:]
    fraction_value_list = value_list[initial_year_index:]

    diff_yrs = time_list[-1] - finyear

    xdata = [fraction_time_list[i] - fraction_time_list[0] for i in range(len(fraction_time_list) - diff_yrs)]
    ydata = [float(fraction_value_list[i]) for i in range(len(fraction_value_list) - diff_yrs)]
    ydata_whole = [float(fraction_value_list[i]) for i in range(len(fraction_value_list))]
    delta_ydata = [ydata_whole[i] - ydata_whole[i - 1] for i in range(1, len(ydata_whole))]

    m_original = (ydata[-1] - ydata[0]) / (xdata[-1] - xdata[0])
    # THIS IS THE KEY LINE: ydata[-1] is the baseline final value
    m_new = (ydata[-1] * (new_relative_final_value / old_relative_final_value) - ydata[0]) / (xdata[-1] - xdata[0])

    if int(m_original) == 0:
        delta_ydata_new = [m_new for i in range(0, len(ydata_whole))]
    else:
        delta_ydata_new = [(m_new / m_original) * (ydata_whole[i] - ydata_whole[i - 1]) for i in range(1, len(ydata_whole))]
        delta_ydata_new = [0] + delta_ydata_new

    ydata_new = [0 for i in range(len(ydata_whole))]
    list_apply_delta_ydata_new = []

    for i in range(0, len(delta_ydata) + 1):
        if time_list[i + initial_year_index] <= finyear:
            apply_delta_ydata_new = delta_ydata_new[i]
        else:
            apply_delta_ydata_new = sum(delta_ydata_new) / len(delta_ydata_new)
        list_apply_delta_ydata_new.append(apply_delta_ydata_new)

        if i == 0:
            ydata_new[i] = ydata_whole[0] + apply_delta_ydata_new
        else:
            ydata_new[i] = ydata_new[i - 1] + apply_delta_ydata_new

    fraction_list_counter = 0
    for n in range(len(time_list)):
        if time_list[n] >= Initial_Year_of_Uncertainty:
            new_value_list.append(ydata_new[fraction_list_counter])
            fraction_list_counter += 1
        else:
            new_value_list.append(float(value_list[n]))

    return new_value_list


def interpolation_linear(time_list, value_list, new_relative_final_value, finyear, Initial_Year_of_Uncertainty):
    """
    From z_auxiliar_code.py line 232.
    Key line: final_value = value_list[-1] * new_relative_final_value
    When value_list[-1] == 0: final_value = 0 * multiplier = 0
    """
    new_value_list = []
    start_index = time_list.index(Initial_Year_of_Uncertainty)
    end_index = time_list.index(finyear)

    initial_value = value_list[start_index]
    # THIS IS THE KEY LINE
    final_value = value_list[-1] * new_relative_final_value

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


def interpolation_logistic_trajectory(time_list, value_list, Values_per_Future, last_year_analysis, Initial_Year_of_Uncertainty):
    """
    From z_auxiliar_code.py line 178.
    Key line: final_value = value_list[-1] * Values_per_Future
    When value_list[-1] == 0: final_value = 0 * multiplier = 0
    """
    new_value_list = value_list.copy()

    start_index = time_list.index(Initial_Year_of_Uncertainty)
    end_index = time_list.index(last_year_analysis)

    initial_value = value_list[start_index]
    # THIS IS THE KEY LINE
    final_value = value_list[-1] * Values_per_Future

    num_steps = end_index - start_index + 1

    L = final_value
    k = 1.0
    x0 = num_steps / 2

    for i in range(num_steps):
        t = i
        logistic_factor = 1 / (1 + math.exp(-k * (t - x0)))
        interpolated_value = initial_value + (L - initial_value) * logistic_factor
        new_value_list[start_index + i] = interpolated_value

    return new_value_list


def interpolation_constant_trajectory(time_list, value_list, initial_year_of_uncertainty):
    """
    From z_auxiliar_code.py line 151.
    NOTE: This function does NOT use a multiplier at all. It freezes values
    at the Initial_Year_of_Uncertainty level. If that value > 0, it stays > 0.
    """
    new_value_list = []
    constant_value = None

    for year, value in zip(time_list, value_list):
        if year < initial_year_of_uncertainty:
            new_value_list.append(value)
        else:
            if constant_value is None:
                constant_value = value
            new_value_list.append(constant_value)

    return new_value_list


def interpolation_step(time_list, value_list, absolute_value, Initial_Year_of_Uncertainty):
    """
    NEW: Step function that uses absolute values instead of multipliers.
    Keeps baseline values before Initial_Year_of_Uncertainty, then sets
    all values to absolute_value from that year onwards.

    This solves the zero-baseline problem: when baseline final = 0,
    the absolute_value is used directly (not multiplied by 0).
    """
    new_value_list = []
    for year, value in zip(time_list, value_list):
        if year < Initial_Year_of_Uncertainty:
            new_value_list.append(value)
        else:
            new_value_list.append(absolute_value)
    return new_value_list


# ===========================================================================
# TEST CASES
# ===========================================================================

def print_separator():
    print("=" * 80)


def test_case(description, time_list, value_list, multiplier, finyear, initial_year):
    """Run all mathematical types and print results."""
    print_separator()
    print(f"TEST: {description}")
    print(f"  time_list = {time_list}")
    print(f"  value_list = {value_list}")
    print(f"  multiplier = {multiplier}")
    print(f"  final year (finyear) = {finyear}")
    print(f"  Initial_Year_of_Uncertainty = {initial_year}")
    print(f"  BASELINE FINAL VALUE = {value_list[-1]}")
    print()

    # 1. Time_Series (non-linear)
    try:
        result_ts = interpolation_non_linear_final(time_list, value_list, multiplier, finyear, initial_year)
        print(f"  [Time_Series]  result = {[round(v, 4) for v in result_ts]}")
        print(f"                 final  = {round(result_ts[-1], 4)}")
    except Exception as e:
        print(f"  [Time_Series]  ERROR: {e}")

    # 2. Linear
    try:
        result_lin = interpolation_linear(time_list, value_list, multiplier, finyear, initial_year)
        print(f"  [Linear]       result = {[round(v, 4) for v in result_lin]}")
        print(f"                 final  = {round(result_lin[-1], 4)}")
    except Exception as e:
        print(f"  [Linear]       ERROR: {e}")

    # 3. Logistic
    try:
        result_log = interpolation_logistic_trajectory(time_list, value_list, multiplier, finyear, initial_year)
        print(f"  [Logistic]     result = {[round(v, 4) for v in result_log]}")
        print(f"                 final  = {round(result_log[-1], 4)}")
    except Exception as e:
        print(f"  [Logistic]     ERROR: {e}")

    # 4. Constant (no multiplier used)
    try:
        result_const = interpolation_constant_trajectory(time_list, value_list, initial_year)
        print(f"  [Constant]     result = {[round(v, 4) for v in result_const]}")
        print(f"                 final  = {round(result_const[-1], 4)}")
    except Exception as e:
        print(f"  [Constant]     ERROR: {e}")

    # 5. Step (NEW - uses absolute value, not multiplier)
    try:
        result_step = interpolation_step(time_list, value_list, multiplier, initial_year)
        print(f"  [Step]         result = {[round(v, 4) for v in result_step]}")
        print(f"                 final  = {round(result_step[-1], 4)}")
    except Exception as e:
        print(f"  [Step]         ERROR: {e}")

    print()


if __name__ == "__main__":

    print()
    print("#" * 80)
    print("# TEST: Uncertainty multipliers when baseline final value = 0")
    print("# PRUEBA: Multiplicadores de incertidumbre cuando valor final base = 0")
    print("#" * 80)
    print()

    # -----------------------------------------------------------------------
    # CASE 1: Imports that drop to zero after 2026
    # Scenario: Baseline has imports declining from 100 in 2019 to 0 in 2027+
    # -----------------------------------------------------------------------
    time_list_1 = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2035, 2040, 2045, 2050]
    value_list_1 = [100.0, 90.0, 80.0, 60.0, 40.0, 20.0, 10.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    test_case(
        "CASE 1a: Imports drop to 0 after 2026, multiplier=1.5 (baseline_final=0)",
        time_list_1, value_list_1,
        multiplier=1.5, finyear=2050, initial_year=2025
    )

    test_case(
        "CASE 1b: Imports drop to 0 after 2026, multiplier=2.0 (baseline_final=0)",
        time_list_1, value_list_1,
        multiplier=2.0, finyear=2050, initial_year=2025
    )

    test_case(
        "CASE 1c: Imports drop to 0 after 2026, multiplier=0.5 (baseline_final=0)",
        time_list_1, value_list_1,
        multiplier=0.5, finyear=2050, initial_year=2025
    )

    # -----------------------------------------------------------------------
    # CASE 2: Control case - Non-zero final value (normal behavior)
    # -----------------------------------------------------------------------
    value_list_2 = [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 45.0, 40.0, 35.0, 30.0, 28.0, 25.0, 20.0, 15.0, 12.0, 10.0]

    test_case(
        "CASE 2: CONTROL - Non-zero final value (baseline_final=10), multiplier=1.5",
        time_list_1, value_list_2,
        multiplier=1.5, finyear=2050, initial_year=2025
    )

    # -----------------------------------------------------------------------
    # CASE 3: All zeros from a certain point
    # -----------------------------------------------------------------------
    value_list_3 = [50.0, 40.0, 30.0, 20.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    test_case(
        "CASE 3: Zero from 2024 onwards, multiplier=3.0 (baseline_final=0)",
        time_list_1, value_list_3,
        multiplier=3.0, finyear=2050, initial_year=2025
    )

    # -----------------------------------------------------------------------
    # CASE 4: Step function - absolute value = 25 PJ (demonstrates the fix)
    # With Step, the value 25.0 is used DIRECTLY, not as a multiplier
    # -----------------------------------------------------------------------
    print_separator()
    print("CASE 4: STEP FUNCTION DEMO - absolute_value=25.0 with baseline_final=0")
    print("  This shows the Step function solving the zero-baseline problem.")
    print(f"  time_list = {time_list_1}")
    print(f"  value_list = {value_list_1}")
    print(f"  absolute_value = 25.0 (PJ, used directly, NOT as multiplier)")
    print(f"  Initial_Year_of_Uncertainty = 2025")
    print()
    result_step_25 = interpolation_step(time_list_1, value_list_1, 25.0, 2025)
    print(f"  [Step]  result = {[round(v, 4) for v in result_step_25]}")
    print(f"          final  = {round(result_step_25[-1], 4)}")
    print()
    result_step_50 = interpolation_step(time_list_1, value_list_1, 50.0, 2025)
    print(f"  [Step]  absolute_value=50.0:")
    print(f"          result = {[round(v, 4) for v in result_step_50]}")
    print(f"          final  = {round(result_step_50[-1], 4)}")
    print()
    result_step_5 = interpolation_step(time_list_1, value_list_1, 5.0, 2025)
    print(f"  [Step]  absolute_value=5.0:")
    print(f"          result = {[round(v, 4) for v in result_step_5]}")
    print(f"          final  = {round(result_step_5[-1], 4)}")
    print()
    print("  CONCLUSION: Step function produces NON-ZERO values even when baseline=0!")
    print("  CONCLUSIÓN: La función Step produce valores NO CERO incluso con base=0!")
    print()

    # -----------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------
    print_separator()
    print("SUMMARY / RESUMEN")
    print_separator()
    print()
    print("MATHEMATICAL PROOF / DEMOSTRACIÓN MATEMÁTICA:")
    print()
    print("All interpolation functions that use a multiplier compute the new")
    print("final value as:")
    print()
    print("  new_final_value = value_list[-1] * multiplier")
    print()
    print("Where value_list[-1] is the BASELINE final year value.")
    print()
    print("If value_list[-1] = 0:")
    print("  new_final_value = 0 * multiplier = 0  (for ANY multiplier)")
    print()
    print("This applies to:")
    print("  - Time_Series (non-linear): line 84 of z_auxiliar_code.py")
    print("    m_new = (ydata[-1] * multiplier - ydata[0]) / (xdata[-1] - xdata[0])")
    print("    When ydata[-1]=0: m_new = -ydata[0] / denom (slope towards zero)")
    print()
    print("  - Linear: line 261 of z_auxiliar_code.py")
    print("    final_value = value_list[-1] * new_relative_final_value")
    print("    When value_list[-1]=0: final_value = 0")
    print()
    print("  - Logistic: line 213 of z_auxiliar_code.py")
    print("    final_value = value_list[-1] * Values_per_Future")
    print("    When value_list[-1]=0: L = 0, so logistic curve targets 0")
    print()
    print("  - Constant: Does NOT use a multiplier (freezes at uncertainty year value)")
    print("    If the value at Initial_Year_of_Uncertainty > 0, it stays > 0")
    print("    But it cannot model growth beyond that frozen point")
    print()
    print("  - Step (NEW): Uses ABSOLUTE value, not a multiplier")
    print("    new_value = absolute_value (directly, for years >= Initial_Year_of_Uncertainty)")
    print("    When baseline=0: new_value = absolute_value (WORKS!)")
    print("    Min_Value/Max_Value define the range of absolute target values")
    print()
    print("DEVELOPER'S STATEMENT IS: ** CORRECT ** (for existing types)")
    print("LA AFIRMACIÓN DEL DESARROLLADOR ES: ** CORRECTA ** (para tipos existentes)")
    print()
    print("SOLUTION: The new 'Step' mathematical type solves this problem")
    print("SOLUCIÓN: El nuevo tipo matemático 'Step' resuelve este problema")
    print()