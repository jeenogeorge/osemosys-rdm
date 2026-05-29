#!/usr/bin/env python3
"""Generate a renewable-share base scenario from the committed BAU (Scenario1).

The committed BAU (``src/workflow/0_Scenarios/Scenario1.txt``) intentionally
does NOT activate the PWRREN renewable-share UDC: ``UDCTag[RE1,PWRREN]=0`` and
``UDCMultiplierActivity`` has no PWRREN slices, so the RDM perturbation has no
target to act on (it silently does nothing).

This script produces a SEPARATE base file -- it does **not** modify the
committed BAU -- with the PWRREN UDC activated so the perturbation has a target:

  1. ``UDCTag[RE1,PWRREN] = 1``  (equality share UDC, per RDM_Verification_Guide.md).
  2. ``UDCMultiplierActivity`` PWRREN slices for the RE / non-RE technologies:
     coefficient ``0`` before ``FROM_YEAR`` (so the constraint is ``0 = 0``,
     inert, in historical years -> avoids historical-year infeasibility) and
     ``RE_COEF`` / ``NONRE_COEF`` from ``FROM_YEAR`` onward.

The RE group is uniform (all RE techs share one coefficient) and the per-row
fixer (``fix_re_nonre_share_per_row``) enforces ``|coef_RE| + coef_NonRE =
Sum_To_Value`` on the perturbed futures, matching this baseline.

USAGE
-----
    python make_re_share_base.py

It reads ``SOURCE`` and writes ``OUTPUT`` (a staging folder OUTSIDE
``0_Scenarios`` so RUN_RDM does not auto-pick it up as an extra scenario).
To run the renewable-share experiment, copy the generated file over
``src/workflow/0_Scenarios/Scenario1.txt`` -- a reproducible version of the
manual "run Scenario2 as Scenario1" workaround. Keep the original BAU under
version control to restore it afterwards.

NOTE ON DIRECTION
-----------------
``UDCTag=1`` is an *equality* (``Sum = UDCConstant = 0``), as the guide
prescribes. If the equality proves infeasible, the less-restrictive
alternative is ``UDCTag=0`` (inequality ``Sum <= 0``), which expresses a
renewable *floor* rather than an exact share. Set ``UDC_TAG`` below to switch.
"""
from __future__ import annotations

import os
import sys

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(REPO_ROOT, "src", "workflow", "0_Scenarios", "Scenario1.txt")
OUTPUT = os.path.join(REPO_ROOT, "src", "workflow", "RE_Share_Base", "Scenario1.txt")

REGION = "RE1"
UDC = "PWRREN"
UDC_TAG = "1"            # 1 = equality (guide default); 0 = inequality (RE floor)
FROM_YEAR = 2030         # matches Initial_Year_of_Uncertainty; 0 before this year
RE_COEF = -0.3           # uniform RE coefficient (negative by sign convention)
NONRE_COEF = 0.7         # uniform non-RE coefficient

RE_TECHS = [
    "PWRSOL001", "PWRBIO001", "PWRWND001", "PWRWND001S",
    "PWRCSP002", "PWRCSP001", "PWRSOL001S", "PWRGEO",
]
NONRE_TECHS = [
    "PWRCBM001", "PWRCOA003", "PWRCOA_CCS", "PWRBIO_CCS",
    "PWRNGS001", "PWRCOA001", "PWRNGS002", "PWROHC002",
    "PWROHC003", "PWRNUC", "PWRDSL", "PWRLFG001", "PWRCOA002",
]


def fmt(v: float) -> str:
    """Format a coefficient the way the .txt data file does (no trailing .0)."""
    if v == int(v):
        return str(int(v))
    return repr(v)


