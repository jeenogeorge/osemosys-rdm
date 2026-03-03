# RDM Pipeline

The Robust Decision Making (RDM) pipeline is the core of OSeMOSYS-RDM, enabling systematic exploration of uncertainty in energy system models.

## What is RDM?

Robust Decision Making is a decision support methodology that:

- Explores a wide range of plausible futures
- Identifies strategies that perform well across many scenarios
- Helps decision-makers understand vulnerabilities
- Supports adaptive policy design

## Pipeline Stages

### 1. Base Future Generation

The base future (Future 0) establishes the reference scenario.

```bash
python scripts/run_base_future.py
```

**What happens:**
1. Reads scenario from `src/workflow/0_Scenarios/`
2. Extracts model structure to `B1_Model_Structure.xlsx`
3. Solves the optimization problem
4. Exports results to CSV format

### 2. Uncertainty Sampling

Latin Hypercube Sampling (LHS) generates parameter combinations.

**Why LHS?**
- Ensures uniform coverage of the uncertainty space
- More efficient than random sampling
- Stratified sampling across all dimensions

**Configuration:**
```
# In Interface_RDM.xlsx, Setup sheet:
Number_of_Runs: 100  # Number of futures to generate
```

### 3. Future Generation and Solving

Each future is created by modifying baseline parameters.

```python
# Pseudocode of the process
for future_id in range(1, N+1):
    # Generate parameter modifications from LHS sample
    modifications = apply_uncertainties(baseline, lhs_sample[future_id])

    # Create scenario file
    create_scenario_file(modifications, future_id)

    # Preprocess data file (add sets, compute CRF/PvAnnuity)
    preprocess_data(scenario_file)

    # Solve optimization
    solve(scenario_file, solver)

    # Export results
    export_results(future_id)
```

#### Automatic Data Preprocessing

Before each future is solved, the data file is automatically pre-processed by `preprocess_data.py`. This step:

1. Parses bracket-format parameters (`OutputActivityRatio`, `InputActivityRatio`, `EmissionActivityRatio`, etc.)
2. Calculates `CapitalRecoveryFactor` and `PvAnnuity` for each technology
3. Adds preprocessed sets (`MODExTECHNOLOGYperFUELout`, `MODExTECHNOLOGYperFUELin`, `MODEperTECHNOLOGY`, etc.)

This is required for OSeMOSYS model formulation v5.4 and reduces matrix generation time.

#### EV UDC Sign Correction

When using User-Defined Constraints (UDC) to model EV penetration caps, LHS perturbations can flip coefficient signs, causing infeasibility. The workflow includes automatic post-perturbation sign correction:

- Scans `UDCMultiplierTotalCapacity`, `UDCMultiplierNewCapacity`, and `UDCMultiplierActivity`
- Ensures conventional technology coefficients (e.g., diesel/gasoline) remain **negative**
- Ensures electric technology coefficients remain **positive**
- Clamps flipped values to a small epsilon (0.001)

This is configured via three fields in `Interface_RDM.xlsx` → `Setup` sheet:

| Field | Description | Example |
|---|---|---|
| `EV_Conventional_Patterns` | Semicolon-separated substrings for conventional technologies | `DSL;DSH;GSL` |
| `EV_Electric_Pattern` | Substring for electric technologies | `ELC` |
| `EV_UDCs` | Semicolon-separated EV penetration UDC names | `2TRAHTREVCAP;2TRALTREVCAP` |

If any of these fields is empty, the correction is skipped. Correction logs are saved to `Experimental_Platform/Logs/UDC_Corrections/`.

### 4. Result Aggregation

Results are consolidated into unified datasets across two stages:

- **`rdm_experiment` stage:** generates `OSEMOSYS_{Region}_Energy_Input.csv` immediately after all futures are solved
- **`postprocess` stage:** generates `OSEMOSYS_{Region}_Energy_Output.csv`

```
src/Results/
├── OSEMOSYS_{Region}_Energy_Input.csv   # Generated in rdm_experiment
├── OSEMOSYS_{Region}_Energy_Output.csv  # Generated in postprocess
└── *.parquet                            # Efficient intermediate storage
```

## Configuring Uncertainties

### Uncertainty Table Structure

Define uncertainties in `Interface_RDM.xlsx` → `Uncertainty_Table` sheet:

```{list-table}
:header-rows: 1

* - Column
  - Description
  - Example
* - X_Num
  - Unique ID
  - 1, 2, 3...
* - X_Category
  - Grouping category
  - "Fuel Costs"
* - Min_Value
  - Lower bound
  - 0.8
* - Max_Value
  - Upper bound
  - 1.2
* - X_Mathematical_Type
  - Variation method
  - "Time_Series"
```

### Mathematical Types

#### Time_Series

Interpolates from current value to a modified final value:

```
Current trajectory:     2025: 100  →  2050: 200
With multiplier 1.2:    2025: 100  →  2050: 240
```

#### Constant

Maintains constant value from the uncertainty start year:

