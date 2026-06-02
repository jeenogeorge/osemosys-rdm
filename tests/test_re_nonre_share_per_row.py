"""Unit test sintético para fix_re_nonre_share_per_row.

Carga la función desde 0_experiment_manager.py sin ejecutar el script entero,
construye un experiment_dictionary mínimo + un inherited_scenarios con datos
sintéticos, invoca el fixer y verifica el invariante POR-COEFICIENTE por (R, Y):

  |mean(RE_values)| + coef_NonRE == Sum_To_Value

(cada non-RE queda en Sum_To_Value - |mean(RE)|, igual que Path B).
"""
from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "src" / "workflow" / "1_Experiment" / "0_experiment_manager.py"


def load_fixer():
    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "fix_re_nonre_share_per_row":
            func_src = ast.get_source_segment(src, node)
            break
    else:
        raise RuntimeError("Función fix_re_nonre_share_per_row no encontrada")

    import os  # noqa: F401 — usada por la función
    ns = {"os": os, "__name__": "fixer_under_test"}
    exec(func_src, ns)
    return ns["fix_re_nonre_share_per_row"]


def make_param_data(entries):
    """entries: list of (r, t, y, u, value). 'u' es el second-set (UDC)."""
    return {
        "r": [r for (r, _t, _y, _u, _v) in entries],
        "t": [t for (_r, t, _y, _u, _v) in entries],
        "y": [y for (_r, _t, y, _u, _v) in entries],
        "u": [u for (_r, _t, _y, u, _v) in entries],
        "value": [v for (_r, _t, _y, _u, v) in entries],
    }


def assert_share(pdata, re_techs, nonre_techs, expected, year_filter=None):
    """Verifica el invariante por-coeficiente |mean(RE)| + coef_NonRE == expected.

    Para cada (R, Y): calcula |mean(valores RE)| y comprueba que cada non-RE
    quede en expected - |mean(RE)|.
    """
    re_set = set(re_techs)
    nonre_set = set(nonre_techs)
    re_vals = {}
    nonre_vals = {}
    for i, v in enumerate(pdata["value"]):
        r = pdata["r"][i]
        t = pdata["t"][i]
        y = pdata["y"][i]
        if year_filter is not None and int(y) < year_filter:
            continue
        if t in re_set:
            re_vals.setdefault((r, y), []).append(float(v))
        elif t in nonre_set:
            nonre_vals.setdefault((r, y), []).append(float(v))
    pairs = set(re_vals) & set(nonre_vals)
    for (r, y) in pairs:
        re_coef = abs(sum(re_vals[(r, y)]) / len(re_vals[(r, y)]))
        expected_nonre = expected - re_coef
        for nv in nonre_vals[(r, y)]:
            assert abs(nv - expected_nonre) < 1e-9, \
                f"({r}, {y}): non-RE {nv} != {expected_nonre} (|mean(RE)|={re_coef})"
    return len(pairs)


def test_basic_sum_to_one(fixer):
    """Caso típico: RE perturbado a -0.5, cada non-RE debe quedar en 1.0-0.5=0.5."""
    entries = []
    # RE: 8 techs todos a -0.5 (ya perturbados)
    re_techs = ["PWRSOL001", "PWRBIO001", "PWRWND001", "PWRWND001S",
                "PWRCSP002", "PWRCSP001", "PWRSOL001S", "PWRGEO"]
    nonre_techs = ["PWRCBM001", "PWRCOA003", "PWRCOA_CCS", "PWRBIO_CCS",
                   "PWRNGS001", "PWRCOA001", "PWRNGS002",
                   "PWROHC002", "PWROHC003", "PWRNUC",
                   "PWRDSL", "PWRLFG001", "PWRCOA002"]
    for y in ("2030", "2035"):
        for t in re_techs:
            entries.append(("RE1", t, y, "PWRREN", -0.5))
        for t in nonre_techs:
            entries.append(("RE1", t, y, "PWRREN", 0.7))  # no ajustado todavía

    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": re_techs,
            "NonRE_Techs": nonre_techs,
            "Sum_To_Value": 1.0,
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    corrections = fixer(inh, ["ScenA"], [1], exp_dict, log_dir=None)
    pdata = inh["ScenA"][1]["UDCMultiplierActivity"]
    n_pairs = assert_share(pdata, re_techs, nonre_techs, 1.0)
    assert n_pairs == 2, f"esperados 2 (R,Y) pairs, got {n_pairs}"

    # Cada non-RE debe ser 1.0 - |mean(RE)| = 1.0 - 0.5 = 0.5
    expected_nonre = 1.0 - abs(-0.5)
    for i, t in enumerate(pdata["t"]):
        if t in nonre_techs:
            assert abs(float(pdata["value"][i]) - expected_nonre) < 1e-9, \
                f"NonRE {t} = {pdata['value'][i]}, expected {expected_nonre}"
    print("  test_basic_sum_to_one: OK")


