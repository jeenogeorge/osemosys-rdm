# Tutorial: Running Your First Analysis

This tutorial walks you through running a complete OSeMOSYS-RDM analysis from scratch.

## Prerequisites

Before starting, ensure you have:

- [ ] OSeMOSYS-RDM installed (see [Installation](../getting-started/installation.md))
- [ ] A solver installed (GLPK at minimum)
- [ ] An OSeMOSYS scenario file

## Step 1: Prepare Your Scenario File

### Scenario File Format

Your scenario file should be a valid GNU MathProg data file. Here's a minimal structure:

```
###############
#    Sets     #
###############

set YEAR := 2020 2025 2030 2035 2040 2045 2050 ;
set TECHNOLOGY := PWRSOL001 PWRGAS001 PWRIMP001 PWRTRN001 ;
set FUEL := ELC NATGAS ;
set EMISSION := CO2 ;
set MODE_OF_OPERATION := 1 ;
set REGION := REG1 ;
set TIMESLICE := TS01 TS02 TS03 TS04 ;

###############
#  Parameters #
###############

param SpecifiedAnnualDemand default 0 :=
REG1 ELC 2020 100
REG1 ELC 2025 120
REG1 ELC 2030 140
REG1 ELC 2035 160
REG1 ELC 2040 180
REG1 ELC 2045 200
REG1 ELC 2050 220
;

# ... more parameters ...

end;
```

### Place the File

Copy your scenario file to:

```bash
cp Scenario1.txt osemosys-rdm/src/workflow/0_Scenarios/
```

## Step 2: Configure the Interface

Open `src/Interface_RDM.xlsx` and configure the Setup sheet:

### Essential Settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| Solver | `glpk` | Or `cbc`/`cplex`/`gurobi` |
| Run_Base_Future | `Yes` | Enable for first run |
| Run_RDM | `No` | Disable for this tutorial |
| Region | `REG1` | Match your scenario |
| OSeMOSYS_Model_Name | `model.v.5.3.txt` | Model formulation |
| Timeslices_model | `4` | Match your time slices |

### Save the File

```{important}
Save and close the Excel file before running the pipeline.
```

## Step 3: Run the Base Future

### Execute

```bash
cd osemosys-rdm
python run.py rdm
```

### Expected Output

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
Step 1 finished
Step 2 finished
Step 3 finished
...
----------------------------------------------------------------------
✅ RDM Pipeline completed in 2m 15s!
```

## Step 4: Review Results

### Check Output Files

```bash
ls -la src/workflow/1_Experiment/Executables/Scenario1_0/
```

Expected files:
```
Scenario1_0.txt           # Processed scenario file
Scenario1_0_Input.csv     # Input parameters
Scenario1_0_Output.csv    # Solution outputs
Scenario1_0_Output.sol    # Raw solver output
```

### View Results Summary

```python
import pandas as pd

# Load outputs
df = pd.read_csv('src/Results/OSEMOSYS_REG1_Energy_Output.csv')

# View columns
print(df.columns.tolist())

# Summary by technology
print(df.groupby('TECHNOLOGY')['Value'].sum())
```

## Step 5: Verify the Model

### Check Total Capacity

```python
capacity = df[df['Variable'] == 'TotalCapacityAnnual']
print(capacity[['TECHNOLOGY', 'YEAR', 'Value']])
```

### Check Production

```python
production = df[df['Variable'] == 'ProductionByTechnology']
print(production[['TECHNOLOGY', 'YEAR', 'Value']])
```

### Check Costs

```python
costs = df[df['Variable'] == 'TotalDiscountedCost']
print(costs[['REGION', 'Value']])
```

## Troubleshooting

### "Solver not found"

```bash
# Check solver installation
glpsol --version
```

If not found, install GLPK:
```bash
conda install -c conda-forge glpk
```

### "Set not found" Error

Check that all sets referenced in parameters exist:

```bash
# In your scenario file, verify:
set TECHNOLOGY := ... ;  # All technologies used
set FUEL := ... ;        # All fuels used
```

### "Infeasible" Solution

The model has no solution. Common causes:
- Demand exceeds available capacity
- Missing technology pathways
- Conflicting constraints

### Empty Output Files

If output files are empty:
1. Check solver log files (`.log`)
2. Verify the scenario file syntax
3. Ensure all required parameters are defined

## Next Steps

Now that you've successfully run a base future:

1. **Add uncertainties**: See [Uncertainty Analysis Tutorial](uncertainty-analysis.md)
2. **Run PRIM analysis**: See [Scenario Discovery Tutorial](scenario-discovery.md)
3. **Customize configuration**: See [Interface Configuration](../user-guide/interface-configuration.md)

## Complete Example

Here's a complete working example:

### Scenario File: `Scenario1.txt`

```
###############
#    Sets     #
###############

