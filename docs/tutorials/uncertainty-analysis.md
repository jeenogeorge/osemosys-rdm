# Tutorial: Uncertainty Analysis with RDM

This tutorial guides you through setting up and running a Robust Decision Making (RDM) uncertainty analysis.

## Prerequisites

- Completed the [Basic Run Tutorial](basic-run.md)
- A working base future (Future 0)
- Understanding of your model's key uncertainties

## Overview

In this tutorial, we will:

1. Define uncertain parameters
2. Configure the RDM experiment
3. Run the analysis
4. Analyze the results

## Step 1: Identify Uncertainties

### What to Make Uncertain

Good candidates for uncertainty analysis:

| Category | Examples |
|----------|----------|
| **Fuel Costs** | Natural gas prices, coal prices, oil prices |
| **Technology Costs** | Solar PV capital cost, battery storage cost |
| **Demand** | Electricity demand growth, transport demand |
| **Policy** | Carbon prices, renewable mandates |
| **Technology Performance** | Capacity factors, efficiency improvements |

### Determine Ranges

For each uncertainty, determine plausible ranges:

| Parameter | Min | Max | Rationale |
|-----------|-----|-----|-----------|
| Gas Price | 0.7x | 1.5x | Historical volatility ±30% |
| Solar Cost | 0.5x | 1.2x | Technology learning curves |
| Demand Growth | 0.8x | 1.3x | Economic uncertainty |

## Step 2: Configure Uncertainties

Open `src/Interface_RDM.xlsx` and navigate to the `Uncertainty_Table` sheet.

### Add Your First Uncertainty: Fuel Cost

Fill in a new row:

| Column | Value |
|--------|-------|
| X_Num | 1 |
| X_Category | Fuel Costs |
| X_Plain_English_Description | Natural gas import price uncertainty |
| X_Mathematical_Type | Time_Series |
| Explored_Parameter_of_X | Final_Value |
| Min_Value | 0.7 |
| Max_Value | 1.5 |
| Involved_Scenarios | Scenario1 |
| Involved_First_Sets_in_Osemosys | IMPNATGAS |
| Exact_Parameters_Involved_in_Osemosys | VariableCost |
| Initial_Year_of_Uncertainty | 2025 |

### Add Second Uncertainty: Technology Cost

| Column | Value |
|--------|-------|
| X_Num | 2 |
| X_Category | Technology Costs |
| X_Plain_English_Description | Solar PV capital cost reduction |
| X_Mathematical_Type | Time_Series |
| Explored_Parameter_of_X | Final_Value |
| Min_Value | 0.5 |
| Max_Value | 1.2 |
| Involved_Scenarios | Scenario1 |
| Involved_First_Sets_in_Osemosys | PWRSOL001 ; PWRSOL002 |
| Exact_Parameters_Involved_in_Osemosys | CapitalCost |
| Initial_Year_of_Uncertainty | 2025 |

### Add Third Uncertainty: Demand

| Column | Value |
|--------|-------|
| X_Num | 3 |
| X_Category | Demand |
| X_Plain_English_Description | Electricity demand growth rate |
| X_Mathematical_Type | Time_Series |
| Explored_Parameter_of_X | Final_Value |
| Min_Value | 0.8 |
| Max_Value | 1.3 |
| Involved_Scenarios | Scenario1 |
| Involved_First_Sets_in_Osemosys | ELC |
| Exact_Parameters_Involved_in_Osemosys | SpecifiedAnnualDemand |
| Initial_Year_of_Uncertainty | 2025 |

## Step 3: Configure the Experiment

In the `Setup` sheet, configure:

| Parameter | Value | Notes |
|-----------|-------|-------|
| Run_Base_Future | Yes | Generate baseline first |
| Run_RDM | Yes | Enable RDM experiment |
| Number_of_Runs | 50 | Start with 50 futures |
| Parallel_Use | 5 | Adjust based on your RAM |
| Solver | cplex | Or cbc for better speed |

```{tip}
Start with 50 futures to test your configuration, then increase to 100-500 for final analysis.
```

## Step 4: Run the Experiment

### Execute

```bash
python run.py rdm
```

### Monitor Progress

Watch for output like:

```
======================================================================
🔬 RDM Pipeline (Robust Decision Making)
======================================================================
Stages: base_future → rdm_experiment → postprocess
======================================================================

🔄 Executing RDM Pipeline...
----------------------------------------------------------------------
Step 1 finished
...
# This is future: 1 and scenario Scenario1
# This is future: 2 and scenario Scenario1
...
# This is future: 50 and scenario Scenario1
...
----------------------------------------------------------------------
✅ RDM Pipeline completed in 25m 15s!
```

### Check for Errors

If futures fail:
- Check solver logs in the future directory
- Verify parameter ranges don't create infeasible models
- Review error messages carefully

## Step 5: Analyze Results

### Load the Data

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load results
df = pd.read_csv('src/Results/OSEMOSYS_REG1_Energy_Output.csv')

# Filter to cost results
costs = df[df['Variable'] == 'TotalDiscountedCost'].copy()
costs['Future.ID'] = costs['Future.ID'].astype(int)
```

### Visualize Cost Distribution

```python
# Get cost by future
cost_by_future = costs.groupby('Future.ID')['Value'].sum()

# Plot histogram
plt.figure(figsize=(10, 6))
plt.hist(cost_by_future, bins=20, edgecolor='black')
plt.xlabel('Total Discounted Cost (Million USD)')
plt.ylabel('Frequency')
plt.title('Distribution of System Costs Across Futures')
plt.axvline(cost_by_future.iloc[0], color='red', 
            linestyle='--', label='Base Future')
