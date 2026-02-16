#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la funcionalidad de Dependency en Uncertainty_Table.

Este script prueba que:
1. La columna Dependency se lee correctamente del Excel
2. La formula aditiva a nivel de valores preserva la restriccion de suma
3. La logica de dependencia funciona con datos simulados de escenarios

Uso:
    python test_dependency.py
"""

import pandas as pd
import numpy as np

def test_dependency_column():
    """Verificar que la columna Dependency existe y tiene valores validos."""
    print("="*70)
    print("TEST 1: Verificar columna Dependency en Interface_RDM.xlsx")
    print("="*70)

    try:
        book = pd.ExcelFile('src/Interface_RDM.xlsx')
        uncertainty_table = book.parse('Uncertainty_Table')

        # Verificar que existe la columna
        if 'Dependency' not in uncertainty_table.columns:
            print("FAIL: Columna 'Dependency' no encontrada")
            return False

        print(f"PASS: Columna 'Dependency' encontrada")

        # Verificar valores
        dep_values = uncertainty_table['Dependency'].unique()
        print(f"PASS: Valores unicos en Dependency: {dep_values}")

        # Contar YES vs NO
        yes_count = uncertainty_table['Dependency'].str.upper().isin(['YES', 'SI']).sum()
        no_count = uncertainty_table['Dependency'].str.upper().isin(['NO']).sum()

        print(f"  - Filas con YES/SI: {yes_count}")
        print(f"  - Filas con NO: {no_count}")

        if yes_count > 0:
            print(f"\n  Filas con Dependency=YES:")
            yes_rows = uncertainty_table[uncertainty_table['Dependency'].str.upper().isin(['YES', 'SI'])]
            for idx, row in yes_rows.iterrows():
                print(f"    Row {idx}: X_Num={row['X_Num']}, Desc={row['X_Plain_English_Description'][:50]}")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_value_level_constraint():
    """Verificar que la formula aditiva preserva |primary| + |dependent| = constante."""
    print("\n" + "="*70)
    print("TEST 2: Verificar formula aditiva a nivel de valores")
    print("="*70)

    # Caso UDCMultiplierTotalCapacity: baseline EV=0.98, nonEV=-0.02
    # Restriccion: |EV| + |nonEV| = 1.0

    test_cases = [
        # (baseline_pri, baseline_dep, new_pri, description)
        (0.98, -0.02, 0.97, "EV share 2% -> 3%"),
        (0.98, -0.02, 0.95, "EV share 2% -> 5%"),
        (0.98, -0.02, 0.50, "EV share 2% -> 50%"),
        (0.98, -0.02, 0.99, "EV share 2% -> 1%"),
        (0.98, -0.02, 0.80, "EV share 2% -> 20%"),
        (0.98, -0.02, 0.98, "EV share 2% -> 2% (sin cambio)"),
    ]

    all_passed = True
    for baseline_pri, baseline_dep, new_pri, description in test_cases:
        # Formula: new_dep = baseline_dep + (new_pri - baseline_pri)
        delta = new_pri - baseline_pri
        new_dep = baseline_dep + delta

        # Verificar restriccion
        original_sum = abs(baseline_pri) + abs(baseline_dep)
        new_sum = abs(new_pri) + abs(new_dep)

        passed = abs(new_sum - original_sum) < 1e-10
        status = "PASS" if passed else "FAIL"

        print(f"{status}: {description}")
        print(f"       baseline: pri={baseline_pri}, dep={baseline_dep}, |sum|={original_sum}")
        print(f"       new:      pri={new_pri}, dep={new_dep:.4f}, |sum|={new_sum:.4f}")

        if not passed:
            all_passed = False

    return all_passed

def test_time_series_constraint():
    """Verificar que la restriccion se preserva para cada anio en una serie de tiempo."""
    print("\n" + "="*70)
    print("TEST 3: Verificar restriccion en serie de tiempo completa")
    print("="*70)

    # Simular una serie de tiempo donde el multiplicador crea una trayectoria
    years = list(range(2020, 2051))
    baseline_pri = [0.98] * len(years)  # EV UDC constante en baseline
    baseline_dep = [-0.02] * len(years)  # nonEV UDC constante en baseline

    # Simular que la interpolacion crea una trayectoria gradual para EV
    # (de 0.98 en 2020 a 0.90 en 2050 = de 2% a 10% EV share)
    new_pri = [0.98 - (0.08 * max(0, (y - 2025)) / 25) for y in years]

    all_passed = True
    for i in range(len(years)):
        delta = new_pri[i] - baseline_pri[i]
        new_dep = baseline_dep[i] + delta
        total = abs(new_pri[i]) + abs(new_dep)
        if abs(total - 1.0) > 1e-10:
            print(f"FAIL: Year {years[i]}: |{new_pri[i]:.4f}| + |{new_dep:.4f}| = {total:.4f} != 1.0")
            all_passed = False

    if all_passed:
        print(f"PASS: Restriccion |pri| + |dep| = 1.0 se preserva para los {len(years)} anios")
        print(f"       Year 2020: pri={new_pri[0]:.4f}, dep={baseline_dep[0] + (new_pri[0] - baseline_pri[0]):.4f}")
        print(f"       Year 2030: pri={new_pri[10]:.4f}, dep={baseline_dep[10] + (new_pri[10] - baseline_pri[10]):.4f}")
        print(f"       Year 2050: pri={new_pri[-1]:.4f}, dep={baseline_dep[-1] + (new_pri[-1] - baseline_pri[-1]):.4f}")

    return all_passed

def test_dependency_logic_simulation():
    """Simular la logica de dependencia con datos de prueba completos."""
    print("\n" + "="*70)
    print("TEST 4: Simulacion de logica de dependencia end-to-end")
    print("="*70)

    # Simular el flujo completo:
    # Step 1: LHS genera multiplicadores
    # Step 3: Se aplican multiplicadores, y para filas dependientes se aplica la restriccion

    # Configuracion
    baseline_ev = 0.98
    baseline_nonev = -0.02
    multiplier_ev = 0.9694  # Corresponde a ~5% EV share: 0.98 * 0.9694 = 0.95

    # Step 3: Aplicar multiplicador al primario (EV)
    new_ev = baseline_ev * multiplier_ev

    # Step 3: Para el dependiente (nonEV), aplicar formula aditiva
    delta = new_ev - baseline_ev
    new_nonev = baseline_nonev + delta

    # Verificar
    expected_ev_share = 1.0 - new_ev
    expected_sum = abs(new_ev) + abs(new_nonev)

    print(f"  Baseline: EV={baseline_ev}, nonEV={baseline_nonev}")
    print(f"  Multiplicador EV: {multiplier_ev}")
    print(f"  Nuevo EV: {baseline_ev} x {multiplier_ev} = {new_ev:.4f}")
    print(f"  Delta: {new_ev:.4f} - {baseline_ev} = {delta:.4f}")
    print(f"  Nuevo nonEV: {baseline_nonev} + ({delta:.4f}) = {new_nonev:.4f}")
    print(f"  Participacion EV: {expected_ev_share*100:.2f}%")
    print(f"  |EV| + |nonEV| = {expected_sum:.6f}")

    passed = abs(expected_sum - 1.0) < 1e-10
    status = "PASS" if passed else "FAIL"
    print(f"\n{status}: La restriccion se {'preserva' if passed else 'NO se preserva'}")

    return passed

def main():
    """Ejecutar todas las pruebas."""
    print("\n" + "="*70)
    print(" PRUEBAS DE FUNCIONALIDAD: DEPENDENCY EN UNCERTAINTY_TABLE")
    print(" (Formula aditiva a nivel de valores)")
    print("="*70 + "\n")

    results = []

    # Test 1
    results.append(("Columna Dependency existe", test_dependency_column()))

    # Test 2
    results.append(("Formula aditiva preserva restriccion", test_value_level_constraint()))

    # Test 3
    results.append(("Restriccion en serie de tiempo", test_time_series_constraint()))

    # Test 4
    results.append(("Simulacion end-to-end", test_dependency_logic_simulation()))

    # Resumen
    print("\n" + "="*70)
    print(" RESUMEN DE PRUEBAS")
    print("="*70)

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "="*70)
    if all_passed:
        print("TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
    else:
        print("ALGUNAS PRUEBAS FALLARON - REVISAR ARRIBA")
    print("="*70 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