def collect_technology_set(lines):
    """Return the members of `set TECHNOLOGY` (handles multi-line ':=' blocks)."""
    members = set()
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        if s.startswith("set TECHNOLOGY"):
            # members may follow ':=' on the same line and/or subsequent lines
            buf = s.split(":=", 1)[1] if ":=" in s else ""
            j = i
            while ";" not in lines[j]:
                j += 1
                if j >= n:
                    break
                buf += " " + lines[j]
            buf = buf.replace(":=", " ").replace(";", " ")
            members.update(tok for tok in buf.split() if tok)
            break
        i += 1
    return members


def flip_udctag(lines):
    """Set UDCTag[REGION, UDC] = UDC_TAG in the tabular UDCTag block."""
    for i, line in enumerate(lines):
        if line.strip().startswith("param UDCTag"):
            header = lines[i + 1].replace(":=", " ").split()
            if UDC not in header:
                sys.exit(f"ERROR: {UDC} not found in UDCTag header")
            col = header.index(UDC)
            j = i + 2
            while j < len(lines) and lines[j].strip() != ";":
                toks = lines[j].split()
                if toks and toks[0] == REGION:
                    toks[1 + col] = UDC_TAG
                    lines[j] = " ".join(toks) + " \n"
                    return
                j += 1
            sys.exit(f"ERROR: region {REGION} row not found in UDCTag block")
    sys.exit("ERROR: 'param UDCTag' block not found")


def find_year_header(lines, block_start):
    """Return the verbatim year-header line (e.g. '2020 ... 2055 :=') of the block."""
    for k in range(block_start, len(lines)):
        if lines[k].strip() == ";":
            break
        toks = lines[k].replace(":=", "").split()
        if toks and all(t.isdigit() for t in toks):
            return lines[k].rstrip("\n"), [int(t) for t in toks]
    sys.exit("ERROR: could not locate a year header inside UDCMultiplierActivity")


def build_slices(year_header_line, years):
    """Build the PWRREN UDCMultiplierActivity slices for all techs."""
    def values(coef):
        return " ".join(fmt(coef if y >= FROM_YEAR else 0) for y in years)

    out = []
    for tech in RE_TECHS:
        out.append(f"[{REGION},{tech},*,*]:")
        out.append(year_header_line)
        out.append(f"{UDC} {values(RE_COEF)} ")
    for tech in NONRE_TECHS:
        out.append(f"[{REGION},{tech},*,*]:")
        out.append(year_header_line)
        out.append(f"{UDC} {values(NONRE_COEF)} ")
    return [l + "\n" for l in out]


def inject_multipliers(lines):
    """Insert PWRREN slices right after the UDCMultiplierActivity header."""
    for i, line in enumerate(lines):
        if line.strip().startswith("param UDCMultiplierActivity"):
            year_header_line, years = find_year_header(lines, i + 1)
            slices = build_slices(year_header_line, years)
            lines[i + 1:i + 1] = slices
            return len(slices)
    sys.exit("ERROR: 'param UDCMultiplierActivity' block not found")


def main():
    if not os.path.exists(SOURCE):
        sys.exit(f"ERROR: source not found: {SOURCE}")

    with open(SOURCE, "r") as fh:
        lines = fh.readlines()

    techs = collect_technology_set(lines)
    missing = [t for t in RE_TECHS + NONRE_TECHS if t not in techs]
    if missing:
        sys.exit(f"ERROR: these techs are not in set TECHNOLOGY: {missing}")

    flip_udctag(lines)
    n_inserted = inject_multipliers(lines)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as fh:
        fh.writelines(lines)

    print(f"OK  UDCTag[{REGION},{UDC}] = {UDC_TAG}")
    print(f"OK  inserted {n_inserted} lines of UDCMultiplierActivity "
          f"({len(RE_TECHS)} RE + {len(NONRE_TECHS)} non-RE slices, "
          f"coef 0 before {FROM_YEAR}, {RE_COEF}/{NONRE_COEF} from {FROM_YEAR})")
    print(f"OK  wrote {OUTPUT}")
    print("\nTo run the experiment, copy this file over "
          "src/workflow/0_Scenarios/Scenario1.txt (keep a backup of the BAU).")


if __name__ == "__main__":
    main()
