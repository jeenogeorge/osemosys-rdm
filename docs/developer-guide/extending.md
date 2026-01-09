# Extending OSeMOSYS-RDM

This guide explains how to extend and customize OSeMOSYS-RDM for your specific needs.

## Adding Custom Uncertainty Types

### Understanding the Math Type System

OSeMOSYS-RDM supports several mathematical types for uncertainty propagation:

| Type | Function | Description |
|------|----------|-------------|
| Time_Series | `interpolation_non_linear_final()` | Non-linear to final value |
| Constant | `interpolation_constant_trajectory()` | Maintain constant |
| Linear | `interpolation_linear()` | Linear interpolation |
| Logistic | `interpolation_logistic_trajectory()` | S-curve |
| Timeslices_Curve | Custom | Shape modification |

### Creating a New Type

1. **Add the interpolation function** in `z_auxiliar_code.py`:

```python
def interpolation_exponential(time_list, value_list, multiplier, 
                               last_year, initial_year):
    """
    Exponential growth trajectory.
    
    Parameters
    ----------
    time_list : list
        Years for interpolation
    value_list : list
        Base values
    multiplier : float
        Final value multiplier
    last_year : int
        Last year of analysis
    initial_year : int
        Year uncertainty begins
    
    Returns
    -------
    list
        New value trajectory
    """
    import numpy as np
    
    new_values = []
    for i, year in enumerate(time_list):
        if year < initial_year:
            new_values.append(value_list[i])
        else:
            # Calculate years from start of uncertainty
            years_elapsed = year - initial_year
            total_years = last_year - initial_year
            
            # Exponential interpolation
            factor = (multiplier - 1) * (np.exp(years_elapsed/total_years) - 1) / (np.e - 1) + 1
            new_values.append(value_list[i] * factor)
    
    return new_values
```

2. **Register the type** in `0_experiment_manager.py`:

```python
# In the uncertainty application section
if Math_Type == 'Time_Series':
    new_value_list = deepcopy(AUX.interpolation_non_linear_final(...))
elif Math_Type == 'Exponential':  # ADD YOUR NEW TYPE
    new_value_list = deepcopy(AUX.interpolation_exponential(
        time_list, value_list, 
        float(Values_per_Future[fut_id]), 
        last_year_analysis, 
        Initial_Year_of_Uncertainty
    ))
```

3. **Use in Interface_RDM.xlsx**:

Set `X_Mathematical_Type` to `Exponential` for your uncertainty.

## Adding Custom Output Variables

### Step 1: Modify To_Print Sheet

Add your variable to `Interface_RDM.xlsx` → `To_Print`:

```
Parameter: MyCustomVariable
Print: Yes
```

### Step 2: Handle in Output Processing

If special processing is needed, modify `data_processor_new()` in `z_auxiliar_code.py`:

```python
def data_processor_new(file_path, structure_path, scenario, future, 
                        solver, params_to_print, output_format):
    # ... existing code ...
    
    # Add custom variable handling
    if 'MyCustomVariable' in params_to_print:
        # Calculate custom metric
        my_value = calculate_custom_metric(df)
        
        # Add to output
        output_row = {
            'Scenario': scenario,
            'Future': future,
            'Variable': 'MyCustomVariable',
            'Value': my_value
        }
        results.append(output_row)
```

## Creating Custom PRIM Metrics

### Adding New Outcomes

1. **Edit prim_structure.xlsx** in `Analysis_1/`:

```
# Outcomes sheet
ID: 10
Name: My_Custom_Metric
Source: OSeMOSYS outputs
Set_Type: TECHNOLOGY
Sets: TECH1; TECH2
Parameter: ProductionByTechnology
Processing: cumulative
Variable_Management: direct
```

2. **Add processing logic** if needed in `t3f2_prim_files_creator.py`:

```python
# In f2_exe_postproc function
if 'my_custom' in num_frml:
    # Custom calculation
    for y in range(len(apyr)):
        value = custom_calculation(file_data_f2, apyr[y])
        res_lists_sum[y] = value
```

### Creating Derived Metrics

Example: Ratio of two technologies

```python
# In PRIM processing
if 'tech_ratio' in num_frml:
    tech1_production = []
    tech2_production = []
    
    for y in range(len(apyr)):
        mask1 = (file_data['TECHNOLOGY'] == 'TECH1') & \
                (file_data['YEAR'] == apyr[y])
        tech1_production.append(file_data.loc[mask1, 'Value'].sum())
        
        mask2 = (file_data['TECHNOLOGY'] == 'TECH2') & \
                (file_data['YEAR'] == apyr[y])
        tech2_production.append(file_data.loc[mask2, 'Value'].sum())
    
    res_lists_sum = [t1/t2 if t2 > 0 else 0 
                     for t1, t2 in zip(tech1_production, tech2_production)]
```

## Adding New Solver Support