def test_default_sum_to_value(fixer):
    """Si Sum_To_Value es None, default 1.0."""
    entries = [("RE1", "PWRSOL001", "2030", "PWRREN", -0.4),
               ("RE1", "PWRCBM001", "2030", "PWRREN", 0.5)]
    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": ["PWRSOL001"],
            "NonRE_Techs": ["PWRCBM001"],
            "Sum_To_Value": None,  # debe defaultear a 1.0
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    fixer(inh, ["ScenA"], [1], exp_dict, log_dir=None)
    pdata = inh["ScenA"][1]["UDCMultiplierActivity"]
    # Expected: NonRE = 1.0 - |-0.4| = 0.6
    nonre_val = float(pdata["value"][1])
    assert abs(nonre_val - 0.6) < 1e-9, f"NonRE={nonre_val}, expected 0.6"
    print("  test_default_sum_to_value: OK")


def test_custom_sum_to_value(fixer):
    """Sum_To_Value distinto de 1.0."""
    entries = [("RE1", "PWRSOL001", "2030", "PWRREN", -0.2),
               ("RE1", "PWRCBM001", "2030", "PWRREN", 0.5),
               ("RE1", "PWRNGS001", "2030", "PWRREN", 0.5)]
    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": ["PWRSOL001"],
            "NonRE_Techs": ["PWRCBM001", "PWRNGS001"],
            "Sum_To_Value": 0.5,
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    fixer(inh, ["ScenA"], [1], exp_dict, log_dir=None)
    pdata = inh["ScenA"][1]["UDCMultiplierActivity"]
    # Expected: cada non-RE = 0.5 - |-0.2| = 0.3
    for i, t in enumerate(pdata["t"]):
        if t in ("PWRCBM001", "PWRNGS001"):
            assert abs(float(pdata["value"][i]) - 0.3) < 1e-9, \
                f"NonRE {t} = {pdata['value'][i]}, expected 0.3"
    print("  test_custom_sum_to_value: OK")


def test_year_filter(fixer):
    """Solo años >= Initial_Year_of_Uncertainty deben corregirse."""
    entries = [
        ("RE1", "PWRSOL001", "2025", "PWRREN", -0.3),
        ("RE1", "PWRCBM001", "2025", "PWRREN", 0.7),
        ("RE1", "PWRSOL001", "2030", "PWRREN", -0.5),
        ("RE1", "PWRCBM001", "2030", "PWRREN", 0.7),
    ]
    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": ["PWRSOL001"],
            "NonRE_Techs": ["PWRCBM001"],
            "Sum_To_Value": 1.0,
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    fixer(inh, ["ScenA"], [1], exp_dict, log_dir=None)
    pdata = inh["ScenA"][1]["UDCMultiplierActivity"]
    # 2025 no debe haberse tocado: PWRCBM001=0.7
    # 2030 sí: PWRCBM001 = 1.0 - |-0.5| = 0.5
    assert abs(float(pdata["value"][1]) - 0.7) < 1e-9, "2025 no debió tocarse"
    assert abs(float(pdata["value"][3]) - 0.5) < 1e-9, "2030 debió corregirse a 0.5"
    print("  test_year_filter: OK")


def test_opt_in_no_re_techs(fixer):
    """Una fila con RE_Techs vacío no activa el fixer."""
    entries = [("RE1", "PWRSOL001", "2030", "PWRREN", -0.5),
               ("RE1", "PWRCBM001", "2030", "PWRREN", 0.5)]
    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": [],
            "NonRE_Techs": ["PWRCBM001"],
            "Sum_To_Value": 1.0,
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    corrections = fixer(inh, ["ScenA"], [1], exp_dict, log_dir=None)
    assert corrections == [], "No debió aplicarse ninguna corrección"
    # PWRCBM001 debe seguir en 0.5
    pdata = inh["ScenA"][1]["UDCMultiplierActivity"]
    assert abs(float(pdata["value"][1]) - 0.5) < 1e-9
    print("  test_opt_in_no_re_techs: OK")


def test_no_op_when_already_satisfies(fixer):
    """Si los valores ya satisfacen el invariante, no debe haber correcciones."""
    # non-RE ya en 1.0 - |-0.5| = 0.5 -> sin corrección
    entries = [("RE1", "PWRSOL001", "2030", "PWRREN", -0.5),
               ("RE1", "PWRCBM001", "2030", "PWRREN", 0.5)]
    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": ["PWRSOL001"],
            "NonRE_Techs": ["PWRCBM001"],
            "Sum_To_Value": 1.0,
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    corrections = fixer(inh, ["ScenA"], [1], exp_dict, log_dir=None)
    assert corrections == [], f"No debería haber correcciones, got {corrections}"
    print("  test_no_op_when_already_satisfies: OK")


