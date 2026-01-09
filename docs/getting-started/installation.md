# Installation

This guide covers the installation of OSeMOSYS-RDM and its dependencies.

## Prerequisites

Before installing OSeMOSYS-RDM, ensure you have the following:

### Required Software

- **Python 3.10+**: Required for all execution modes
- **Conda/Miniconda/Anaconda**: Required for DVC automation (optional for manual execution)
- **At least one solver** installed and available in PATH:
  - [GLPK](https://www.gnu.org/software/glpk/) (free, **required** for preprocessing)
  - [CBC](https://github.com/coin-or/Cbc) (free)
  - [CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio) (commercial)
  - [Gurobi](https://www.gurobi.com/) (commercial)

### Optional Software

- **Git**: Recommended but not required. The pipeline can run without Git installed.
- **DVC remote storage**: Required if you want to share large artifacts across machines.

## Installation Methods

### Option 1: Automated Setup (Recommended)

The simplest way to get started is to clone the repository and run the automated setup:

```bash
# Clone the repository
git clone https://github.com/clg-admin/osemosys-rdm.git
cd osemosys-rdm

# Run the pipeline (this will automatically set up the environment)
python run.py rdm
```

The automated setup will:

1. Create a Conda environment named `AFR-RDM-env`
2. Install all required dependencies (pandas, numpy, DVC, etc.)
3. Initialize DVC if needed
4. Execute the complete pipeline

### Option 2: Manual Setup

For more control over the installation process:

```bash
# Clone the repository
git clone https://github.com/clg-admin/osemosys-rdm.git
cd osemosys-rdm

# Create and activate the conda environment
conda env create -f environment.yaml
conda activate AFR-RDM-env

# Alternatively, install with pip
pip install -r requirements.txt
```

## Solver Installation

### GLPK (Required)

GLPK is required for preprocessing. Install it based on your operating system:

::::{tab-set}

:::{tab-item} Ubuntu/Debian
```bash
sudo apt-get install glpk-utils
```
:::

:::{tab-item} macOS
```bash
brew install glpk
```
:::

:::{tab-item} Windows
Download from [GLPK for Windows](https://sourceforge.net/projects/winglpk/) and add to PATH.
:::

:::{tab-item} Conda
```bash
conda install -c conda-forge glpk
```
:::

::::

### CBC (Free, Optional)

CBC often provides better performance than GLPK for larger problems:

::::{tab-set}

:::{tab-item} Ubuntu/Debian
```bash
sudo apt-get install coinor-cbc
```
:::

:::{tab-item} macOS
```bash
brew install coin-or-tools/coinor/cbc
```
:::

:::{tab-item} Conda
```bash
conda install -c conda-forge coincbc
```
:::

::::

### Commercial Solvers

For CPLEX or Gurobi:

1. Obtain a license (academic licenses are often available for free)
2. Install following the vendor's instructions
3. Ensure the solver executable is in your system PATH

## Verifying Installation

After installation, verify everything is working:

```bash
# Check Python version
python --version

# Check solver availability
glpsol --version

# Check DVC installation
dvc --version

# Run a quick test
python run.py rdm --help
```

## Troubleshooting

### Common Issues

**Solver not found**

If you get a "solver not found" error:

1. Verify the solver is installed: `glpsol --version` or `cbc -version`
2. Check that the solver is in your PATH
3. For commercial solvers, verify the license is valid

**Environment issues**

If you encounter environment problems:

```bash
# Remove and recreate the environment
conda env remove -n AFR-RDM-env
conda env create -f environment.yaml
```

**Import errors**

If you get import errors for Python packages:

```bash
# Reinstall dependencies
conda activate AFR-RDM-env
pip install -r requirements.txt
```

## Next Steps

Once installation is complete:

1. Read the [Quickstart Guide](quickstart.md) to run your first analysis
2. Learn about [Configuration](configuration.md) options
3. Explore the [Workflow Overview](../user-guide/workflow-overview.md)
