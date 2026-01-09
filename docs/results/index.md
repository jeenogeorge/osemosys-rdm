# Results & Examples

This guide shows you how to run OSeMOSYS-RDM step-by-step using Anaconda. This is a beginner-friendly guide that assumes no prior experience with command-line interfaces.

## Step-by-Step Execution Guide

### Step 1: Open Anaconda Prompt

First, open the Anaconda Prompt terminal. This is a special command-line interface that comes with Anaconda.

![Open Anaconda Prompt](../_static/images/1_open_anacondaprompt.png)

*Opening the Anaconda Prompt terminal*

```{tip}
You can find Anaconda Prompt in your Windows Start menu by searching for "Anaconda Prompt".
```

### Step 2: Navigate to Repository

Change to the repository directory using the `cd` command (which stands for "change directory").

**Command explanation:**
- `cd` followed by a path tells the terminal to move to that location on your computer
- Replace the path in the image with your actual repository location

Type the command and **press Enter** to execute it.

![Navigate to Repository](../_static/images/2_repository_path.png)

*Accessing the repository directory path*

```{important}
Make sure to replace the path with the actual location where you cloned or downloaded the repository on your computer.
```

### Step 3: Run the Model

Execute the model using the appropriate command. Type the command and **press Enter** to start the execution.

**Command explanation:**
```bash
python run.py rdm
```

- `python` tells the computer to use Python to run a program
- `run.py` is the main program file that controls the workflow
- `rdm` tells the program to run the RDM (Robust Decision Making) pipeline

**Other available options:**
- `python run.py prim` - Runs only the PRIM analysis (requires RDM results already available)
- `python run.py all` - Runs both RDM and PRIM pipelines sequentially

![Run Model](../_static/images/3_run_model.png)

*Command to execute the process*

### Step 4: Process Starts

After pressing Enter, the process will begin executing the pipeline stages. You'll see text appearing on the screen showing the progress.

![Process Start](../_static/images/4_start_procces.png)

*Beginning of the execution process*

```{note}
Don't close the window while the process is running. The terminal will show you updates as each stage completes.
```

### Step 5: Process Completes

The process will finish when all stages are complete. You'll see a final message indicating success.

![Process Finish](../_static/images/5_finish_procces.png)

*End of the execution process*

```{note}
In this example, the process completes very quickly because the last model executed is cached in memory. DVC (Data Version Control) detects that re-running would produce the same results, so it skips unnecessary computations. Your first run may take longer.
```

## Understanding the Output

After the process completes successfully, your results will be available in the `src/Results/` directory. You can find:

- CSV files with consolidated outputs
- Parquet files for efficient data storage
- Analysis-ready datasets for visualization

## Contributing Results

If you have interesting results to share:

1. Ensure data is anonymized if needed
2. Provide context and interpretation
3. Include reproduction steps if possible
4. Submit a pull request to the documentation repository

### How to Add Results

To add your own results to this documentation:

1. Save images to `docs/_static/images/`
2. Reference them in markdown:
   ```markdown
   ![Description](../_static/images/your-image.png)
   ```
3. Add interpretation and context

#### File Formats Supported

| Format | Use Case |
|--------|----------|
| PNG | Screenshots, diagrams |
| SVG | Scalable charts |
| PDF | Embedded documents |
| GIF | Animated demonstrations |
