# Interface Configuration Guide

This guide provides detailed documentation for the `Interface_RDM.xlsx` configuration file.

## Overview

`Interface_RDM.xlsx` is the central configuration file that controls all aspects of the OSeMOSYS-RDM workflow. It contains multiple sheets, each handling different configuration aspects.

## Sheet Reference

| Sheet | Purpose |
|-------|---------|
| Setup | Main execution parameters |
| To_Print | Output variables to export |
| Uncertainty_Table | RDM uncertainty definitions |
| Params_Sets_Vari | Parameter-set mappings |

## Setup Sheet

### Parameter Reference

#### Execution Control

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| Run_Base_Future | String | Yes/No | Execute baseline scenario |
| Run_RDM | String | Yes/No | Execute RDM experiment |
| Scenario_to_Reproduce | String | Experiment/All/{name} | Which scenarios to run |

#### Solver Configuration

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| Solver | String | glpk/cbc/cplex/gurobi | Optimization solver |
| OSeMOSYS_Model_Name | String | filename | Model formulation file |

#### Model Settings

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| Region | String | Any | Model region identifier |
| Timeslices_model | Integer | 1-8760 | Number of time slices |

#### RDM Settings

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| Number_of_Runs | Integer | ≥1 | Number of futures to generate |
| Parallel_Use | Integer | ≥1 | Batch size for parallelization |
| Experiment_ID | String | Any | Unique experiment identifier |
| Initial_Year_of_Uncertainty | Integer | Year | Global uncertainty start year |

### Example Configuration

```
Solver: cplex
Run_Base_Future: Yes
Run_RDM: Yes
Region: UGA
OSeMOSYS_Model_Name: model.v.5.3.txt
Timeslices_model: 48
Number_of_Runs: 100
Parallel_Use: 10
Scenario_to_Reproduce: Experiment
Experiment_ID: 1
Initial_Year_of_Uncertainty: 2025
```

## To_Print Sheet

Controls which OSeMOSYS output variables are exported.

### Structure

| Column | Description |
|--------|-------------|
| Parameter | OSeMOSYS variable name |
| Print | Mark with an **X** to include in output (not Yes/No) |

```{note}
To enable an output parameter for printing, place an **X** in the Print column. Do not use "Yes" or "No".
```

### Common Output Variables

#### Cost Variables
- `TotalDiscountedCost`
- `CapitalInvestment`
- `OperatingCost`
- `AnnualFixedOperatingCost`
- `AnnualVariableOperatingCost`

#### Capacity Variables
- `TotalCapacityAnnual`
- `NewCapacity`
- `AccumulatedNewCapacity`

#### Activity Variables
- `ProductionByTechnology`
- `TotalAnnualTechnologyActivityByMode`
- `RateOfActivity`
- `UseByTechnology`

#### Emission Variables
- `AnnualEmissions`
- `AnnualTechnologyEmission`

#### Trade Variables
- `Export`
- `Import`

## Uncertainty_Table Sheet

Defines all uncertain parameters for RDM analysis.

### Column Definitions

#### Identification

| Column | Type | Description |
|--------|------|-------------|
| X_Num | Integer | Unique identifier (1, 2, 3, ...) |
| X_Category | String | Grouping category |
| X_Plain_English_Description | String | Human-readable description |
| XLRM_ID | String | Optional XLRM framework ID |

#### Mathematical Specification

| Column | Type | Description |
|--------|------|-------------|
| X_Mathematical_Type | String | Variation method |
| Explored_Parameter_of_X | String | What aspect to vary |
| Min_Value | Float | Lower bound (multiplier or value) |
| Max_Value | Float | Upper bound (multiplier or value) |

#### OSeMOSYS Mapping

| Column | Type | Description |
|--------|------|-------------|
| Involved_Scenarios | String | Semicolon-separated scenario list |
| Involved_First_Sets_in_Osemosys | String | Primary set elements |
| Involved_Second_Sets_in_Osemosys | String | Secondary set elements |
| Involved_Third_Sets_in_Osemosys | String | Tertiary set elements |
| Exact_Parameters_Involved_in_Osemosys | String | OSeMOSYS parameter names |

```{important}
**Multiple Values in Columns:**
- When specifying multiple values in the columns mentioned above (sets, scenarios, parameters), separate them with ` ; ` (space-semicolon-space)
- The spaces before and after the semicolon are **required**
- Example: `PWRSOL001 ; PWRSOL002` (correct) vs `PWRSOL001;PWRSOL002` (incorrect)
- **Note:** The option "All" is not valid. You must specify each value individually.
```

#### Temporal Settings

| Column | Type | Description |
|--------|------|-------------|
| Initial_Year_of_Uncertainty | Integer | Year uncertainty begins |

