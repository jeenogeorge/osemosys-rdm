# -*- coding: utf-8 -*-
"""
PRIM Files Creator Wrapper for DVC Pipeline

This script executes the first stage of PRIM analysis: creating the input files
for PRIM from the RDM experiment results.

Usage:
    python scripts/run_prim_files_creator.py

Dependencies:
    - src/Results/ must contain the RDM output CSVs
    - src/workflow/4_PRIM/Population.xlsx
    - src/workflow/4_PRIM/prim_files_creator_cntrl.xlsx
    - src/workflow/4_PRIM/PRIM_t3f2.yaml

Author: AFR_RDM Team
"""

import os
import sys
import json
import time
from pathlib import Path

def generate_metrics(output_dir, metrics_file):
    """
    Generate metrics JSON file for DVC tracking.
    """
    metrics = {
        "stage": "prim_files_creator",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "output_files": 0,
        "experiment_data_files": 0
    }

    # Count output files
    if output_dir.exists():
        experiment_data = output_dir / "experiment_data"
        if experiment_data.exists():
            metrics["experiment_data_files"] = len(list(experiment_data.glob("*")))

        pickle_files = list(output_dir.glob("**/*.pickle"))
        metrics["output_files"] = len(pickle_files)

    # Write metrics
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"Metrics written to {metrics_file}")
    print(f"  - Experiment data files: {metrics['experiment_data_files']}")
    print(f"  - Pickle files: {metrics['output_files']}")

def main():
    """Main execution function"""
    print("=" * 70)
    print("AFR_RDM - PRIM Files Creator")
    print("=" * 70)

    # Paths
    project_root = Path(__file__).parent.parent
    prim_dir = project_root / 'src' / 'workflow' / '4_PRIM'
    prim_script = prim_dir / 't3f2_prim_files_creator.py'
    sdiscovery_dir = prim_dir / 't3b_sdiscovery'
    metrics_file = prim_dir / 'prim_files_creator_metrics.json'
    results_dir = project_root / 'src' / 'Results'

    # Verify prerequisites
    if not prim_script.exists():
        print(f"Error: {prim_script} not found")
        sys.exit(1)

    if not results_dir.exists() or len(list(results_dir.glob("*.csv"))) < 2:
        print(f"Error: RDM results not found in {results_dir}")
        print("Please run 'python run.py rdm' first.")
        sys.exit(1)

    start_time = time.time()

    try:
        print(f"PRIM directory: {prim_dir}")
        print(f"Script: {prim_script.name}")
        print()

        # Ensure experiment_data directory structure exists
        # This directory is used by t3f2_prim_files_creator.py to store/read pickle files
        experiment_data_dir = sdiscovery_dir / 'experiment_data' / '1_Experiment'
        experiment_data_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Verified experiment_data directory: {experiment_data_dir}")

        import subprocess

        # Step 1: Execute t3f1_prim_structure.py first (defines PRIM structure)
        prim_structure_script = sdiscovery_dir / 't3f1_prim_structure.py'
        if prim_structure_script.exists():
            print("\nStep 1: Executing t3f1_prim_structure.py...")
            print("-" * 70)
            sys.stdout.flush()

            original_dir = os.getcwd()
            os.chdir(sdiscovery_dir)
            subprocess.run(
                [sys.executable, "-u", str(prim_structure_script)],
                check=True
            )
            os.chdir(original_dir)
            print("-" * 70)
            print("✓ t3f1_prim_structure.py completed.")
        else:
            print(f"Warning: {prim_structure_script} not found, skipping...")

        # Step 2: Execute t3f2_prim_files_creator.py (creates PRIM input files)
        print("\nStep 2: Executing t3f2_prim_files_creator.py...")
        print("-" * 70)
        sys.stdout.flush()

        # Change to PRIM directory (script expects to be run from there)
        original_dir = os.getcwd()
        os.chdir(prim_dir)

        # Execute the PRIM files creator script
        # Use -u flag for unbuffered Python output
        result = subprocess.run(
            [sys.executable, "-u", str(prim_script)],
            check=True
        )
        os.chdir(original_dir)

        print("-" * 70)
        print("✓ t3f2_prim_files_creator.py completed.")

        # Change back to original directory
        os.chdir(original_dir)

        # Generate metrics
        elapsed_time = time.time() - start_time
        print(f"\nExecution time: {elapsed_time:.2f} seconds")

        generate_metrics(sdiscovery_dir, metrics_file)

        print("\nPRIM Files Creator completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"\nError during PRIM files creation: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
