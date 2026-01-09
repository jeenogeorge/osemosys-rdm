# Results & Examples

This guide shows you how to run OSeMOSYS-RDM step-by-step using Anaconda.

## Step-by-Step Execution Guide

### Step 1: Open Anaconda Prompt

First, open the Anaconda Prompt terminal.

![Open Anaconda Prompt](../_static/images/1_open_anacondaprompt.png)

*Opening the Anaconda Prompt terminal*

### Step 2: Navigate to Repository

Change to the repository directory using the `cd` command.

![Navigate to Repository](../_static/images/2_repository_path.png)

*Accessing the repository directory path*

### Step 3: Run the Model

Execute the model using the appropriate command. This example shows the general RDM pipeline, but you can also use `prim` or `all` for different pipelines.

```bash
python run.py rdm
```

![Run Model](../_static/images/3_run_model.png)

*Command to execute the process*

### Step 4: Process Starts

The process will begin executing the pipeline stages.

![Process Start](../_static/images/4_start_procces.png)

*Beginning of the execution process*

### Step 5: Process Completes

The process will finish when all stages are complete.

![Process Finish](../_static/images/5_finish_procces.png)

*End of the execution process*

```{note}
In this example, the process completes very quickly because the last model executed is cached in memory. DVC detects that re-running would produce the same results, so it skips unnecessary computations.
```

## Coming Soon

### Example Case Studies

- **Uganda Energy System**: RDM analysis of the Uganda energy sector
- **Regional Integration**: Multi-country analysis example
- **Sector Coupling**: Energy-water-land nexus example

### Visualizations

- Cost distribution across futures
- Technology pathway comparisons
- Emission trajectories
- PRIM discovery visualizations

## How to Add Results

To add your own results to this documentation:

1. Save images to `docs/_static/images/`
2. Reference them in markdown:
   ```markdown
   ![Description](../_static/images/your-image.png)
   ```
3. Add interpretation and context

## File Formats Supported

| Format | Use Case |
|--------|----------|
| PNG | Screenshots, diagrams |
| SVG | Scalable charts |
| PDF | Embedded documents |
| GIF | Animated demonstrations |

## Contributing Results

If you have interesting results to share:

1. Ensure data is anonymized if needed
2. Provide context and interpretation
3. Include reproduction steps if possible
4. Submit a pull request to the documentation repository