### X_Mathematical_Type Options

#### Time_Series

Non-linear interpolation from current trajectory to modified final value.

```
Original: 2025: 100 → 2030: 120 → 2050: 200
Modified (mult=1.2): 2025: 100 → 2030: 124 → 2050: 240
```

**Use for:** Cost projections, demand growth, efficiency improvements

#### Constant

Maintains value constant from uncertainty start year.

```
Original: 2025: 100 → 2030: 100 → 2050: 100
Result: Values frozen at start year level
```

**Use for:** Fixed policy constraints, technology limits

#### Linear

Linear interpolation to modified final value.

```
Original: 2025: 100 → 2050: 200
Modified: Linear path from 100 to 240
```

**Use for:** Simple linear projections

#### Logistic

S-curve (sigmoid) trajectory.

```
Slow start → Rapid middle growth → Saturation
```

**Use for:** Technology adoption curves, market penetration

#### Timeslices_Curve

Modifies time slice profiles using predefined curves.

```
References: shape_of_demand.csv
Selects curve based on LHS sample
```

**Use for:** Demand shape uncertainty, load profiles

### Explored_Parameter_of_X Options

| Value | Description |
|-------|-------------|
| Final_Value | Modify the final year value |
| Multiplier | Apply constant multiplier |
| Change_Curve | Change the profile/shape |

### Example Entries

#### Fuel Cost Uncertainty

```
X_Num: 1
X_Category: Fuel Costs
X_Plain_English_Description: Natural gas import price
X_Mathematical_Type: Time_Series
Explored_Parameter_of_X: Final_Value
Min_Value: 0.7
Max_Value: 1.5
Involved_Scenarios: Scenario1 ; Scenario2
Involved_First_Sets_in_Osemosys: IMPNATGAS
Exact_Parameters_Involved_in_Osemosys: VariableCost
Initial_Year_of_Uncertainty: 2025
```

#### Technology Limit Uncertainty

```
X_Num: 2
X_Category: Technology Limits
X_Plain_English_Description: Solar PV maximum installable capacity
X_Mathematical_Type: Time_Series
Explored_Parameter_of_X: Final_Value
Min_Value: 0.5
Max_Value: 2.0
Involved_Scenarios: Scenario1
Involved_First_Sets_in_Osemosys: PWRSOL001 ; PWRSOL002
Exact_Parameters_Involved_in_Osemosys: TotalAnnualMaxCapacity
Initial_Year_of_Uncertainty: 2025
```

#### Demand Shape Uncertainty

```
X_Num: 3
X_Category: Demand
X_Plain_English_Description: Electricity demand profile shape
X_Mathematical_Type: Timeslices_Curve
Explored_Parameter_of_X: Change_Curve
Min_Value: 1
Max_Value: 10
Involved_Scenarios: Scenario1
Involved_First_Sets_in_Osemosys: ELCDEM
Involved_Second_Sets_in_Osemosys: All
Exact_Parameters_Involved_in_Osemosys: SpecifiedDemandProfile
Initial_Year_of_Uncertainty: 2025
```

## Params_Sets_Vari Sheet

Maps parameters to their dependent sets for correct data manipulation.

### Structure

| Column | Description |
|--------|-------------|
| parameter | OSeMOSYS parameter name |
| Number | Count of dependent sets (1-3) |
| Set1 | First set type |
| Set2 | Second set type (if applicable) |
| Set3 | Third set type (if applicable) |

### Set Type Values

- `TECHNOLOGY`
- `FUEL` / `COMMODITY`
- `YEAR`
- `TIMESLICE`
- `MODE_OF_OPERATION`
- `EMISSION`
- `REGION`
- `STORAGE`

### Example Entries

```
parameter: VariableCost
Number: 2
Set1: TECHNOLOGY
Set2: MODE_OF_OPERATION

parameter: CapacityFactor
Number: 2
Set1: TECHNOLOGY
Set2: TIMESLICE

parameter: SpecifiedDemandProfile
Number: 2
Set1: FUEL
Set2: TIMESLICE
```

## Validation Tips

### Before Running

1. **Check solver availability**: Ensure selected solver is installed
2. **Verify scenario files**: Confirm `.txt` files exist in `0_Scenarios/`
3. **Validate sets**: Check that referenced sets exist in scenario files
4. **Check parameter names**: Ensure exact OSeMOSYS parameter names

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Parameter not found" | Typo in parameter name | Check exact OSeMOSYS spelling |
| "Set not found" | Set element doesn't exist | Verify in scenario file |
| "NaN values" | Formula error in Excel | Check cell references |
| "Index out of range" | Missing set mapping | Add to Params_Sets_Vari |
