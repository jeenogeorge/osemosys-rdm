# Quickstart Guide

This guide will walk you through running your first OSeMOSYS-RDM analysis.

## Overview

OSeMOSYS-RDM provides a streamlined workflow for:

1. **Base Future**: Execute a single baseline scenario ("Future 0")
2. **RDM Experiment**: Generate and evaluate multiple futures using uncertainty ranges
3. **Postprocessing**: Consolidate results into analysis-ready datasets
4. **PRIM Analysis**: Perform scenario discovery to identify key drivers

## Step 1: Prepare Input Scenarios

Place your OSeMOSYS scenario/data files (GNU MathProg format) in the scenarios directory:

```
src/workflow/0_Scenarios/
```

Your scenario file should be a valid GNU MathProg data file compatible with OSeMOSYS.

```{note}
A reference formulation consistent with this workflow is included as `model.v.5.3.txt`.
```

## Step 2: Configure the Run

Open the main configuration interface:

```
src/Interface_RDM.xlsx
```

### Key Configuration Sheets

| Sheet | Purpose |
|-------|---------|
| `Setup` | Solver selection, run toggles, region, model name |
| `To_Print` | Outputs to export from the model |
| `Uncertainty_Table` | Define uncertain parameters and their ranges |

### Essential Setup Parameters

In the `Setup` sheet, configure:

- **Solver**: Choose from `glpk`, `cbc`, `cplex`, or `gurobi`
- **Run_Base_Future**: Set to `Yes` to run the baseline
- **Run_RDM**: Set to `Yes` to run the uncertainty analysis
- **Region**: Your model's region identifier
- **Number_of_Runs**: Number of futures to generate (for RDM)

## Step 3: Run the Pipeline

### Execute Complete Workflow

```bash
# Run the complete RDM pipeline
python run.py rdm

# Run PRIM analysis (requires RDM results)
python run.py prim

# Run both sequentially
python run.py all
```

### Example: First Run

```bash
# Navigate to the project directory
cd osemosys-rdm

# Run with default settings
python run.py rdm
```

You should see output similar to:

```
======================================================================
AFR_RDM Pipeline Runner
======================================================================
Module: RDM
Environment: AFR-RDM-env
======================================================================

🔧 Step 1: Environment Setup
✓ Conda environment 'AFR-RDM-env' already exists.

🔧 Step 2: Dependency Management
✓ All conda packages are present.
✓ All pip packages are present.

🔧 Step 3: Git Repository Check
✓ Git repository detected.

🔧 Step 4: DVC Initialization
✓ DVC repository detected.

======================================================================
🔬 RDM Pipeline (Robust Decision Making)
======================================================================
Stages: base_future → rdm_experiment → postprocess
======================================================================

🔄 Executing RDM Pipeline...
----------------------------------------------------------------------
...
```

## Step 4: Review Results

After execution, results are available in:

```
src/Results/
```

### Output Files

| File Pattern | Description |
|-------------|-------------|
| `OSEMOSYS_{Region}_Energy_Output.csv` | Consolidated model outputs |
| `OSEMOSYS_{Region}_Energy_Input.csv` | Consolidated model inputs |
| `output_dataset_f.parquet` | Efficient storage of all futures |
| `input_dataset_f.parquet` | Efficient storage of all inputs |

## What's Next?

- **Customize uncertainty parameters**: Edit the `Uncertainty_Table` sheet
- **Add more scenarios**: Place additional `.txt` files in `0_Scenarios/`
- **Explore PRIM results**: Check `src/workflow/4_PRIM/t3b_sdiscovery/`