### Step 1: Modify run_osemosys()

In `z_auxiliar_code.py`:

```python
def run_osemosys(solver, output_dir, data_file, model_file, output_base):
    # ... existing code ...
    
    if solver == 'highs':  # NEW SOLVER
        # Generate LP file
        str_matrix = f'glpsol -m {model_file} -d {data_file} --wlp {output_base}.lp --check'
        os.system(str_matrix)
        
        # Solve with HiGHS
        str_solve = f'highs {output_base}.lp --solution_file {output_base}.sol'
        os.system(str_solve)
```

### Step 2: Handle Solution Parsing

If the solver has a different output format:

```python
def parse_highs_solution(sol_file):
    """Parse HiGHS solution file format."""
    variables = {}
    with open(sol_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                var_name = parts[0]
                value = float(parts[1])
                variables[var_name] = value
    return variables
```

### Step 3: Update data_processor_new()

```python
if solver == 'highs':
    solution = parse_highs_solution(file_path)
    # Process solution into standard format
```

## Customizing the DVC Pipeline

### Adding New Stages

1. **Create wrapper script** in `scripts/`:

```python
# scripts/run_my_stage.py
import sys
import json
from pathlib import Path

def generate_metrics(output_dir, metrics_file):
    metrics = {
        "stage": "my_stage",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "custom_metric": 42
    }
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

def main():
    # Your stage logic here
    pass

if __name__ == "__main__":
    main()
```

2. **Add to dvc.yaml**:

```yaml
stages:
  my_stage:
    cmd: python scripts/run_my_stage.py
    deps:
      - src/Results/
      - scripts/run_my_stage.py
    outs:
      - src/MyOutput/
    metrics:
      - src/my_stage_metrics.json:
          cache: false
    desc: My custom processing stage
```

3. **Update run.py** if needed:

```python
MY_STAGE = "my_stage"

def run_my_pipeline(env_name, force, skip_pull):
    """Execute my custom pipeline."""
    print("Running my custom stage...")
    repro_args = f"repro {MY_STAGE}"
    if force:
        repro_args += " --force"
    dvc_command(env_name, repro_args)
```

## Custom Visualization Pipelines

### Creating Analysis Scripts

```python
# scripts/visualize_results.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def load_results(results_dir):
    """Load and preprocess results."""
    output_file = list(results_dir.glob('*_Output.csv'))[0]
    return pd.read_csv(output_file)

def create_technology_comparison(df, output_dir):
    """Create technology comparison chart."""
    capacity = df[df['Variable'] == 'TotalCapacityAnnual']
    
    pivot = capacity.pivot_table(
        values='Value',
        index='YEAR',
        columns='TECHNOLOGY',
        aggfunc='mean'
    )
    
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot(kind='bar', stacked=True, ax=ax)
    ax.set_ylabel('Capacity (GW)')
    ax.set_title('Average Capacity by Technology')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'technology_comparison.png', dpi=150)
    plt.close()

def main():
    results_dir = Path('src/Results')
    output_dir = Path('src/Visualizations')
    output_dir.mkdir(exist_ok=True)
    
    df = load_results(results_dir)
    create_technology_comparison(df, output_dir)
    
    print(f"Visualizations saved to {output_dir}")

if __name__ == "__main__":
    main()
```

## Testing Extensions

### Unit Tests

```python
# tests/test_interpolation.py
import pytest
from src.workflow.z_auxiliar_code import interpolation_exponential

def test_exponential_interpolation():
    time_list = [2020, 2025, 2030, 2035, 2040]
    value_list = [100, 100, 100, 100, 100]
    multiplier = 1.5
    last_year = 2040
    initial_year = 2025
    
    result = interpolation_exponential(
        time_list, value_list, multiplier, last_year, initial_year
    )
    
    # Before uncertainty year, values unchanged
    assert result[0] == 100
    
    # After, values should increase
    assert result[-1] == 150  # or close to it
    
    # Should be monotonically increasing after initial_year
    for i in range(2, len(result)):
        assert result[i] >= result[i-1]

def test_exponential_no_change():
    """Multiplier of 1 should not change values."""
    time_list = [2020, 2025, 2030]
    value_list = [100, 100, 100]
    
    result = interpolation_exponential(
        time_list, value_list, 1.0, 2030, 2020
    )
    
    assert result == value_list
```

### Integration Tests

```python
# tests/test_pipeline.py
import subprocess
import pytest
from pathlib import Path

@pytest.fixture
def setup_test_env():
    """Set up test environment."""
    # Create minimal test scenario
    pass

def test_base_future_runs(setup_test_env):
    """Test that base future executes successfully."""
    result = subprocess.run(
        ['python', 'scripts/run_base_future.py'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    # Check outputs exist
    output_dir = Path('src/workflow/1_Experiment/Executables')
    assert any(output_dir.glob('*_0/*_Output.csv'))
```
