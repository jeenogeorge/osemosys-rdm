# AFR_RDM (Africa Robust Decision Making)

A comprehensive workflow tool for preprocessing, solving, and postprocessing OSeMOSYS energy models with built-in support for Robust Decision Making (RDM) experiments.

## Overview

AFR_RDM is a Python-based framework that streamlines the entire workflow for working with OSeMOSYS (Open Source Energy Modelling System) scenarios. The tool provides automated data processing, model execution with multiple solvers, and experimental capabilities for uncertainty analysis through RDM methodology.

### Key Features

- **Dual Operation Modes**:
  - **Base Future Mode**: Execute single baseline scenarios (Future 0)
  - **RDM Experiment Mode**: Generate and analyze multiple futures with uncertainty ranges
  
- **Multi-Solver Support**: Compatible with GLPK, CBC, and CPLEX solvers

- **Automated Workflow**: Complete preprocessing and postprocessing pipeline for OSeMOSYS models

- **Uncertainty Analysis**: Latin Hypercube Sampling (LHS) for generating futures with configurable tolerance ranges

- **Structured Output**: Organized CSV outputs ready for analysis and visualization

## Prerequisites

### System Requirements

- **Python**: Version 3.11 or higher
- **Solvers** (at least one required, install separately):
  - [GLPK](https://www.gnu.org/software/glpk/) (GNU Linear Programming Kit)
  - [CBC](https://github.com/coin-or/Cbc) (COIN-OR Branch and Cut)
  - [CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio) (IBM ILOG CPLEX Optimization Studio)

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

3. Ensure your chosen solver (GLPK, CBC, or CPLEX) is properly installed and accessible from the command line.

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
│   │   └── 3_Postprocessing/      # Output processing tools
│   ├── Interface_RDM.xlsx         # Main configuration interface
│   └── RUN_RDM.py                 # Main execution script
├── LICENSE
└── README.md
```

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
  - `Solver`: Choose "glpk", "cbc", or "cplex"
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

Generates and analyzes multiple futures:
1. Creates uncertainty ranges for specified parameters
2. Uses Latin Hypercube Sampling to generate futures
3. Executes each future scenario
4. Aggregates results for comparative analysis

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
- `src/Results/OSEMOSYS_SL_Energy_Input.csv`
- `src/Results/OSEMOSYS_SL_Energy_Output.csv`

## Advanced Configuration

### Customizing RDM Parameters

Edit `Interface_RDM.xlsx` to define:
- Uncertainty parameters and their ranges
- Number of futures to generate
- Sampling strategy parameters
- Output parameter selection

### Solver-Specific Notes

- **GLPK**: Free, open-source, suitable for medium-scale models
- **CBC**: Free, open-source, better performance for larger models
- **CPLEX**: Commercial, optimal for very large models (requires license)

## Troubleshooting

### Common Issues

1. **Solver not found**: Ensure the solver executable is in your system PATH
2. **Memory errors**: Large models may require more RAM; consider using CPLEX for better memory management
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