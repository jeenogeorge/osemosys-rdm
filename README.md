# OSeMOSYS-RDM (osemosys-rdm)

A reproducible workflow tool for **preprocessing, solving, and postprocessing** models built with the **OSeMOSYS** (Open Source Energy Modelling System) architecture, with built-in support for **Robust Decision Making (RDM)** style exploratory ensembles and **scenario discovery** (PRIM).

**Developed by:** **Luis Victor Gallardo** and **Andrey Salazar Vargas**.

---

## What this is (and is not)

This repository provides an **OSeMOSYS-specific workflow** for running:

- a **single baseline** model run (“Future 0”), and/or
- a **large ensemble of futures** (e.g., Latin Hypercube Sampling) for RDM-type uncertainty analysis,

…then producing standardized outputs suitable for downstream analysis and **PRIM** scenario discovery.

**Not affiliated:** This is an independent tool and is **not affiliated with or endorsed by** the upstream OSeMOSYS project.

- Upstream OSeMOSYS: https://github.com/OSeMOSYS/OSeMOSYS

---

## Scope: energy and beyond

OSeMOSYS is often used for energy-system planning, but the workflow here is **not limited to “energy-only” models**.

It can also support OSeMOSYS-based models that represent additional domains (e.g., land-use, industrial processes, waste, CLEWs-style integrated systems), **as long as the model is expressed using the OSeMOSYS set/parameter/variable architecture** (and the formulation used is compatible — see below).

---

## Key features

- **Two operation modes**
  - **Base Future mode:** execute a single baseline scenario (“Future 0”)
  - **RDM Experiment mode:** generate and evaluate multiple futures using uncertainty ranges (Latin Hypercube Sampling)

- **Multi-solver support**
  - Compatible with: **GLPK**, **CBC**, **CPLEX**, **Gurobi** (install at least one separately)

- **End-to-end automation**
  - preprocessing → solve → postprocessing → consolidated datasets in `src/Results/`

- **Reproducible pipelines**
  - runs as a **DVC pipeline** with dependency tracking and caching

- **Scenario discovery**
  - integrated **PRIM** workflow for identifying parameter ranges associated with success/risk outcomes

---

## Compatibility: OSeMOSYS formulation/version

This workflow is designed for the **GNU MathProg** implementation of OSeMOSYS (LP formulation), and has been tested with the formulation used in **MUIO v5.3**.

- MUIO v5.3 release notes (GitHub): https://github.com/OSeMOSYS/MUIO/releases/tag/v5.3
- A reference formulation consistent with this workflow is included as `model.v.5.3.txt`.

### What “compatible” means in practice

Your model/data should be consistent with the OSeMOSYS architecture and naming conventions used in GNU MathProg OSeMOSYS formulations (examples):

- sets like `REGION`, `TECHNOLOGY`, `COMMODITY`, `EMISSION`, `YEAR`, `TIMESLICE` (and optional `STORAGE`, `UDC`, etc.)
- the standard OSeMOSYS “commodity-flow” structure for technologies and demands

If you are using a different OSeMOSYS formulation (or substantially different naming conventions), you may need to adjust parsing/post-processing configuration accordingly.

---

## Requirements

### System

