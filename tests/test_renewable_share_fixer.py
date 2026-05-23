"""Unit test sintético para fix_renewable_share_consistency.

No requiere modelo OSeMOSYS real ni Setup.RE_Param populadas. Construye un
inherited_scenarios mínimo, invoca el fixer y verifica:
  1. Tras el fix, RE + nonRE == 1.0 para cada (region, year) emparejado.
  2. Los valores RE se mantuvieron intactos (RE es la fuente de verdad).
  3. Se generó el .log con las correcciones esperadas.
  4. Sin pares (R, Y) duplicados o desalineados.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "src" / "workflow" / "1_Experiment" / "0_experiment_manager.py"


def load_fixer():
    """Carga fix_renewable_share_consistency sin ejecutar el script principal.

    El módulo `0_experiment_manager.py` ejecuta código de top-level si se importa
    como script. Aquí lo cargamos como módulo en isolation y extraemos solo la
    función que necesitamos.
    """
    spec = importlib.util.spec_from_file_location("exp_manager_module", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo crear spec para {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)

    # Evitar que el módulo intente ejecutar la lógica main al cargar:
    # le ponemos sys.argv mínimo y rezamos. Como alternativa más segura,
    # extraemos solo el código fuente de la función.
    import ast
    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    func_src = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "fix_renewable_share_consistency":
            func_src = ast.get_source_segment(src, node)
            break
    if func_src is None:
        raise RuntimeError("No se encontró la función fix_renewable_share_consistency")

    # Ejecutar la función en namespace aislado con los imports que necesita
    import os  # noqa: F401  — usado por la función
    ns = {"os": os, "__name__": "fixer_under_test"}
    exec(func_src, ns)
    return ns["fix_renewable_share_consistency"]


def make_scenarios(re_values, nonre_values):
    """Construye inherited_scenarios sintético.

    re_values / nonre_values: lista de (region, year, value).
    """
    re_data = {
        "r": [r for (r, _y, _v) in re_values],
        "y": [y for (_r, y, _v) in re_values],
        "value": [v for (_r, _y, v) in re_values],
    }
    nonre_data = {
        "r": [r for (r, _y, _v) in nonre_values],
        "y": [y for (_r, y, _v) in nonre_values],
        "value": [v for (_r, _y, v) in nonre_values],
    }
    return {
        "ScenA": {
            1: {"REMinShare": re_data, "NonREMaxShare": nonre_data},
        }
    }


def test_basic_correction(fixer, tmp_log_dir):
    """RE + nonRE inicialmente NO suman 1; tras fix, sí."""
    inh = make_scenarios(
        re_values=[("RE1", "2030", 0.3), ("RE1", "2035", 0.5), ("RE1", "2040", 0.7)],
        nonre_values=[("RE1", "2030", 0.5), ("RE1", "2035", 0.4), ("RE1", "2040", 0.2)],
    )
    corrections = fixer(inh, ["ScenA"], [1], "REMinShare", "NonREMaxShare",
                       log_dir=str(tmp_log_dir))

    # 1. Suma 1.0 por (R, Y) post-fix
    re = inh["ScenA"][1]["REMinShare"]
    nonre = inh["ScenA"][1]["NonREMaxShare"]
    for i, (r, y) in enumerate(zip(re["r"], re["y"])):
        # buscar j en nonre con mismos (r, y)
        j = next(k for k, (rr, yy) in enumerate(zip(nonre["r"], nonre["y"]))
                if rr == r and yy == y)
        total = re["value"][i] + nonre["value"][j]
        assert abs(total - 1.0) < 1e-9, f"(R={r}, Y={y}) suma={total} != 1.0"

    # 2. RE intacto (es la fuente de verdad)
    assert re["value"] == [0.3, 0.5, 0.7], f"RE alterado: {re['value']}"

    # 3. Tres correcciones registradas
    assert len(corrections) == 3, f"esperadas 3 correcciones, got {len(corrections)}"

    # 4. Log escrito
    log_path = tmp_log_dir / "renewable_share_corrections.log"
    assert log_path.exists(), f"log no escrito en {log_path}"
    log_content = log_path.read_text()
    assert "scenario,future,region,year,old,new" in log_content
    assert "ScenA,1,RE1,2030" in log_content

    print("  test_basic_correction: OK")


def test_no_correction_needed(fixer, tmp_log_dir):
    """Si RE + nonRE ya suman 1, no debe haber cambios."""
    inh = make_scenarios(
        re_values=[("RE1", "2030", 0.4)],
        nonre_values=[("RE1", "2030", 0.6)],
    )
    corrections = fixer(inh, ["ScenA"], [1], "REMinShare", "NonREMaxShare",
                       log_dir=str(tmp_log_dir))
    assert corrections == [], f"esperadas 0 correcciones, got {corrections}"
    assert inh["ScenA"][1]["NonREMaxShare"]["value"] == [0.6]
    print("  test_no_correction_needed: OK")


def test_partial_match(fixer, tmp_log_dir):
    """Si nonRE no tiene (R, Y) presente en RE, se ignora ese índice."""
    inh = make_scenarios(
        re_values=[("RE1", "2030", 0.3), ("RE2", "2030", 0.4)],
        nonre_values=[("RE1", "2030", 0.5)],  # solo RE1
    )
    corrections = fixer(inh, ["ScenA"], [1], "REMinShare", "NonREMaxShare",
                       log_dir=None)
    # Solo se corrige (RE1, 2030)
    assert len(corrections) == 1, f"esperadas 1 corrección, got {len(corrections)}"
    assert corrections[0][2:4] == ("RE1", "2030")
    print("  test_partial_match: OK")


def test_missing_params(fixer, tmp_log_dir):
    """Si re_param o nonre_param no existen en inherited_scenarios, no falla."""
    inh = {"ScenA": {1: {"OtroParam": {"r": [], "y": [], "value": []}}}}
    corrections = fixer(inh, ["ScenA"], [1], "REMinShare", "NonREMaxShare", log_dir=None)
    assert corrections == []
    print("  test_missing_params: OK")


def test_multiple_regions(fixer, tmp_log_dir):
    """Múltiples regiones y años, alineamiento correcto."""
    inh = make_scenarios(
        re_values=[
            ("RE1", "2030", 0.3), ("RE1", "2035", 0.5),
            ("RE2", "2030", 0.2), ("RE2", "2035", 0.6),
        ],
        nonre_values=[
            ("RE1", "2030", 0.99), ("RE1", "2035", 0.99),
            ("RE2", "2030", 0.99), ("RE2", "2035", 0.99),
        ],
    )
    fixer(inh, ["ScenA"], [1], "REMinShare", "NonREMaxShare", log_dir=None)
    expected = [0.7, 0.5, 0.8, 0.4]  # 1 - RE en mismo orden
    got = inh["ScenA"][1]["NonREMaxShare"]["value"]
    assert all(abs(g - e) < 1e-9 for g, e in zip(got, expected)), f"got {got}, expected {expected}"
    print("  test_multiple_regions: OK")


def main() -> int:
    fixer = load_fixer()
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for name, test in [
            ("test_basic_correction", test_basic_correction),
            ("test_no_correction_needed", test_no_correction_needed),
            ("test_partial_match", test_partial_match),
            ("test_missing_params", test_missing_params),
            ("test_multiple_regions", test_multiple_regions),
        ]:
            sub = td_path / name
            sub.mkdir(exist_ok=True)
            try:
                test(fixer, sub)
            except AssertionError as e:
                failures += 1
                print(f"  {name}: FAIL — {e}")
            except Exception as e:
                failures += 1
                print(f"  {name}: ERROR — {type(e).__name__}: {e}")

    if failures == 0:
        print("\nTODOS LOS TESTS PASAN (fixer 3b funcional)")
        return 0
    print(f"\n{failures} test(s) fallidos")
    return 1


if __name__ == "__main__":
    sys.exit(main())