def test_multiple_second_sets(fixer):
    """Dos UDC en la misma fila: ambos deben corregirse independientemente.

    Regresión del bug 'solo se lee el primer second-set' + colisión de claves:
    el mismo tech aparece bajo PWRREN y PWRREN2 en el mismo (R, Y) pero con
    valores RE distintos, así que cada UDC tiene un target non-RE distinto.
      - PWRREN : RE=-0.3 -> non-RE = 1.0 - 0.3 = 0.7
      - PWRREN2: RE=-0.6 -> non-RE = 1.0 - 0.6 = 0.4
    Con el código viejo PWRREN2 quedaba intacto (en 0.9).
    """
    entries = [
        # UDC PWRREN
        ("RE1", "PWRSOL001", "2030", "PWRREN", -0.3),
        ("RE1", "PWRCBM001", "2030", "PWRREN", 0.9),   # debe pasar a 0.7
        # UDC PWRREN2 (mismo tech, mismo (R,Y), valor RE distinto)
        ("RE1", "PWRSOL001", "2030", "PWRREN2", -0.6),
        ("RE1", "PWRCBM001", "2030", "PWRREN2", 0.9),  # debe pasar a 0.4
    ]
    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": ["PWRSOL001"],
            "NonRE_Techs": ["PWRCBM001"],
            "Sum_To_Value": 1.0,
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN", "PWRREN2"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    corrections = fixer(inh, ["ScenA"], [1], exp_dict, log_dir=None)
    pdata = inh["ScenA"][1]["UDCMultiplierActivity"]
    # index 1 = non-RE bajo PWRREN, index 3 = non-RE bajo PWRREN2
    assert abs(float(pdata["value"][1]) - 0.7) < 1e-9, \
        f"PWRREN non-RE = {pdata['value'][1]}, expected 0.7"
    assert abs(float(pdata["value"][3]) - 0.4) < 1e-9, \
        f"PWRREN2 non-RE = {pdata['value'][3]}, expected 0.4 (segundo UDC ignorado por el bug)"
    assert len(corrections) == 2, f"esperadas 2 correcciones (una por UDC), got {len(corrections)}"
    print("  test_multiple_second_sets: OK")


def test_log_written(fixer):
    """Si hay correcciones y log_dir, debe escribirse el log."""
    entries = [("RE1", "PWRSOL001", "2030", "PWRREN", -0.5),
               ("RE1", "PWRCBM001", "2030", "PWRREN", 0.7)]
    inh = {"ScenA": {1: {"UDCMultiplierActivity": make_param_data(entries)}}}
    exp_dict = {
        18: {
            "RE_Techs": ["PWRSOL001"],
            "NonRE_Techs": ["PWRCBM001"],
            "Sum_To_Value": 1.0,
            "Exact_Parameters_Involved_in_Osemosys": ["UDCMultiplierActivity"],
            "Involved_Second_Sets_in_Osemosys": ["PWRREN"],
            "Initial_Year_of_Uncertainty": 2030,
        }
    }
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        fixer(inh, ["ScenA"], [1], exp_dict, log_dir=str(td_path))
        log_path = td_path / "re_nonre_share_corrections.log"
        assert log_path.exists(), f"log no escrito en {log_path}"
        content = log_path.read_text()
        assert "x_num,scenario,future,region,year,tech,old,new" in content
        assert "18,ScenA,1,RE1,2030,PWRCBM001" in content
    print("  test_log_written: OK")


def main() -> int:
    fixer = load_fixer()
    failures = 0
    for name, test in [
        ("test_basic_sum_to_one", test_basic_sum_to_one),
        ("test_default_sum_to_value", test_default_sum_to_value),
        ("test_custom_sum_to_value", test_custom_sum_to_value),
        ("test_year_filter", test_year_filter),
        ("test_opt_in_no_re_techs", test_opt_in_no_re_techs),
        ("test_no_op_when_already_satisfies", test_no_op_when_already_satisfies),
        ("test_multiple_second_sets", test_multiple_second_sets),
        ("test_log_written", test_log_written),
    ]:
        try:
            test(fixer)
        except AssertionError as e:
            failures += 1
            print(f"  {name}: FAIL — {e}")
        except Exception as e:
            failures += 1
            print(f"  {name}: ERROR — {type(e).__name__}: {e}")

    if failures == 0:
        print("\nTODOS LOS TESTS PASAN (fixer per-row funcional)")
        return 0
    print(f"\n{failures} test(s) fallidos")
    return 1


if __name__ == "__main__":
    sys.exit(main())
