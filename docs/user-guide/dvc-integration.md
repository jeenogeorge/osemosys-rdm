# DVC Integration

OSeMOSYS-RDM uses [DVC (Data Version Control)](https://dvc.org/) for reproducible pipeline automation, dependency tracking, and data versioning.

## Why DVC?

DVC provides:

- **Automatic dependency tracking**: Re-runs only what changed
- **Caching**: Saves time by skipping unchanged stages
- **Reproducibility**: Ensures consistent results across machines
- **Data versioning**: Track large files without Git bloat
- **Remote storage**: Share data across teams

## Pipeline Structure

The pipeline is defined in `dvc.yaml`:

```yaml
stages:
  base_future:
    cmd: python scripts/run_base_future.py
    deps:
      - src/workflow/0_Scenarios/
      - src/Interface_RDM.xlsx
    outs:
      - src/workflow/1_Experiment/Executables/

  rdm_experiment:
    cmd: python scripts/run_rdm_experiment.py
    deps:
      - src/Interface_RDM.xlsx
      - src/workflow/1_Experiment/0_From_Confection/B1_Model_Structure.xlsx
    outs:
      - src/workflow/1_Experiment/Experimental_Platform/

  postprocess:
    cmd: python scripts/run_postprocess.py
    deps:
      - src/workflow/1_Experiment/Experimental_Platform/
      - src/workflow/1_Experiment/Executables/
    outs:
      - src/Results/

  prim_files_creator:
    cmd: python scripts/run_prim_files_creator.py
    deps:
      - src/Results/
    outs:
      - src/workflow/4_PRIM/t3b_sdiscovery/experiment_data/

  prim_analysis:
    cmd: python scripts/run_prim_analysis.py
    deps:
      - src/workflow/4_PRIM/t3b_sdiscovery/experiment_data/
    outs:
      - src/workflow/4_PRIM/t3b_sdiscovery/sd_ana_*.csv
      - src/workflow/4_PRIM/t3b_sdiscovery/t3f4_predominant_ranges_*.xlsx
```

## Visualizing the DAG

View the pipeline structure:

```bash
conda run -n AFR-RDM-env dvc dag
```

Output:
```
+-------------+
| base_future |
+-------------+
       *
       *
       *
+----------------+
| rdm_experiment |
+----------------+
       *
       *
       *
+-------------+
| postprocess |
+-------------+
       *
       *
       *
+--------------------+
| prim_files_creator |
+--------------------+
       *
       *
       *
+---------------+
| prim_analysis |
+---------------+
```

## Common DVC Commands

### Check Pipeline Status

```bash
conda run -n AFR-RDM-env dvc status
```

Shows which stages need to be re-run.

### Execute Pipeline

```bash
# Run entire pipeline
conda run -n AFR-RDM-env dvc repro

# Run specific stage (and dependencies)
conda run -n AFR-RDM-env dvc repro postprocess

# Force re-execution
conda run -n AFR-RDM-env dvc repro --force
```

### View Metrics

```bash
conda run -n AFR-RDM-env dvc metrics show
```

Displays metrics from `*_metrics.json` files.

### Push/Pull Data

```bash
# Push data to remote
conda run -n AFR-RDM-env dvc push

# Pull data from remote
conda run -n AFR-RDM-env dvc pull
```

## Configuring Remote Storage

### Local Directory

```bash
dvc remote add -d myremote /path/to/storage
```

### Google Drive

```bash
# Add remote
dvc remote add -d gdrive gdrive://folder_id

# Configure (may require auth)
dvc remote modify gdrive gdrive_acknowledge_abuse true
```

### Amazon S3

```bash
dvc remote add -d s3remote s3://mybucket/path

# Configure credentials
dvc remote modify s3remote access_key_id mykey
dvc remote modify s3remote secret_access_key mysecret
```

### Azure Blob Storage

```bash
dvc remote add -d azure azure://container/path

# Configure
dvc remote modify azure connection_string "your_connection_string"
```

### OneDrive / SharePoint

```bash
dvc remote add -d onedrive \
    https://yourtenant.sharepoint.com/sites/yoursite/_layouts/15/download.aspx?UniqueId=folder_id
```

## The dvc.lock File

`dvc.lock` records the exact state of each pipeline run:

```yaml
schema: '2.0'
stages:
  base_future:
    cmd: python scripts/run_base_future.py
    deps:
    - path: src/Interface_RDM.xlsx
      hash: md5
      md5: 0b1b34692ccd178946420e941782389f
      size: 30436
    outs:
    - path: src/workflow/1_Experiment/Executables/
      hash: md5
      md5: f3064203b41fc19bcde70c161515d026.dir
      size: 17887476
      nfiles: 3
```

**Important**: Commit `dvc.lock` to Git for full reproducibility.

## Ignoring Files

The `.dvcignore` file specifies what DVC should ignore:

```
# Temporary solver files
*.lp
*.log
*.sol

# Python cache
__pycache__/
*.py[cod]

# Virtual environments
venv/
env/

# Large dashboard files
*.twbx
```

## Workflow with Git + DVC

### Typical Development Cycle

```bash
# 1. Make changes to code or configuration
vim src/Interface_RDM.xlsx

# 2. Run pipeline
python run.py rdm

# 3. Check what changed
dvc status
git status

# 4. Commit to Git
git add dvc.yaml dvc.lock src/Interface_RDM.xlsx
git commit -m "Updated uncertainty ranges"

# 5. Push data to DVC remote
dvc push

# 6. Push code to Git
git push
```

### Reproducing on Another Machine

```bash
# 1. Clone repository
git clone https://github.com/yourrepo/osemosys-rdm.git
cd osemosys-rdm

# 2. Pull data from DVC remote
dvc pull

# 3. (Optional) Re-run pipeline to verify
python run.py rdm
```

## Running Without Git

OSeMOSYS-RDM can run on machines without Git installed:

```bash
# Download repository as ZIP and extract
# Navigate to directory

# DVC will initialize in standalone mode
python run.py rdm
```

DVC will create `.dvc/` with `--no-scm` flag automatically.

**Limitations without Git:**
- No code version history
- Cannot push to Git remotes
- Pipeline still works normally

## Metrics Tracking

Each stage generates metrics files:

| Stage | Metrics File |
|-------|-------------|
| base_future | `src/workflow/1_Experiment/base_future_metrics.json` |
| rdm_experiment | `src/workflow/1_Experiment/rdm_experiment_metrics.json` |
| postprocess | `src/workflow/3_Postprocessing/postprocess_metrics.json` |
| prim_files_creator | `src/workflow/4_PRIM/prim_files_creator_metrics.json` |
| prim_analysis | `src/workflow/4_PRIM/prim_analysis_metrics.json` |

Example metrics:

```json
{
  "stage": "rdm_experiment",
  "timestamp": "2025-01-08 10:30:00",
  "futures_generated": 100,
  "total_parquet_files": 200,
  "scenarios_processed": 1
}
```

## Troubleshooting

### "DVC not initialized"

```bash
conda run -n AFR-RDM-env dvc init
```

### "Remote not configured"

```bash
# Check current remotes
dvc remote list

# Add a remote
dvc remote add -d myremote /path/to/storage
```

### "Stage is cached but output is missing"

```bash
# Force reproduction
dvc repro --force stage_name

# Or checkout from cache
dvc checkout
```

### "Lock file is out of sync"

```bash
# Regenerate lock file
dvc repro
git add dvc.lock
git commit -m "Update dvc.lock"
```

## Best Practices

### 1. Commit dvc.lock

Always commit `dvc.lock` to track exact pipeline state.

### 2. Use Remotes for Large Files

Don't store GB-sized files in Git. Use DVC remotes.

### 3. Document Parameter Changes

Use descriptive commit messages:
```bash
git commit -m "RDM: Increased futures to 200, added fuel uncertainty"
```

### 4. Regular Pushes

Push to DVC remote after successful runs:
```bash
dvc push
git push
```

### 5. Clean Up Cache

Periodically clean old cached data:
```bash
dvc gc -w  # Remove unused cache (keep workspace)
```
