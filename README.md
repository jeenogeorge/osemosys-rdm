# AFR_RDM (Africa Robust Decision Making)

A comprehensive workflow tool for preprocessing, solving, and postprocessing OSeMOSYS energy models with built-in support for Robust Decision Making (RDM) experiments.

## Overview

AFR_RDM is a Python-based framework that streamlines the entire workflow for working with OSeMOSYS (Open Source Energy Modelling System) scenarios. The tool provides automated data processing, model execution with multiple solvers, and experimental capabilities for uncertainty analysis through RDM methodology.

### Key Features

- **Dual Operation Modes**:
  - **Base Future Mode**: Execute single baseline scenarios (Future 0)
  - **RDM Experiment Mode**: Generate and analyze multiple futures with uncertainty ranges
  
- **Multi-Solver Support**: Compatible with GLPK, CBC, CPLEX, and Gurobi solvers

- **Automated Workflow**: Complete preprocessing and postprocessing pipeline for OSeMOSYS models

- **Uncertainty Analysis**: Latin Hypercube Sampling (LHS) for generating futures with configurable tolerance ranges

- **Structured Output**: Organized CSV outputs ready for analysis and visualization

## Prerequisites

### System Requirements

- **Python**: Version 3.10 or higher
- **Solvers** (at least one required, install separately):
  - [GLPK](https://www.gnu.org/software/glpk/) (GNU Linear Programming Kit)
  - [CBC](https://github.com/coin-or/Cbc) (COIN-OR Branch and Cut)
  - [CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio) (IBM ILOG CPLEX Optimization Studio)
  - [Gurobi](https://www.gurobi.com/) (Gurobi Optimizer)

### Python Dependencies

Install the required Python packages:

```bash
pip install pandas numpy scipy xlsxwriter pyDOE pyarrow openpyxl
```

Or using a requirements file:

```bash
pip install -r requirements.txt
```

**Core Dependencies:**
- pandas
- numpy
- scipy
- xlsxwriter
- pyDOE (for Latin Hypercube Sampling)
- pyarrow (for Parquet file support)
- openpyxl (for Excel file handling)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/clg-admin/AFR_RDM.git
cd AFR_RDM
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure your chosen solver (GLPK, CBC, CPLEX, or Gurobi) is properly installed and accessible from the command line.

## Project Structure

```
AFR_RDM/
├── src/
│   ├── Results/                    # Output CSV files
│   ├── workflow/
│   │   ├── 0_Scenarios/           # Input scenario files (.txt)
│   │   ├── 1_Experiment/          # Experiment execution
│   │   │   ├── 0_From_Confection/ # Generated model structure
│   │   │   ├── Executables/       # Base future (Future 0) runs
│   │   │   └── Experimental_Platform/
│   │   │       └── Futures/       # RDM experiment futures
│   │   ├── 2_Miscellaneous/       # Reference files
│   │   ├── 3_Postprocessing/      # Output processing tools
│   │   │   ├── create_csv_concatenate.py
│   │   │   ├── config_concatenate.yaml
│   │   │   └── otoole_config/     # OSeMOSYS conversion templates
│   │   └── 4_PRIM/                # PRIM scenario discovery module
│   │       ├── t3f2_prim_files_creator.py
│   │       ├── PRIM_t3f2.yaml
│   │       ├── prim_files_creator_cntrl.xlsx
│   │       ├── Population.xlsx
│   │       └── t3b_sdiscovery/    # Scenario discovery analysis
│   │           ├── Analysis_1/
│   │           │   ├── prim_structure.xlsx
│   │           │   ├── comp_pfd_1.pickle
│   │           │   └── prim_files_creator.pickle
│   │           ├── experiment_data/
│   │           ├── Units.xlsx
│   │           ├── t3f1_prim_structure.py
│   │           ├── t3f3_prim_manager.py
│   │           ├── t3f4_range_finder_mapping.py
│   │           ├── t3f4_predominant_ranges_a1_e1_Experiment.xlsx
│   │           ├── sd_ana_1_exp_1_Experiment.csv
│   │           ├── sd_ana_1_exp_1_Experiment.txt
│   │           ├── sd_manager.txt
│   │           └── subtbl_ana_1_exp_1_Experiment.pickle
│   ├── Guides/                     # User documentation
│   │   ├── Guide AFR_RDM.html
│   │   └── Guide PRIM Module Configuration.html
│   ├── z_auxiliar_code.py         # Core library functions
│   ├── Interface_RDM.xlsx         # Main configuration interface
│   └── RUN_RDM.py                 # Main execution script
├── LICENSE
├── requirements.txt
└── README.md
```

## Core Components

### Main Scripts

- **RUN_RDM.py**: Primary execution script that orchestrates the entire workflow
- **z_auxiliar_code.py**: Core library containing utility functions for:
  - Time series interpolation (linear, non-linear, logistic)
  - OSeMOSYS file parsing and structure extraction
  - Dataset creation and manipulation
  - Solver execution (GLPK, CBC, CPLEX, Gurobi)
  - Output processing and data transformation

### Visualization

- **Dashboard.twbx**: Tableau dashboard for results visualization and analysis
  - **Note**: Due to file size constraints, this dashboard is not included in the repository. It can be generated or obtained separately.

### Documentation

Comprehensive HTML guides are available in `src/Guides/`:
- **Guide AFR_RDM.html**: Complete usage guide for the AFR_RDM framework
- **Guide PRIM Module Configuration.html**: Detailed instructions for PRIM module setup and configuration

## Usage

### 1. Prepare Input Scenarios

Create your OSeMOSYS scenario files in GNU MathProg format and place them in:
```
src/workflow/0_Scenarios/
```

**Note**: Scenario files can be created using tools from Climate Compatible Growth (CCG) such as:
- MUIO
- ClicSAND

### 2. Configure the Interface

Open `Interface_RDM.xlsx` and configure:

- **Setup Sheet**:
  - `Timeslices_model`: Number of time slices in your model
  - `Run_Base_Future`: "Yes" to run base scenario, "No" to skip
  - `Run_RDM`: "Yes" to run RDM experiment, "No" to skip
  - `Solver`: Choose "glpk", "cbc", "cplex", or "gurobi"
  - `OSeMOSYS_Model_Name`: Name of your OSeMOSYS model file

- **To_Print Sheet**: Specify which output parameters to export

### 3. Run the Workflow

Execute the main script:

```bash
cd src
python RUN_RDM.py
```

### Operation Modes

#### Base Future Mode (`Run_Base_Future: Yes`)

Executes a single baseline scenario:
1. Processes scenario structure
2. Creates input datasets
3. Solves the optimization model
4. Generates output datasets in CSV format

Output location: `src/workflow/1_Experiment/Executables/`

#### RDM Experiment Mode (`Run_RDM: Yes`)

Generates and analyzes multiple futures under uncertainty:
1. **Future 0**: Baseline scenario (executed first)
2. **Additional Futures**: Generated using Latin Hypercube Sampling based on user-defined uncertainty ranges
3. Creates uncertainty ranges for specified parameters
4. Executes each future scenario in parallel
5. Aggregates results for comparative analysis

The number of futures generated depends on the configuration specified by the user in the experiment settings.

Output location: `src/workflow/1_Experiment/Experimental_Platform/Futures/`

## Workflow Steps

The tool executes the following automated steps:

1. **Structure Extraction**: Extracts model structure from scenario files
2. **Data Preprocessing**: Converts scenario data into solver-compatible format
3. **Model Execution**: Runs OSeMOSYS with the selected solver
4. **Output Processing**: Converts solver outputs to structured CSV files
5. **RDM Generation** (if enabled): Creates and executes uncertainty scenarios
6. **Results Aggregation**: Consolidates outputs in `src/Results/`

## Output Files

### Base Future Outputs
- `Scenario_0_Input.csv`: Input parameters for base scenario
- `Scenario_0_Output.csv`: Optimization results for base scenario

### RDM Experiment Outputs
- `Scenario_N_Input.csv`: Input parameters for each future N
- `Scenario_N_Output.parquet`: Results for each future (Parquet format for efficiency)
- `input_dataset_f.parquet`: Aggregated input dataset
- `output_dataset_f.parquet`: Aggregated output dataset

### Final Results
The aggregated results are stored in `src/Results/` with filenames that include the region identifier:
- `src/Results/OSEMOSYS_{Region}_Energy_Input.csv`
- `src/Results/OSEMOSYS_{Region}_Energy_Output.csv`

Where `{Region}` corresponds to the value specified in the "Region" column of the "Setup" sheet in [Interface_RDM.xlsx](Interface_RDM.xlsx).

## Advanced Configuration

### Customizing RDM Parameters

Edit `Interface_RDM.xlsx` to define:
- Uncertainty parameters and their ranges
- Number of futures to generate
- Sampling strategy parameters
- Output parameter selection

### PRIM Module (Scenario Discovery)

The PRIM (Patient Rule Induction Method) module enables scenario discovery by identifying which combinations of uncertain input parameters lead to specific outcomes of interest.

#### Purpose

PRIM analyzes the results from RDM experiments to find "boxes" or regions in the uncertainty space where:
- Desirable outcomes occur (e.g., low costs, low emissions)
- Undesirable outcomes or risks occur (e.g., high costs, high emissions)

#### Key Features

- **Driver Analysis**: Identifies which uncertain parameters (drivers) most influence outcomes
- **Threshold Detection**: Finds parameter ranges that lead to outcomes above/below critical thresholds:
  - **High**: Values greater than 75th percentile
  - **Low**: Values lower than 25th percentile
  - **Mid**: Values greater than 50th percentile
  - **Zero**: Values lower than zero
- **Multi-metric Support**: Analyzes costs, emissions, and other metrics simultaneously
- **Temporal Analysis**: Evaluates outcomes across different time periods

#### Configuration Files

The PRIM module requires several configuration files located in `src/workflow/4_PRIM/`:

1. **prim_structure.xlsx**: Defines the analysis structure
   - **Sequences sheet**: Maps drivers to outcomes with detailed formulas
   - **Outcomes sheet**: Lists unique outcomes without repetition

2. **Population.xlsx**: Historical and projected population data for normalization

3. **prim_files_creator_cntrl.xlsx**: Execution control parameters
   - **match_exp_ana sheet**: Links experiments to analyses
   - **periods sheet**: Defines temporal analysis periods
   - **dtype sheet**: Specifies data types for processing

4. **Units.xlsx**: Measurement units for each driver (MUSD, PJ, GgCO2e, etc.)

5. **PRIM_t3f2.yaml**: Main configuration file
   ```yaml
   # Base scenario name
   BAU: 'Scenario1'

   # Model names (must match Region from Interface_RDM.xlsx)
   ose_inputs: 'OSeMOSYS-{Region} inputs'
   ose_oupts: 'OSeMOSYS-{Region} outputs'
   ```

#### Execution Scripts

Located in `src/workflow/4_PRIM/`:
- `t3f2_prim_files_creator.py`: Generates PRIM analysis files
- `t3b_sdiscovery/t3f1_prim_structure.py`: Defines PRIM structure
- `t3b_sdiscovery/t3f3_prim_manager.py`: Executes PRIM analysis
- `t3b_sdiscovery/t3f4_range_finder_mapping.py`: Maps predominant parameter ranges

#### Output Files

Results are stored in `src/workflow/4_PRIM/t3b_sdiscovery/`:
- **t3f4_predominant_ranges_*.xlsx**: Contains identified parameter ranges with columns:
  - `Driver`: Uncertain parameter being analyzed
  - `Min_Norm` / `Max_Norm`: Normalized range boundaries (0-1)
  - `Outcome_Type`: "Desirable" or "Risk"
  - `Metric`: "Costs", "Emissions", or "All"
  - `Period`: Temporal range of analysis
  - `Case`: Scenario identifier grouping related drivers

#### Usage Guide

Detailed configuration instructions are available in:
- `src/Guides/Guide PRIM Module Configuration.html`

For more information on PRIM methodology, see the included documentation.

### Solver-Specific Notes

- **GLPK**: Free, open-source, suitable for medium-scale models
- **CBC**: Free, open-source, better performance for larger models
- **CPLEX**: Commercial, optimal for very large models (requires license)
- **Gurobi**: Commercial, high-performance solver for large-scale optimization (requires license)

## Troubleshooting

### Common Issues

1. **Solver not found**: Ensure the solver executable is in your system PATH
2. **Memory errors**: Large models may require more RAM; consider using CPLEX or Gurobi for better memory management
3. **Import errors**: Verify all Python dependencies are installed
4. **File format errors**: Ensure scenario files are in valid GNU MathProg format

### Log Files

The tool generates log files during execution:
- `cplex.log`: CPLEX solver log (when using CPLEX)
- `clone1.log`, `clone2.log`: Additional execution logs

## Related Tools

This workflow integrates with Climate Compatible Growth (CCG) tools:
- **MUIO**: Model User Interface and Optimizer
- **ClicSAND**: Climate-Compatible Growth Scenario Analysis and Navigation Dashboard

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## References

- [OSeMOSYS](http://www.osemosys.org/): Open Source Energy Modelling System
- [Climate Compatible Growth](https://climatecompatiblegrowth.com/): CCG Initiative
- [pyDOE](https://pythonhosted.org/pyDOE/): Design of Experiments for Python

## Acknowledgments

This tool was developed as part of energy system modeling research, building upon the OSeMOSYS framework and RDM methodology for decision-making under uncertainty.
