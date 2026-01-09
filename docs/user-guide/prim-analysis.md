# PRIM Analysis

The PRIM (Patient Rule Induction Method) module enables **scenario discovery** by identifying which combinations of uncertain input parameters are associated with outcomes of interest.

## What is PRIM?

PRIM is a bump-hunting algorithm that:

1. Takes a high-dimensional dataset of inputs and outputs
2. Finds regions ("boxes") where outcomes of interest occur
3. Describes these regions using simple rules on input parameters
4. Helps identify which uncertainties matter most

## Why Use PRIM?

After running an RDM experiment with hundreds of futures, you need to understand:

- **Which parameters drive risk?** What conditions lead to undesirable outcomes?
- **Which parameters enable success?** What conditions lead to desirable outcomes?
- **Where are the tipping points?** At what parameter values do outcomes change?

## Running PRIM Analysis

### Configuration Guide

For detailed instructions on configuring the PRIM module, refer to:

```
src/Guides/Guide PRIM Module Configuration.html
```

This comprehensive guide explains how to properly configure all PRIM Excel files for your analysis.

### Quick Start

```bash
# Requires RDM results in src/Results/
python run.py prim
```

### Prerequisites

Before running PRIM:

1. ✅ RDM pipeline completed successfully
2. ✅ Results available in `src/Results/`
3. ✅ PRIM configuration files set up (see configuration guide above)

### What Happens

```{mermaid}
flowchart LR
    A[RDM Results] --> B[t3f1_prim_structure.py<br/>Define Structure]
    B --> C[t3f2_prim_files_creator.py<br/>Create PRIM Files]
    C --> D[t3f3_prim_manager.py<br/>Execute PRIM]
    D --> E[t3f4_range_finder_mapping.py<br/>Map Ranges]
    E --> F[Predominant Ranges<br/>Excel Files]
```

## Configuration Files

PRIM analysis is configured through files in `src/workflow/4_PRIM/`:

### 1. prim_structure.xlsx

Defines the analysis structure:

**Outcomes Sheet:**
| Column | Description |
|--------|-------------|
| ID | Unique outcome identifier |
| Name | Human-readable name |
| Source | Data source (OSeMOSYS outputs) |
| Set_Type | Technology, Fuel, Emission, etc. |
| Processing | Calculation method |

**Drivers Sheet:**
| Column | Description |
|--------|-------------|
| ID | Unique driver identifier |
| Name | Human-readable name |
| Source | Data source (OSeMOSYS inputs) |
| Processing | How to aggregate values |

### 2. PRIM_t3f2.yaml

Main PRIM configuration:

```yaml
# Base scenario name
BAU: 'Scenario1'

# Model names
ose_inputs: 'OSeMOSYS-UGA inputs'
ose_oupts: 'OSeMOSYS-UGA outputs'

# Directory structure
dir_exps: '1_Experiment'
dir_sdisc: 't3b_sdiscovery'

# Processing parameters
max_per_batch: 10
```

### 3. prim_files_creator_cntrl.xlsx

Controls execution and analysis periods:

**match_exp_ana Sheet:**
| exps | analyses | include_exp | include_ana |
|------|----------|-------------|-------------|
| 1 | 1 | YES | YES |

**periods Sheet:**
| period_list | year_initial | year_final |
|-------------|--------------|------------|
| all | 2020 | 2050 |
| near | 2020 | 2030 |
| mid | 2031 | 2040 |
| far | 2041 | 2050 |

### 4. Units.xlsx

Defines units for drivers and outcomes:

| Variable | Unit |
|----------|------|
| TotalDiscountedCost | MUSD |
| ProductionByTechnology | PJ |
| AnnualEmissions | GgCO2e |

## Defining Outcomes

Outcomes are the metrics you want to analyze. Common examples:

### Cost Outcomes

```yaml
Name: Total System Cost
Source: OSeMOSYS outputs
Parameter: TotalDiscountedCost
Processing: cumulative
Set_Type: REGION
```

### Emission Outcomes

```yaml
Name: Total CO2 Emissions
Source: OSeMOSYS outputs
Parameter: AnnualEmissions
Processing: cumulative
Set_Type: EMISSION
Supporting_Sets: CO2
```

### Technology Outcomes

```yaml
Name: Renewable Energy Share
Source: OSeMOSYS outputs
Parameter: ProductionByTechnology
Processing: share_renewable_gen
Set_Type: TECHNOLOGY
```

