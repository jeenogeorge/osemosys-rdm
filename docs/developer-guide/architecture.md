# Architecture

This document describes the technical architecture of OSeMOSYS-RDM.

## System Overview

```{mermaid}
flowchart TB
    subgraph UI["User Interface"]
        A[Interface_RDM.xlsx]
        B[run.py]
    end
    
    subgraph Core["Core Engine"]
        C[RUN_RDM.py]
        D[z_auxiliar_code.py]
    end
    
    subgraph Pipeline["DVC Pipeline"]
        E[run_base_future.py]
        F[run_rdm_experiment.py]
        G[run_postprocess.py]
        H[run_prim_files_creator.py]
        I[run_prim_analysis.py]
    end
    
    subgraph Solvers["External Solvers"]
        J[GLPK]
        K[CBC]
        L[CPLEX]
        M[Gurobi]
    end
    
    UI --> Core
    Core --> Pipeline
    Pipeline --> Solvers
```

## Directory Structure

```
osemosys-rdm/
├── run.py                          # Main entry point
├── dvc.yaml                        # Pipeline definition
├── environment.yaml                # Conda environment
├── model.v.5.3.txt                 # OSeMOSYS formulation
│
├── scripts/                        # DVC wrapper scripts
│   ├── run_base_future.py
│   ├── run_rdm_experiment.py
│   ├── run_postprocess.py
│   ├── run_prim_files_creator.py
│   └── run_prim_analysis.py
│
└── src/
    ├── Interface_RDM.xlsx          # Configuration
    ├── RUN_RDM.py                  # Legacy entry point
    ├── Results/                    # Output directory
    │
    └── workflow/
        ├── z_auxiliar_code.py      # Core utilities
        ├── 0_Scenarios/            # Input scenarios
        ├── 1_Experiment/           # Experiment workspace
        │   ├── 0_From_Confection/  # Model structure
        │   ├── 0_experiment_manager.py
        │   ├── 1_output_dataset_creator.py
        │   ├── Executables/        # Base future runs
        │   └── Experimental_Platform/
        │       └── Futures/        # RDM futures
        ├── 2_Miscellaneous/        # Reference files
        ├── 3_Postprocessing/       # Output processing
        └── 4_PRIM/                 # PRIM module
            ├── PRIM_t3f2.yaml
            ├── t3f2_prim_files_creator.py
            └── t3b_sdiscovery/     # Scenario discovery
```

## Core Components

### run.py - Pipeline Orchestrator

The main entry point that:

1. Manages Conda environment
2. Checks/installs dependencies
3. Initializes DVC/Git
4. Executes pipeline stages

```python
# Key functions
def main():
    # Parse arguments
    args = parser.parse_args()
    
    # Setup environment
    create_env_if_missing(env_name, env_file)
    ensure_deps(env_name)
    
    # Execute pipeline
    if args.module == "rdm":
        run_rdm_pipeline(env_name, args.force, args.skip_pull)
    elif args.module == "prim":
        run_prim_pipeline(env_name, args.force, args.skip_pull)
```

### z_auxiliar_code.py - Core Utilities

Contains all shared functions:

| Function | Purpose |
|----------|---------|
| `obtain_structure_file()` | Extract model structure |
| `isolate_params()` | Parse scenario files |
| `generate_df_per_param()` | Create DataFrames |
| `run_osemosys()` | Execute solver |
| `data_processor_new()` | Process solver output |
| `interpolation_*()` | Trajectory functions |

### 0_experiment_manager.py - RDM Engine

Handles uncertainty sampling and future generation:

```python
# Core workflow
def main():
    # Latin Hypercube Sampling
    hypercube = lhs(P-subtracter, samples=N)
    
    # Generate experiment dictionary
    for n in range(N):
        for p in range(P):
            # Calculate sampled values
            evaluation_value = scipy.stats.uniform.ppf(...)
            
    # Apply uncertainties to scenarios
    for s in range(len(scenario_list)):
        for f in range(1, len(all_futures)+1):
            for u in range(1, len(experiment_dictionary)+1):
                # Modify parameters
                
    # Generate and solve futures
    for fut_index in range(len(all_futures)):
        function_C_mathprog_parallel(...)
```

