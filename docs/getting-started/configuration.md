# Configuration

This guide covers all configuration options for OSeMOSYS-RDM.

## Main Configuration File

The primary configuration is managed through:

```
src/Interface_RDM.xlsx
```

This Excel workbook contains multiple sheets that control different aspects of the workflow.

## Setup Sheet

The `Setup` sheet controls the main execution parameters:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `Solver` | String | Optimization solver to use | `cplex`, `cbc`, `glpk`, `gurobi` |
| `Run_Base_Future` | Yes/No | Execute baseline scenario | `Yes` |
| `Run_RDM` | Yes/No | Execute RDM uncertainty analysis | `Yes` |
| `Region` | String | Model region identifier | `UGA`, `KEN`, etc. |
| `OSeMOSYS_Model_Name` | String | Model formulation file | `model.v.5.3.txt` |
| `Timeslices_model` | Integer | Number of time slices | `48` |
| `Number_of_Runs` | Integer | Number of futures to generate | `100` |
| `Parallel_Use` | Integer | Batch size for parallel execution | `10` |
| `Initial_Year_of_Uncertainty` | Integer | Year uncertainties begin | `2025` |
| `Scenario_to_Reproduce` | String | Which scenarios to run | `Experiment` |
| `Experiment_ID` | String | Identifier for this experiment | `1` |

### Solver Selection

Choose a solver based on your needs:

| Solver | Speed | Cost | Notes |
|--------|-------|------|-------|
| GLPK | Slowest | Free | Required for preprocessing |
| CBC | Fast | Free | Good for most applications |
| CPLEX | Fastest | Commercial | Best for large ensembles |
| Gurobi | Fastest | Commercial | Excellent performance |

```{tip}
For large RDM experiments (>50 futures), commercial solvers provide 
significant time savings.
```

## To_Print Sheet

Controls which model outputs are exported:

| Column | Description |
|--------|-------------|
| `Parameter` | Name of the OSeMOSYS output variable |
| `Print` | `Yes` to include in output files |

Common parameters to export:

- `ProductionByTechnology`
- `TotalCapacityAnnual`
- `AnnualEmissions`
- `TotalDiscountedCost`
- `NewCapacity`

## Uncertainty_Table Sheet

Defines the parameters for RDM uncertainty analysis.

### Column Definitions

| Column | Description |
|--------|-------------|
| `X_Num` | Unique identifier for this uncertainty |
| `X_Category` | Category grouping for the uncertainty |
| `X_Plain_English_Description` | Human-readable description |
| `X_Mathematical_Type` | Type of variation (see below) |
| `Explored_Parameter_of_X` | What aspect is being varied |
| `Min_Value` | Minimum value or multiplier |
| `Max_Value` | Maximum value or multiplier |
| `Involved_Scenarios` | Which scenarios this applies to |
| `Involved_First_Sets_in_Osemosys` | Technology/Fuel sets involved |
| `Involved_Second_Sets_in_Osemosys` | Secondary sets (if applicable) |
| `Involved_Third_Sets_in_Osemosys` | Tertiary sets (if applicable) |
| `Exact_Parameters_Involved_in_Osemosys` | OSeMOSYS parameter names |
| `Initial_Year_of_Uncertainty` | Year uncertainty begins |

### Mathematical Types

| Type | Description | Use Case |
|------|-------------|----------|
| `Time_Series` | Non-linear interpolation to final value | Cost projections |
| `Constant` | Maintain constant trajectory from uncertainty year | Fixed parameters |
| `Linear` | Linear interpolation to final value | Simple projections |
| `Logistic` | S-curve trajectory | Technology adoption |
| `Timeslices_Curve` | Modify time slice profiles | Demand shapes |

### Example Uncertainty Definition

```
X_Num: 1
X_Category: Fuel Costs
X_Plain_English_Description: Natural gas price uncertainty
X_Mathematical_Type: Time_Series
Explored_Parameter_of_X: Final_Value
Min_Value: 0.8
Max_Value: 1.2
Involved_Scenarios: Scenario1
Involved_First_Sets_in_Osemosys: NATGAS
Exact_Parameters_Involved_in_Osemosys: VariableCost
Initial_Year_of_Uncertainty: 2025
```

## Params_Sets_Vari Sheet

Maps parameters to their associated sets for correct data manipulation.

| Column | Description |
|--------|-------------|
| `parameter` | OSeMOSYS parameter name |
| `Number` | Number of sets this parameter depends on |
| `Set1`, `Set2`, `Set3` | The set names in order |

## DVC Configuration

### dvc.yaml

The DVC pipeline is defined in `dvc.yaml`:

```yaml
stages:
  base_future:
    cmd: python scripts/run_base_future.py
    deps:
      - src/workflow/0_Scenarios/
      - src/Interface_RDM.xlsx
    outs:
      - src/workflow/1_Experiment/Executables/
```

### Remote Storage

Configure DVC remote storage for sharing results:

```bash
# Local directory
dvc remote add -d myremote /path/to/storage

# Google Drive
dvc remote add -d gdrive gdrive://folder_id

# Amazon S3
dvc remote add -d s3remote s3://mybucket/path

# Azure Blob Storage
dvc remote add -d azure azure://container/path
```

## PRIM Configuration

PRIM analysis is configured through files in `src/workflow/4_PRIM/`:

### PRIM_t3f2.yaml

Main PRIM configuration:

```yaml
# Base scenario name
BAU: 'Scenario1'

# Model names (must match Region from Interface_RDM.xlsx)
ose_inputs: 'OSeMOSYS-{Region} inputs'
ose_oupts: 'OSeMOSYS-{Region} outputs'

# Directory structure
dir_exps: '1_Experiment'
dir_sdisc: 't3b_sdiscovery'

# Parallel processing
max_per_batch: 10
```

### prim_structure.xlsx

Defines the analysis structure (driver→outcome mapping):

- **Outcomes**: Metrics to analyze (costs, emissions, etc.)
- **Drivers**: Uncertain parameters that influence outcomes

### prim_files_creator_cntrl.xlsx

Execution controls and analysis periods:

| Sheet | Purpose |
|-------|---------|
| `match_exp_ana` | Link experiments to analyses |
| `periods` | Define temporal periods for analysis |
| `dtype` | Data typing controls |

## Environment Configuration

### environment.yaml

The Conda environment specification:

```yaml
name: AFR-RDM-env
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - pandas
  - numpy
  - scipy
  - openpyxl
  - xlsxwriter
  - pyarrow
  - pyyaml
  - scikit-learn
  - pip
  - pip:
      - dvc>=3.0.0
      - pyDOE>=0.3.8
```

### Customizing the Environment

To add additional packages:

```bash
# Activate the environment
conda activate AFR-RDM-env

# Install additional packages
conda install -c conda-forge package-name

# Or with pip
pip install package-name
```

## File Structure Configuration

The workflow expects this directory structure:

```
osemosys-rdm/
├── src/
│   ├── Interface_RDM.xlsx          # Main configuration
│   ├── workflow/
│   │   ├── 0_Scenarios/            # Input scenario files
│   │   ├── 1_Experiment/           # Experiment workspace
│   │   ├── 2_Miscellaneous/        # Reference files
│   │   ├── 3_Postprocessing/       # Output processing
│   │   └── 4_PRIM/                 # PRIM configuration
│   └── Results/                    # Final outputs
├── model.v.5.3.txt                 # OSeMOSYS formulation
└── run.py                          # Main runner script
```