```
Original:               2025: 100  →  2030: 100  →  2050: 100
With initial year 2030: 2025: 100  →  2030: 100  →  2050: 100
```

#### Linear

Linear interpolation to final value:

```
Original:     2025: 100  →  2050: 200
Modified:     2025: 100  →  2050: 240  (linear path)
```

#### Logistic

S-curve (sigmoid) trajectory for technology adoption:

```
Slow adoption at start, accelerating in middle, saturating at end
```

#### Timeslices_Curve

Switches between predefined demand curves:

```
Selects a different curve from shape_of_demand.xlsx based on uncertainty sampling
```

```{important}
For `Timeslices_Curve` type:
- Curves must be predefined in the file `shape_of_demand.xlsx`
- The parameter `Explored_Parameter_of_X` must be set to `Change_Curve`
- This allows exploring different demand profile shapes across futures
```

### Example: Fuel Cost Uncertainty

```yaml
X_Num: 1
X_Category: "Fuel Costs"
X_Plain_English_Description: "Natural gas price uncertainty"
X_Mathematical_Type: "Time_Series"
Explored_Parameter_of_X: "Final_Value"
Min_Value: 0.7
Max_Value: 1.5
Involved_Scenarios: "Scenario1"
Involved_First_Sets_in_Osemosys: "NATGAS"
Exact_Parameters_Involved_in_Osemosys: "VariableCost"
Initial_Year_of_Uncertainty: 2025
```

### Example: Technology Capacity Uncertainty

```yaml
X_Num: 2
X_Category: "Technology Limits"
X_Plain_English_Description: "Solar PV maximum capacity"
X_Mathematical_Type: "Time_Series"
Explored_Parameter_of_X: "Final_Value"
Min_Value: 0.5
Max_Value: 2.0
Involved_Scenarios: "Scenario1"
Involved_First_Sets_in_Osemosys: "PWRSOL001 ; PWRSOL002"
Exact_Parameters_Involved_in_Osemosys: "TotalAnnualMaxCapacity"
Initial_Year_of_Uncertainty: 2025
```

## Running the RDM Pipeline

### Quick Start

```bash
python run.py rdm
```

### Monitoring Progress

The pipeline provides progress updates:

```
======================================================================
🔬 RDM Pipeline (Robust Decision Making)
======================================================================
Stages: base_future → rdm_experiment → postprocess
======================================================================

🔄 Executing RDM Pipeline...
----------------------------------------------------------------------
Step 1 finished
Step 2 finished
...
# This is future: 1 and scenario Scenario1
# This is future: 2 and scenario Scenario1
...
----------------------------------------------------------------------
✅ RDM Pipeline completed in 15m 32s!
```

## Parallel Execution

RDM experiments are parallelized for efficiency.

### Configuration

```
# In Interface_RDM.xlsx, Setup sheet:
Parallel_Use: 10  # Futures processed simultaneously
```

### Resource Considerations

| Parallel_Use | RAM Needed | Speed |
|-------------|------------|-------|
| 1 | ~4 GB | Slowest |
| 5 | ~8 GB | Moderate |
| 10 | ~16 GB | Fast |
| 20 | ~32 GB | Fastest |

```{warning}
Set `Parallel_Use` based on your system's available memory. 
Too high a value can cause out-of-memory errors.
```

## Output Structure

### Per-Future Outputs

Each future generates:
```
Experimental_Platform/Futures/Scenario1/Scenario1_1/
├── Scenario1_1.txt          # Modified scenario file
├── Scenario1_1_Input.parquet   # Input parameters
├── Scenario1_1_Output.parquet  # Solution outputs
└── Scenario1_1_Output.sol   # Raw solver output
```

### Aggregated Outputs

After pipeline completion:
```
src/Results/
├── OSEMOSYS_{Region}_Energy_Input.csv    (from rdm_experiment stage)
│   └── Columns: Strategy, Future.ID, YEAR, Parameter, Value, ...
├── OSEMOSYS_{Region}_Energy_Output.csv   (from postprocess stage)
│   └── Columns: Strategy, Future.ID, YEAR, TECHNOLOGY, Value, ...
└── *.parquet (efficient intermediate storage)
```

## Best Practices

### 1. Start Small

```
# Begin with 10-20 futures to test configuration
Number_of_Runs: 20
```

### 2. Validate Base Future

Before running many futures:
- Check base future results manually
- Verify model solves correctly
- Confirm outputs make sense

### 3. Use Appropriate Ranges

```
# Too narrow: misses important outcomes
Min_Value: 0.99, Max_Value: 1.01  # ❌

# Too wide: includes implausible futures
Min_Value: 0.1, Max_Value: 10.0   # ❌

# Reasonable range
Min_Value: 0.7, Max_Value: 1.3    # ✅
```

### 4. Group Related Uncertainties

Use `X_Category` to organize:
- Fuel Costs
- Technology Costs
- Demand Growth
- Policy Constraints

### 5. Document Your Choices

Keep notes on:
- Why specific ranges were chosen
- Data sources for uncertainty bounds
- Assumptions made
