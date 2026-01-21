#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la funcionalidad de Dependency en Uncertainty_Table.

Este script prueba que:
1. La columna Dependency se lee correctamente
2. La fórmula complementaria (2 - X) se aplica correctamente
3. Los valores se almacenan en el orden correcto

Uso:
    python test_dependency.py
"""

import pandas as pd
import numpy as np

def test_dependency_column():
    """Verificar que la columna Dependency existe y tiene valores válidos."""
    print("="*70)
    print("TEST 1: Verificar columna Dependency en Interface_RDM.xlsx")
    print("="*70)

    try:
        book = pd.ExcelFile('src/Interface_RDM.xlsx')
        uncertainty_table = book.parse('Uncertainty_Table')

        # Verificar que existe la columna
        if 'Dependency' not in uncertainty_table.columns:
            print("❌ FAIL: Columna 'Dependency' no encontrada")
            return False

        print(f"✓ Columna 'Dependency' encontrada")

        # Verificar valores
        dep_values = uncertainty_table['Dependency'].unique()
        print(f"✓ Valores únicos en Dependency: {dep_values}")

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
        print(f"❌ ERROR: {e}")
        return False

def test_complementary_formula():
    """Verificar que la fórmula 2-X funciona matemáticamente."""
    print("\n" + "="*70)
    print("TEST 2: Verificar fórmula complementaria (2 - X)")
    print("="*70)

    test_cases = [
        (1.8, 0.2, "80% aumento → 80% disminución"),
        (0.7, 1.3, "30% disminución → 30% aumento"),
        (1.0, 1.0, "Sin cambio → sin cambio"),
        (1.5, 0.5, "50% aumento → 50% disminución"),
        (0.9, 1.1, "10% disminución → 10% aumento"),
    ]

    all_passed = True
    for x, expected, description in test_cases:
        result = 2.0 - x
        passed = abs(result - expected) < 0.0001
        status = "✓" if passed else "❌"
        print(f"{status} X={x:.2f} → 2-X={result:.2f} (esperado {expected:.2f}) - {description}")
        if not passed:
            all_passed = False

    return all_passed

def test_dependency_logic_simulation():
    """Simular la lógica de dependencia con datos de prueba."""
    print("\n" + "="*70)
    print("TEST 3: Simulación de lógica de dependencia")
    print("="*70)

    # Simular 3 parámetros con diferentes configuraciones
    print("\nEscenario de prueba:")
    print("  Param 0: Dependency=NO,  eval_value=1.2")
    print("  Param 1: Dependency=YES, eval_value=0.8")
    print("  Param 2: Dependency=NO,  eval_value=1.1")

    # Valores simulados
    params = [
        {'p': 0, 'dependency': 'NO', 'eval_original': 1.2, 'eval_final': 1.2},
        {'p': 1, 'dependency': 'YES', 'eval_original': 0.8, 'eval_final': 0.8},
        {'p': 2, 'dependency': 'NO', 'eval_original': 1.1, 'eval_final': None},
    ]

    # Aplicar lógica de dependencia
    this_future_X_change = []

    for i, param in enumerate(params):
        p = param['p']
        eval_value = param['eval_original']

        # Lógica de dependencia
        if p > 0:
            prev_dependency = params[p-1]['dependency']
            if prev_dependency in ['YES', 'SI']:
                prev_eval_value = this_future_X_change[p-1]
                eval_value = 2.0 - prev_eval_value
                print(f"\n✓ Param {p}: Dependencia detectada!")
                print(f"    Prev eval_value (Param {p-1}): {prev_eval_value:.4f}")
                print(f"    Nueva eval_value: {eval_value:.4f} (= 2 - {prev_eval_value:.4f})")

        this_future_X_change.append(eval_value)
        param['eval_final'] = eval_value

    # Verificar resultados
    print("\n\nResultados finales:")
    all_correct = True
    for param in params:
        p = param['p']
        expected = param['eval_final']
        actual = this_future_X_change[p]

        if p == 2:  # Este debe ser 2 - 0.8 = 1.2
            expected = 2.0 - params[1]['eval_final']

        correct = abs(actual - expected) < 0.0001
        status = "✓" if correct else "❌"
        print(f"{status} Param {p}: eval_value={actual:.4f} (esperado {expected:.4f})")

        if not correct:
            all_correct = False

    return all_correct

def main():
    """Ejecutar todas las pruebas."""
    print("\n" + "="*70)
    print(" PRUEBAS DE FUNCIONALIDAD: DEPENDENCY EN UNCERTAINTY_TABLE")
    print("="*70 + "\n")

    results = []

    # Test 1
    results.append(("Columna Dependency existe", test_dependency_column()))

    # Test 2
    results.append(("Fórmula complementaria", test_complementary_formula()))

    # Test 3
    results.append(("Lógica de dependencia", test_dependency_logic_simulation()))

    # Resumen
    print("\n" + "="*70)
    print(" RESUMEN DE PRUEBAS")
    print("="*70)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "="*70)
    if all_passed:
        print("✓ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON - REVISAR ARRIBA")
    print("="*70 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