set YEAR := 2020 2025 2030 2035 2040 2045 2050 ;
set TECHNOLOGY := PWRSOL001 PWRGAS001 DEMAND ;
set FUEL := ELC NATGAS ;
set EMISSION := CO2 ;
set MODE_OF_OPERATION := 1 ;
set REGION := REG1 ;
set TIMESLICE := TS01 ;

###############
#  Parameters #
###############

param YearSplit default 0 :=
REG1 TS01 1
;

param SpecifiedAnnualDemand default 0 :=
[REG1,*,*]:
     2020 2025 2030 2035 2040 2045 2050 :=
ELC  100  120  140  160  180  200  220
;

param SpecifiedDemandProfile default 0 :=
[REG1,*,*]:
    2020 2025 2030 2035 2040 2045 2050 :=
ELC TS01 1 1 1 1 1 1 1
;

param CapacityToActivityUnit default 1 :=
REG1 PWRSOL001 31.536
REG1 PWRGAS001 31.536
;

param CapacityFactor default 1 :=
[REG1,*,*,*]:
    TS01 :=
PWRSOL001 2020 0.25
PWRSOL001 2025 0.25
PWRSOL001 2030 0.25
PWRSOL001 2035 0.25
PWRSOL001 2040 0.25
PWRSOL001 2045 0.25
PWRSOL001 2050 0.25
PWRGAS001 2020 0.85
PWRGAS001 2025 0.85
PWRGAS001 2030 0.85
PWRGAS001 2035 0.85
PWRGAS001 2040 0.85
PWRGAS001 2045 0.85
PWRGAS001 2050 0.85
;

param InputActivityRatio default 0 :=
[REG1,*,*,*,*]:
         1 :=
PWRGAS001 NATGAS 2020 2.5
PWRGAS001 NATGAS 2025 2.4
PWRGAS001 NATGAS 2030 2.3
PWRGAS001 NATGAS 2035 2.2
PWRGAS001 NATGAS 2040 2.1
PWRGAS001 NATGAS 2045 2.0
PWRGAS001 NATGAS 2050 1.9
;

param OutputActivityRatio default 0 :=
[REG1,*,*,*,*]:
         1 :=
PWRSOL001 ELC 2020 1
PWRSOL001 ELC 2025 1
PWRSOL001 ELC 2030 1
PWRSOL001 ELC 2035 1
PWRSOL001 ELC 2040 1
PWRSOL001 ELC 2045 1
PWRSOL001 ELC 2050 1
PWRGAS001 ELC 2020 1
PWRGAS001 ELC 2025 1
PWRGAS001 ELC 2030 1
PWRGAS001 ELC 2035 1
PWRGAS001 ELC 2040 1
PWRGAS001 ELC 2045 1
PWRGAS001 ELC 2050 1
;

param CapitalCost default 0 :=
[REG1,*,*]:
         2020 2025 2030 2035 2040 2045 2050 :=
PWRSOL001 1500 1200 1000 800  700  600  500
PWRGAS001 800  800  800  800  800  800  800
;

param VariableCost default 0 :=
[REG1,*,*,*]:
         1 :=
PWRGAS001 2020 5
PWRGAS001 2025 5
PWRGAS001 2030 5
PWRGAS001 2035 5
PWRGAS001 2040 5
PWRGAS001 2045 5
PWRGAS001 2050 5
;

param OperationalLife default 20 :=
REG1 PWRSOL001 25
REG1 PWRGAS001 30
;

param DiscountRate default 0.05 :=
REG1 0.08
;

#
end;
```

### Interface Settings

Setup sheet:
```
Solver: glpk
Run_Base_Future: Yes
Run_RDM: No
Region: REG1
Timeslices_model: 1
```

### Run Command

```bash
python run.py rdm
```

### Verify Success

```python
import pandas as pd
df = pd.read_csv('src/Results/OSEMOSYS_REG1_Energy_Output.csv')
print(f"Total records: {len(df)}")
print(f"Technologies: {df['TECHNOLOGY'].unique()}")
```