plt.legend()
plt.savefig('cost_distribution.png', dpi=150)
plt.show()
```

### Compare Technologies

```python
# Get capacity by technology and future
capacity = df[df['Variable'] == 'TotalCapacityAnnual'].copy()
capacity_2050 = capacity[capacity['YEAR'] == 2050]

# Pivot table
cap_pivot = capacity_2050.pivot_table(
    values='Value',
    index='Future.ID',
    columns='TECHNOLOGY',
    aggfunc='sum'
)

# Box plot
cap_pivot.boxplot(figsize=(12, 6))
plt.ylabel('Capacity (GW)')
plt.title('Capacity Distribution in 2050 Across Futures')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('capacity_distribution.png', dpi=150)
plt.show()
```

### Identify Key Scenarios

```python
# Find high-cost scenarios
cost_threshold = cost_by_future.quantile(0.9)
high_cost_futures = cost_by_future[cost_by_future > cost_threshold].index.tolist()

print(f"High-cost scenarios (top 10%): {high_cost_futures}")

# Find low-cost scenarios
cost_threshold_low = cost_by_future.quantile(0.1)
low_cost_futures = cost_by_future[cost_by_future < cost_threshold_low].index.tolist()

print(f"Low-cost scenarios (bottom 10%): {low_cost_futures}")
```

## Step 6: Examine Input Variations

### Load Input Data

```python
# Load inputs
inputs = pd.read_csv('src/Results/OSEMOSYS_REG1_Energy_Input.csv')

# Filter to our uncertain parameters
gas_cost = inputs[
    (inputs['TECHNOLOGY'] == 'IMPNATGAS') & 
    (inputs['VariableCost'].notna())
].copy()
```

### Correlate Inputs and Outputs

```python
# Merge inputs and outputs for correlation analysis
# This requires matching Future.ID

# Get gas cost by future (using last year)
gas_by_future = gas_cost[gas_cost['YEAR'] == 2050].groupby('Future.ID')['VariableCost'].mean()

# Merge with total cost
analysis_df = pd.DataFrame({
    'Total_Cost': cost_by_future,
    'Gas_Price': gas_by_future
}).dropna()

# Calculate correlation
correlation = analysis_df['Total_Cost'].corr(analysis_df['Gas_Price'])
print(f"Correlation between gas price and total cost: {correlation:.3f}")

# Scatter plot
plt.figure(figsize=(8, 6))
plt.scatter(analysis_df['Gas_Price'], analysis_df['Total_Cost'], alpha=0.5)
plt.xlabel('Gas Price Multiplier')
plt.ylabel('Total System Cost (Million USD)')
plt.title(f'Gas Price vs System Cost (r={correlation:.3f})')
plt.savefig('correlation_analysis.png', dpi=150)
plt.show()
```

## Step 7: Statistical Summary

### Generate Summary Statistics

```python
# Summary by future
summary = pd.DataFrame({
    'Metric': ['Total Cost', 'Solar Capacity 2050', 'Gas Capacity 2050', 'Emissions 2050'],
    'Mean': [
        cost_by_future.mean(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('SOL')]['Value'].mean(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('GAS')]['Value'].mean(),
        df[(df['Variable'] == 'AnnualEmissions') & (df['YEAR'] == 2050)]['Value'].mean()
    ],
    'Std': [
        cost_by_future.std(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('SOL')]['Value'].std(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('GAS')]['Value'].std(),
        df[(df['Variable'] == 'AnnualEmissions') & (df['YEAR'] == 2050)]['Value'].std()
    ],
    'Min': [
        cost_by_future.min(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('SOL')]['Value'].min(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('GAS')]['Value'].min(),
        df[(df['Variable'] == 'AnnualEmissions') & (df['YEAR'] == 2050)]['Value'].min()
    ],
    'Max': [
        cost_by_future.max(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('SOL')]['Value'].max(),
        capacity_2050[capacity_2050['TECHNOLOGY'].str.contains('GAS')]['Value'].max(),
        df[(df['Variable'] == 'AnnualEmissions') & (df['YEAR'] == 2050)]['Value'].max()
    ]
})

print(summary.to_string(index=False))
```

## Next Steps

Now that you have RDM results:

1. **Run PRIM analysis**: Identify which uncertainties drive outcomes
   - See [Scenario Discovery Tutorial](scenario-discovery.md)

2. **Increase sample size**: Run more futures for robust conclusions
   ```
   Number_of_Runs: 200
   ```

3. **Add more uncertainties**: Expand the analysis scope

4. **Visualize with Tableau**: Use the provided dashboard templates

## Common Issues

### Model Becomes Infeasible

Some parameter combinations may create impossible models:

```python
# Check which futures failed
import os
futures_dir = 'src/workflow/1_Experiment/Experimental_Platform/Futures/Scenario1'
all_futures = os.listdir(futures_dir)

for fut in all_futures:
    output_file = f"{futures_dir}/{fut}/{fut}_Output.parquet"
    if not os.path.exists(output_file):
        print(f"Missing output for: {fut}")
```

**Solutions:**
- Narrow uncertainty ranges
- Add slack variables to the model
- Review constraint formulations

### Memory Errors

```bash
# Reduce parallel execution
# In Interface_RDM.xlsx:
Parallel_Use: 3  # Lower value
```

### Slow Execution

- Use a commercial solver (CPLEX/Gurobi)
- Reduce model size (fewer time slices, technologies)
- Use parallelization effectively
