# Workflow Overview

This page provides a comprehensive overview of the OSeMOSYS-RDM workflow and its components.

## What is OSeMOSYS-RDM?

OSeMOSYS-RDM is a reproducible workflow tool designed for:

1. **Preprocessing** OSeMOSYS model data
2. **Solving** energy system optimization problems
3. **Postprocessing** results for analysis
4. **Uncertainty Analysis** using Robust Decision Making (RDM) methodology
5. **Scenario Discovery** using PRIM (Patient Rule Induction Method)

## Architecture Overview

```{mermaid}
flowchart TB
    subgraph Input["📁 Inputs"]
        A[Scenario Files<br/>.txt] 
        B[Interface_RDM.xlsx]
        C[Model Formulation<br/>model.v.5.3.txt]
    end
    
    subgraph Pipeline["🔧 DVC Pipeline"]
        D[base_future]
        E[rdm_experiment]
        F[postprocess]
        G[prim_files_creator]
        H[prim_analysis]
    end
    
    subgraph Output["📊 Outputs"]
        I[CSV/Parquet Results]
        J[PRIM Discoveries]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> I
    I --> G
    G --> H
    H --> J
```

## Pipeline Stages

### Stage 1: Base Future (Future 0)

The base future represents your baseline scenario without uncertainties.

**Purpose:**
- Establish the reference case for comparison
- Validate model structure and data
- Generate baseline projections

**Process:**
1. Extract model structure from scenario file
2. Preprocess data into solver-ready format
3. Execute optimization with selected solver
4. Process outputs into standardized CSV format

**Key Files:**
- Input: `src/workflow/0_Scenarios/*.txt`
- Output: `src/workflow/1_Experiment/Executables/`

### Stage 2: RDM Experiment

The RDM experiment generates multiple futures by systematically varying uncertain parameters.

**Purpose:**
- Explore uncertainty space using Latin Hypercube Sampling
- Generate ensemble of possible futures
- Understand sensitivity to key parameters

**Process:**
1. Read uncertainty definitions from `Interface_RDM.xlsx`
2. Generate parameter samples using LHS
3. Create modified scenario files for each future
4. Execute all futures (parallelized)
5. Store results in Parquet format

**Key Concepts:**

| Concept | Description |
|---------|-------------|
| **Future** | One realization of uncertain parameters |
| **LHS** | Latin Hypercube Sampling for efficient coverage |
| **Multiplier** | Relative change from baseline value |
| **Time Series** | Trajectory of values over time |

### Stage 3: Postprocessing

Consolidates results from all futures into analysis-ready datasets.

**Purpose:**
- Aggregate outputs from parallel runs
- Create unified input/output datasets
- Generate efficient Parquet files

**Process:**
1. Collect outputs from all futures
2. Standardize column formats
3. Concatenate into master datasets
4. Export as CSV and Parquet

**Output Files:**
```
src/Results/
├── OSEMOSYS_{Region}_Energy_Output.csv
├── OSEMOSYS_{Region}_Energy_Input.csv
└── (additional analysis files)
```

### Stage 4: PRIM Files Creator

Prepares data for PRIM scenario discovery analysis.

**Purpose:**
- Transform RDM results into PRIM-compatible format
- Calculate metrics for each future
- Aggregate by analysis periods

**Process:**
1. Read postprocessed results
2. Calculate outcome metrics (costs, emissions, etc.)
3. Match drivers to outcomes
4. Create PRIM input tables

### Stage 5: PRIM Analysis

Executes the Patient Rule Induction Method for scenario discovery.

**Purpose:**
- Identify parameter combinations leading to outcomes of interest
- Find "boxes" in uncertainty space
- Characterize successful/risky scenarios

**Process:**
1. Define outcome thresholds (high/low cases)
2. Execute PRIM peeling algorithm
3. Identify predominant parameter ranges
4. Export discoveries to Excel

## Execution Modes

### Full Automated Execution

```bash
# Run everything
python run.py all
```

### Selective Execution

```bash
# RDM only (stages 1-3)
python run.py rdm

# PRIM only (stages 4-5, requires RDM results)
python run.py prim
```

### Manual Stage Execution

```bash
# Individual DVC stages
conda run -n AFR-RDM-env dvc repro base_future
conda run -n AFR-RDM-env dvc repro rdm_experiment
conda run -n AFR-RDM-env dvc repro postprocess
```

## Data Flow

### Input Data

```
src/workflow/0_Scenarios/Scenario1.txt
```

Contains:
- Set definitions (YEAR, TECHNOLOGY, FUEL, etc.)
- Parameter values (costs, capacities, demands, etc.)
- Constraints and bounds

### Intermediate Data

```
src/workflow/1_Experiment/
├── Executables/           # Base future results
│   └── Scenario1_0/
└── Experimental_Platform/
    └── Futures/           # RDM futures
        └── Scenario1/
            ├── Scenario1_1/
            ├── Scenario1_2/
            └── ...
```

### Output Data

```
src/Results/
├── OSEMOSYS_{Region}_Energy_Output.csv
├── OSEMOSYS_{Region}_Energy_Input.csv
└── *.parquet files
```

## OSeMOSYS Compatibility

OSeMOSYS-RDM is designed for the GNU MathProg implementation of OSeMOSYS.

### Tested Formulation

The workflow has been tested with **MUIO v5.3**:
- Reference formulation: `model.v.5.3.txt`
- Standard OSeMOSYS sets and parameters
- Support for storage and user-defined constraints

### Compatible Model Features

| Feature | Support |
|---------|---------|
| Multi-region | ✅ Yes |
| Storage | ✅ Yes |
| User-defined constraints | ✅ Yes |
| Time slicing | ✅ Yes |
| Trade flows | ✅ Yes |
| Emissions | ✅ Yes |