- **Python 3.10+**
- **Conda/Miniconda** (environment management)
- At least one solver installed and available on PATH:
  - [GLPK](https://www.gnu.org/software/glpk/) (free)
  - [CBC](https://github.com/coin-or/Cbc) (free)
  - [CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio) (commercial)
  - [Gurobi](https://www.gurobi.com/) (commercial)

### Optional

- **Git** (recommended, but not required). The pipeline can run without Git installed.
- **DVC remote storage** if you want to share large artifacts across machines.

---

## Installation

### Option 1 — Automated setup (recommended)

Running the pipeline will create/validate the conda environment and execute the DVC stages:

```bash
python run.py rdm
```

### Option 2 — Manual setup

```bash
git clone https://github.com/clg-admin/osemosys-rdm.git
cd osemosys-rdm

conda env create -f environment.yaml
conda activate <ENV_NAME_FROM_environment.yaml>
```

> Make sure your chosen solver (GLPK/CBC/CPLEX/Gurobi) is installed and available from the command line.

---

## Quickstart (typical workflow)

### 1) Prepare input scenarios

Place your OSeMOSYS scenario/data files (GNU MathProg format) in:

```text
src/workflow/0_Scenarios/
```

### 2) Configure the run

Open the main configuration interface:

```text
src/Interface_RDM.xlsx
```

Typical configuration happens in:

- `Setup` sheet (timeslices model, solver, model name, region, toggles)
- `To_Print` sheet (outputs to export)

### 3) Run the pipeline

```bash
# Execute RDM pipeline (base future + experiment + postprocessing)
python run.py rdm

# Execute PRIM analysis only (requires RDM outputs)
python run.py prim

# Execute both sequentially
python run.py all
```

#### Command options

```bash
python run.py <module> [options]

Modules:
  rdm           Execute RDM pipeline only
  prim          Execute PRIM analysis only (requires RDM results)
  all           Execute both RDM and PRIM sequentially

Options:
  --force       Force re-execution of all stages (ignore cache)
  --skip-pull   Skip 'dvc pull' even if remote is configured
  --env-name    Specify Conda environment name
  --env-file    Path to environment.yaml file
```

---

## Workflow overview

At a high level, OSeMOSYS-RDM does:

1. **Structure extraction** from scenario inputs (sets/parameters present, model structure)
2. **Data preprocessing** into solver-ready inputs
3. **Model execution** with the selected solver
4. **Output processing** into standardized datasets
5. *(Optional)* **RDM experiment generation** (sampling + batch execution)
6. *(Optional)* **Scenario discovery** with PRIM

---

## Outputs

Results are aggregated to:

```text
src/Results/
```

Typical output artifacts include:

- `Scenario_0_Input.csv`, `Scenario_0_Output.csv` (baseline)
- `Scenario_N_Input.csv` (inputs per future)
- `Scenario_N_Output.parquet` (outputs per future, efficient storage)
- `input_dataset_f.parquet`, `output_dataset_f.parquet` (aggregated datasets)

Some exported filenames may contain “Energy” for historical reasons (e.g., `OSEMOSYS_{Region}_Energy_Output.csv`). This is a naming convention and does **not** restrict the model domain.

---

## Advanced configuration

### Customizing RDM parameters (Interface_RDM.xlsx)

You define your experimental design primarily through `src/Interface_RDM.xlsx`, including:

- which parameters are uncertain (and their ranges / tolerance settings)
- number of futures to generate (and any sampling controls)
- sampling strategy settings (e.g., Latin Hypercube Sampling)
- which input/output parameters are exported and consolidated for analysis

> For detailed step-by-step instructions, see the HTML guide(s) in `src/Guides/`.

---

## PRIM scenario discovery (module)

The PRIM (**Patient Rule Induction Method**) module enables **scenario discovery** by identifying which combinations of uncertain input parameters are associated with outcomes of interest.

### Purpose

PRIM searches for “boxes” (regions in the uncertainty space) where:

- **desirable outcomes** occur (e.g., low costs, low emissions), and/or
- **undesirable outcomes / risks** occur (e.g., high costs, high emissions)

### What PRIM helps you do

- **Driver analysis:** identify which uncertain inputs most influence outcomes
- **Threshold-based outcome definitions:** create “risk” and “success” cases using configurable rules

  Common presets (depending on your configuration) include:

  - **High**: values greater than a chosen upper quantile (often the 75th percentile)
  - **Low**: values lower than a chosen lower quantile (often the 25th percentile)
  - **Mid**: values above a chosen midpoint (often the 50th percentile)
  - **Zero**: values lower than zero (useful for “worse than baseline” style metrics)

- **Multi-metric support:** costs, emissions, and other outputs/derived metrics
- **Temporal analysis:** evaluate outcomes across user-defined time periods

### Usage guide

Detailed configuration instructions are available in:

```text
src/Guides/Guide PRIM Module Configuration.html
```

<details>
<summary>PRIM configuration files and execution order</summary>

The PRIM module files live in:

```text
src/workflow/4_PRIM/
```

#### Configuration files

1. **prim_structure.xlsx**
   - defines the analysis structure (driver→outcome mapping)

2. **Population.xlsx**
   - population normalization inputs (when used)

3. **prim_files_creator_cntrl.xlsx**
   - execution controls and analysis periods
   - common sheets include:
     - `match_exp_ana` (link experiments to analyses)
     - `periods` (define temporal periods)
     - `dtype` (data typing controls)

4. **Units.xlsx**
   - units for drivers/outcomes (e.g., MUSD, PJ, GgCO2e)

5. **PRIM_t3f2.yaml**
   - main configuration file (example excerpt):

   ```yaml
   # Base scenario name
   BAU: 'Scenario1'

   # Model names (must match Region from Interface_RDM.xlsx)
   ose_inputs: 'OSeMOSYS-{Region} inputs'
   ose_oupts: 'OSeMOSYS-{Region} outputs'
   ```

#### Execution scripts (conceptual order)

| Order | Script | Typical location | Role |
|---:|---|---|---|
| 1 | `t3f1_prim_structure.py` | `t3b_sdiscovery/` | Builds PRIM structure from `prim_structure.xlsx` |
| 2 | `t3f2_prim_files_creator.py` | `4_PRIM/` | Creates PRIM-ready input files from experiment results |
| 3 | `t3f3_prim_manager.py` | `t3b_sdiscovery/` | Runs PRIM and produces “boxes” |
| 4 | `t3f4_range_finder_mapping.py` | `t3b_sdiscovery/` | Summarizes predominant parameter ranges |

When using the automated pipeline (`python run.py prim`), these steps are executed automatically in the correct order.

#### Output files

Results are typically stored under:

```text
src/workflow/4_PRIM/t3b_sdiscovery/
```

including spreadsheets of predominant parameter ranges, for example:

- `t3f4_predominant_ranges_*.xlsx`

</details>

---

## Project structure

The workflow is organized as a DVC pipeline with wrapper scripts calling the underlying modules.

```text
osemosys-rdm/
├── run.py                          # Main automation script (DVC pipeline runner)
├── dvc.yaml                        # DVC pipeline definition
├── environment.yaml                # Conda environment specification
├── scripts/                        # DVC wrapper scripts (pipeline stages)
│   ├── run_base_future.py          # Base future execution wrapper
│   ├── run_rdm_experiment.py       # RDM experiment wrapper
│   ├── run_postprocess.py          # Postprocessing wrapper
│   ├── run_prim_files_creator.py   # PRIM files creator wrapper
│   └── run_prim_analysis.py        # PRIM analysis wrapper
├── src/
│   ├── Results/                    # Aggregated outputs (CSV/Parquet)
│   ├── workflow/
│   │   ├── 0_Scenarios/            # Input scenario files (.txt)
│   │   ├── 1_Experiment/           # Experiment execution workspace
│   │   │   ├── 0_From_Confection/  # Generated model structure / extracted elements
│   │   │   ├── Executables/        # Base future (Future 0) runs
│   │   │   └── Experimental_Platform/
│   │   │       └── Futures/        # RDM experiment futures
│   │   ├── 2_Miscellaneous/        # Reference files
│   │   ├── 3_Postprocessing/       # Output processing tools
│   │   │   ├── create_csv_concatenate.py
│   │   │   ├── config_concatenate.yaml
│   │   │   └── otoole_config/      # Conversion templates (optional)
│   │   └── 4_PRIM/                 # PRIM scenario discovery module
│   ├── Guides/                     # HTML documentation
│   ├── z_auxiliar_code.py          # Core library functions
│   ├── Interface_RDM.xlsx          # Main configuration interface
│   └── RUN_RDM.py                  # Legacy execution entry point
├── model.v.5.3.txt                 # Reference OSeMOSYS GNU MathProg model (tested formulation)
├── LICENSE
└── README.md
```

> Note: Some file/folder names may still reflect legacy naming conventions; functionality is unchanged.

---

## Core components (what to read first)

If you want to understand/extend the code, these are the key entry points:

- `run.py`
  - orchestrates the DVC pipeline modules (`rdm`, `prim`, `all`)

- `dvc.yaml` + `scripts/`
  - define pipeline stages and wrap their execution

- `src/RUN_RDM.py`
  - legacy “main workflow” runner (called by wrappers / automation)

- `src/z_auxiliar_code.py`
  - shared utilities (parsing OSeMOSYS files, dataset creation, solver execution helpers, transformations)

- `src/Interface_RDM.xlsx`
  - main configuration interface (run toggles, solver, model name, outputs)

---

## OSeMOSYS model structure (as assumed by this workflow)

This project works with models expressed using the OSeMOSYS architecture.

The included reference formulation (`model.v.5.3.txt`) defines (among others):

- **Core sets**
  - `REGION`, `TECHNOLOGY`, `COMMODITY`, `EMISSION`, `YEAR`
- **Time-slicing sets**
  - `TIMESLICE`, plus mappings via `SEASON`, `DAYTYPE`, `DAILYTIMEBRACKET`
- **Optional advanced features**
  - `STORAGE` (including intra-day and intra-year storage subsets)
  - `UDC` (user-defined constraints)
  - cross-sets such as `MODEperTECHNOLOGY{TECHNOLOGY}` and fuel/technology mappings

This means the workflow can support formulations with features such as:

- multi-commodity energy/material flows
- multiple regions with trade (if represented in the data)
- storage and storage constraints (as implemented in the formulation)
- user-defined constraint blocks (UDCs)

---

## DVC pipeline structure (reproducibility)

At a high level:

- **RDM pipeline** (`python run.py rdm`)
  - `base_future` → `rdm_experiment` → `postprocess`

- **PRIM pipeline** (`python run.py prim`)
  - `prim_files_creator` → `prim_analysis`

DVC provides:

- automatic dependency tracking
- caching (skip unchanged stages)
- reproducible reruns across machines

To force a full rerun:

```bash
python run.py rdm --force
```

<details>
<summary>Pipeline architecture diagram</summary>

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RDM PIPELINE                                    │
│                           python run.py rdm                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐         │
│  │ base_future  │ ──► │  rdm_experiment  │ ──► │   postprocess   │         │
│  └──────────────┘     └──────────────────┘     └─────────────────┘         │
│        │                      │                        │                    │
│        ▼                      ▼                        ▼                    │
│   Executables/          Futures/                  src/Results/              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRIM PIPELINE                                    │
│                          python run.py prim                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────┐              ┌─────────────────┐                   │
│  │ prim_files_creator │ ──────────►  │  prim_analysis  │                   │
│  └────────────────────┘              └─────────────────┘                   │
│           │                                   │                             │
│           ▼                                   ▼                             │
│   1. t3f1_prim_structure.py          3. t3f3_prim_manager.py               │
│   2. t3f2_prim_files_creator.py      4. t3f4_range_finder_mapping.py       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

</details>

<details>
<summary>Running without Git installed</summary>

The automation can run on machines **without Git installed** (e.g., if the repository is downloaded as a ZIP).  
When Git is not available, DVC can initialize in standalone mode (`--no-scm`).

You still get:

- pipeline execution
- caching
- reproducible outputs

You do **not** get:

- Git version history for code/configs

</details>

---

## Solver notes (practical)

- **GLPK**: free and widely available; can be slower for large ensembles
- **CBC**: free; often faster than GLPK for larger problems
- **CPLEX / Gurobi**: commercial; typically best performance for large-scale models/ensembles

If a solver is “not found”, ensure the solver executable is on PATH and callable from your terminal.

---

## Troubleshooting

Common issues and fixes:

- **Solver not found**
  - Confirm the solver is installed and on PATH (`glpsol --version`, `cbc -version`, etc.)

- **Memory / runtime issues**
  - Large models or large ensembles may require more RAM/CPU; consider a commercial solver and/or fewer futures

- **File format errors**
  - Ensure scenario files are valid GNU MathProg data files consistent with the chosen OSeMOSYS formulation

- **Import errors**
  - Recreate the conda environment from `environment.yaml`

### Logs (when available)

Depending on solver and execution settings, log files may be created during runs (examples):
- `cplex.log` (when using CPLEX)
- `clone1.log`, `clone2.log` (parallel execution logs, if enabled)

---

## Related tools (often used alongside)

OSeMOSYS-RDM is designed to work with OSeMOSYS GNU MathProg models and can be used alongside other tools in the OSeMOSYS ecosystem, for example:

- **MUIO** (Model User Interface and Optimizer): https://github.com/OSeMOSYS/MUIO
- **otoole** (data conversion and tooling for OSeMOSYS): https://otoole.readthedocs.io/
- **clicSAND** (user-friendly interface for OSeMOSYS/SAND): https://www.mdpi.com/1996-1073/17/16/3923

---

## Documentation

HTML guides are available in:

```text
src/Guides/
```

Including:

- `Guide OSeMOSYS_RDM.html`
- `Guide PRIM Module Configuration.html`

---

## Citation

If you use this workflow in academic work, please cite:

- **OSeMOSYS-RDM MethodsX paper:** *(TODO: add DOI/link when available)*
- **OSeMOSYS**: Howells et al. (2011), *Energy Policy*, 39(10), 5850–5870. https://doi.org/10.1016/j.enpol.2011.06.033

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

---

## References (useful starting points)

- OSeMOSYS: https://www.osemosys.org/  *(and the upstream GitHub repo linked above)*
- DVC: https://dvc.org/
- pyDOE (Design of Experiments for Python): https://pythonhosted.org/pyDOE/

---

## Acknowledgements

This tool builds on the OSeMOSYS ecosystem and the wider community of open modelling and decision-support methods, including the OSeMOSYS maintainers and contributors.
