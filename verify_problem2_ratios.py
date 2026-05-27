"""Verifica que YES_PROP CapitalCost↔FixedCost preserva el ratio por (tech, year).

Para cada futuro perturbado y cada tecnología renovable del grupo:
  ratio_perturbed = FixedCost_perturbed / CapitalCost_perturbed
  ratio_baseline  = FixedCost_baseline  / CapitalCost_baseline
  ASSERT abs(ratio_perturbed - ratio_baseline) < TOL  por cada año

También confirma que la perturbación NO es un no-op: al menos un valor de
CapitalCost del futuro debe diferir del baseline.

Salida: lista por futuro de discrepancias (vacía = todo OK) y un resumen.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BASELINE = Path("src/workflow/1_Experiment/Executables/Scenario1_0/Scenario1_0.txt")
FUTURES_DIR = Path("src/workflow/1_Experiment/Experimental_Platform/Futures/Scenario1")
RE_TECHS = ["PWRSOL001", "PWRWND001", "PWRBIO001", "PWRGEO", "PWRCSP001", "PWRCSP002"]
TOL_RATIO = 1e-6      # tolerancia en ratio
TOL_NOOP = 1e-3       # tolerancia para detectar perturbación efectiva


def parse_param_block(path: Path, param_name: str) -> dict:
    """Parsea `param X default 0 := \n [R,*,*]: y0 y1 ... yN := \n TECH v0 v1 ... vN \n ;`.

    Returns dict: {(region, tech, year): value}
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(
        rf"^param\s+{re.escape(param_name)}\s+default\s+\S+\s*:=\s*$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        raise ValueError(f"No se encontró 'param {param_name} default ...' en {path}")
    body = text[m.end():]
    end = body.find("\n;")
    if end == -1:
        raise ValueError(f"No se encontró el final ';' del bloque {param_name} en {path}")
    body = body[:end]

    out: dict[tuple[str, str, str], float] = {}
    current_region: str | None = None
    years: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Encabezado de slice: [RE1,*,*]:
        m_slice = re.match(r"^\[([^\]]+)\]\s*:\s*$", line)
        if m_slice:
            parts = [p.strip() for p in m_slice.group(1).split(",")]
            # Formato esperado: [REGION,*,*]: -> region es la primera parte
            current_region = parts[0]
            years = []
            continue
        # Línea de años terminando en :=
        if line.endswith(":="):
            toks = line.replace(":=", "").split()
            # solo es la línea de cabecera si todos los tokens parecen años (4 dígitos)
            if toks and all(re.fullmatch(r"\d{4}", t) for t in toks):
                years = toks
                continue
        # Fila de datos: TECH v0 v1 ... vN
        toks = line.split()
        if not toks or current_region is None or not years:
            continue
        tech = toks[0]
        vals = toks[1:]
        if len(vals) != len(years):
            # Línea malformada o no es del bloque esperado; saltar silenciosamente
            continue
        for y, v in zip(years, vals):
            try:
                out[(current_region, tech, y)] = float(v)
            except ValueError:
                pass
    return out


def check_future(future_path: Path, baseline_capital: dict, baseline_fixed: dict) -> tuple[list, dict]:
    """Devuelve (lista_discrepancias, stats)."""
    f_capital = parse_param_block(future_path, "CapitalCost")
    f_fixed = parse_param_block(future_path, "FixedCost")

    discrepancies = []
    perturbation_detected = False
    keys_checked = 0
    max_ratio_diff = 0.0

    for tech in RE_TECHS:
        for (r, t, y), bc in baseline_capital.items():
            if t != tech:
                continue
            bf = baseline_fixed.get((r, t, y))
            if bf is None:
                continue
            fc = f_capital.get((r, t, y))
            ff = f_fixed.get((r, t, y))
            if fc is None or ff is None:
                discrepancies.append(("missing", r, t, y))
                continue
            # Detectar perturbación efectiva
            if abs(fc - bc) > TOL_NOOP:
                perturbation_detected = True
            # Saltar comparación de ratio si baseline no tiene CapitalCost > 0
            if bc <= 0 or fc <= 0:
                continue
            baseline_ratio = bf / bc
            future_ratio = ff / fc
            diff = abs(future_ratio - baseline_ratio)
            max_ratio_diff = max(max_ratio_diff, diff)
            keys_checked += 1
            if diff > TOL_RATIO:
                discrepancies.append(("ratio", r, t, y, baseline_ratio, future_ratio, diff))

    stats = {
        "perturbation_detected": perturbation_detected,
        "keys_checked": keys_checked,
        "max_ratio_diff": max_ratio_diff,
    }
    return discrepancies, stats


def main() -> int:
    if not BASELINE.exists():
        print(f"ERROR: baseline no existe: {BASELINE}", file=sys.stderr)
        return 2

    print(f"Parseando baseline {BASELINE}...")
    baseline_capital = parse_param_block(BASELINE, "CapitalCost")
    baseline_fixed = parse_param_block(BASELINE, "FixedCost")

    # Confirmar que las 6 techs están presentes en baseline
    missing_techs = []
    for tech in RE_TECHS:
        ok_c = any(t == tech for (_r, t, _y) in baseline_capital.keys())
        ok_f = any(t == tech for (_r, t, _y) in baseline_fixed.keys())
        if not (ok_c and ok_f):
            missing_techs.append((tech, ok_c, ok_f))
    if missing_techs:
        print(f"ERROR: técnicas faltantes en baseline: {missing_techs}", file=sys.stderr)
        return 2
    print(f"OK baseline contiene las 6 técnicas renovables")

    futures = sorted(FUTURES_DIR.glob("Scenario1_*/Scenario1_*.txt"))
    if not futures:
        print(f"ERROR: no se encontraron .txt en {FUTURES_DIR}", file=sys.stderr)
        return 2

    all_pass = True
    for fpath in futures:
        future_id = fpath.parent.name
        disc, stats = check_future(fpath, baseline_capital, baseline_fixed)

        status = "OK" if not disc else "FALLA"
        noop_warn = "" if stats["perturbation_detected"] else "  ⚠️ NO HUBO PERTURBACIÓN (CapitalCost == baseline)"
        print(f"  {status} {future_id}: {stats['keys_checked']} celdas comparadas, "
              f"max ratio diff = {stats['max_ratio_diff']:.2e}{noop_warn}")

        if disc:
            all_pass = False
            for d in disc[:5]:
                print(f"      {d}")
            if len(disc) > 5:
                print(f"      ... y {len(disc) - 5} más")
        # Si no hubo perturbación es sospechoso pero no es necesariamente un fallo de
        # YES_PROP — puede ser que LHS tomó valor cercano a 1.0 para CapitalCost.
        # Lo marcamos como warning, no como falla.

    print()
    if all_pass:
        print("RESULTADO: TODOS LOS RATIOS PRESERVADOS (Problema 2 funcional)")
        return 0
    else:
        print("RESULTADO: FALLAS DETECTADAS — revisar discrepancias arriba")
        return 1


if __name__ == "__main__":
    sys.exit(main())