## Defining Drivers

Drivers are the uncertain input parameters:

### Input Parameter Driver

```yaml
Name: Natural Gas Price
Source: OSeMOSYS inputs
Parameter: VariableCost
Set_Type: TECHNOLOGY
Sets: NATGAS_IMPORT
```

### Derived Driver

```yaml
Name: Capital Cost Multiplier
Source: experiment_data
Parameter: experiment_dictionary
Processing: direct
```

## Outcome Classification

PRIM requires classifying outcomes as "of interest" or not. Common presets:

| Preset | Description | Use Case |
|--------|-------------|----------|
| **High** | Above 75th percentile | Identify high-cost scenarios |
| **Low** | Below 25th percentile | Identify low-emission scenarios |
| **Mid** | Above 50th percentile | Above-average outcomes |
| **Zero** | Below zero | Worse than baseline |

### Custom Thresholds

You can define custom thresholds in the analysis configuration:

```python
# Example: scenarios with cost > 20% above baseline
threshold = baseline_cost * 1.2
cases_of_interest = outcomes > threshold
```

## Understanding Results

### Predominant Ranges

The main output is `t3f4_predominant_ranges_*.xlsx`:

| Driver | Low_Bound | High_Bound | Coverage | Density |
|--------|-----------|------------|----------|---------|
| Gas_Price | 1.1 | 1.5 | 0.85 | 0.72 |
| Solar_Cost | 0.5 | 0.8 | 0.78 | 0.68 |

**Interpretation:**
- **Coverage**: Fraction of "interesting" cases captured by this box
- **Density**: Fraction of cases in the box that are "interesting"

### Reading PRIM Boxes

A PRIM "box" describes a region in parameter space:

```
BOX 1:
  Gas_Price: [1.1, 1.5]
  Solar_Cost: [0.5, 0.8]
  
  Coverage: 85%  → This box contains 85% of high-cost scenarios
  Density: 72%   → 72% of scenarios in this box are high-cost
```

### Trade-off Curve

PRIM produces a coverage-density trade-off:

```
Coverage ↑
         |     *
         |   *
         |  *
         | *
         |*
         +--------→ Density
```

- Move right: Higher density (more precise rules)
- Move up: Higher coverage (captures more cases)

## Best Practices

### 1. Start with Clear Questions

Before running PRIM, define:
- What outcomes matter? (costs, emissions, reliability)
- What constitutes success/failure?
- What decisions are you trying to inform?

### 2. Validate Results

After PRIM analysis:
- Check that identified boxes make physical sense
- Verify with domain knowledge
- Test sensitivity to threshold choices

### 3. Iterate on Analysis

PRIM is often iterative:
1. Run initial analysis
2. Review results with stakeholders
3. Refine outcome definitions
4. Re-run with adjusted parameters

### 4. Document Findings

For each PRIM analysis, document:
- Outcome definitions and thresholds
- Key driver ranges identified
- Policy implications
- Limitations and assumptions

## Example Workflow

### 1. Define the Question

"Under what conditions do total costs exceed the budget by more than 20%?"

### 2. Configure Outcome

```yaml
Name: Budget Exceedance
Processing: cumulative
Threshold: baseline_cost * 1.2
```

### 3. Run PRIM

```bash
python run.py prim
```

### 4. Analyze Results

Review `t3f4_predominant_ranges_*.xlsx`:

```
Scenarios with costs > 20% above baseline occur when:
- Natural gas prices are 30-50% above baseline (1.3-1.5)
- Solar costs remain high (>90% of baseline)
- Demand growth exceeds 10% above baseline
```

### 5. Policy Implications

Based on findings:
- Hedge against gas price volatility
- Accelerate solar cost reductions
- Implement demand-side efficiency measures

## Output Files

### sd_ana_*_exp_*_Experiment.csv

Raw PRIM analysis data:
```
Future.ID, Outcome_1, Outcome_2, Driver_1, Driver_2, ...
1, 150.2, 45.3, 1.2, 0.85, ...
2, 148.7, 44.1, 1.1, 0.92, ...
```

### t3f4_predominant_ranges_*.xlsx

Summarized discoveries:
- Parameter ranges for each outcome
- Coverage and density metrics
- Box definitions

### *.pickle Files

Intermediate data for debugging:
- `pfd_*.pickle`: PRIM-formatted data
- `comp_pfd_*.pickle`: Compiled results