## Data Flow

### Input Processing

```{mermaid}
flowchart LR
    A[Scenario.txt] --> B[isolate_params]
    B --> C[data_per_param dict]
    C --> D[generate_df_per_param]
    D --> E[DataFrame per param]
```

### RDM Generation

```{mermaid}
flowchart TD
    A[Uncertainty_Table] --> B[LHS Sampling]
    B --> C[experiment_dictionary]
    C --> D[inherited_scenarios]
    D --> E[Modified Scenarios]
    E --> F[Solve Each Future]
    F --> G[Parquet Outputs]
```

### Postprocessing

```{mermaid}
flowchart LR
    A[Future Outputs] --> B[local_dataset_creator_f]
    B --> C[output_dataset_f.parquet]
    C --> D[Concatenate]
    D --> E[Final CSV/Parquet]
```

## Parallelization

OSeMOSYS-RDM uses Python multiprocessing:

```python
# Parallel future generation
for batch in range(batches_ceiling):
    processes = []
    for run in range(n_ini, max_iter):
        p = mp.Process(target=function_C_mathprog_parallel, args=(...))
        processes.append(p)
        p.start()
    
    for process in processes:
        process.join()
```

### Batch Control

- `Parallel_Use` in Interface_RDM.xlsx controls batch size
- Each batch runs `Parallel_Use` futures simultaneously
- Memory-bound: ~1-2 GB per parallel future

## File Formats

### Scenario Files (.txt)

GNU MathProg data format:

```
set YEAR := 2020 2025 2030 ;
set TECHNOLOGY := T1 T2 T3 ;

param CapitalCost default 0 :=
[REG,*,*]:
    2020 2025 2030 :=
T1  100  90   80
T2  200  180  160
;
```

### Output Files (.parquet)

Apache Parquet for efficient storage:

```python
# Schema
{
    'Strategy': string,
    'Future.ID': int,
    'YEAR': int,
    'TECHNOLOGY': string,
    'Variable': string,
    'Value': float
}
```

### Metrics Files (.json)

DVC metrics tracking:

```json
{
    "stage": "rdm_experiment",
    "timestamp": "2025-01-08 10:30:00",
    "futures_generated": 100,
    "total_parquet_files": 200
}
```

## PRIM Module Architecture

### File Structure

```
4_PRIM/
├── PRIM_t3f2.yaml              # Main configuration
├── Population.xlsx             # Population data
├── prim_files_creator_cntrl.xlsx
├── t3f2_prim_files_creator.py  # Creates PRIM inputs
│
└── t3b_sdiscovery/
    ├── Analysis_1/
    │   └── prim_structure.xlsx  # Outcome/driver definitions
    ├── Units.xlsx
    ├── t3f1_prim_structure.py   # Structure builder
    ├── t3f3_prim_manager.py     # PRIM execution
    └── t3f4_range_finder_mapping.py  # Result processing
```

### PRIM Execution Flow

```{mermaid}
flowchart TD
    A[RDM Results] --> B[t3f1_prim_structure.py]
    B --> C[prim_structure.pickle]
    C --> D[t3f2_prim_files_creator.py]
    D --> E[pfd_*.pickle]
    E --> F[t3f3_prim_manager.py]
    F --> G[PRIM Boxes]
    G --> H[t3f4_range_finder_mapping.py]
    H --> I[Excel Reports]
```

## Extension Points

### Adding New Uncertainty Types

In `0_experiment_manager.py`:

```python
if Math_Type == 'Your_New_Type':
    new_value_list = your_interpolation_function(
        time_list, value_list, 
        float(Values_per_Future[fut_id]),
        last_year_analysis, 
        Initial_Year_of_Uncertainty
    )
```

### Adding New Solvers

In `z_auxiliar_code.py`, function `run_osemosys()`:

```python
if solver == 'new_solver':
    str_solve = 'new_solver_command ' + model_file + ' ' + data_file
```

### Adding New Output Variables

In `Interface_RDM.xlsx`, `To_Print` sheet:

```
Parameter: NewVariable
Print: Yes
```

Then update `data_processor_new()` if special handling needed.
