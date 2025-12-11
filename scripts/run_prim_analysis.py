# -*- coding: utf-8 -*-
"""
PRIM Analysis Wrapper for DVC Pipeline

This script executes the PRIM analysis stages:
1. t3f1_prim_structure.py - Define PRIM structure
2. t3f3_prim_manager.py - Execute PRIM analysis
3. t3f4_range_finder_mapping.py - Map predominant parameter ranges

Usage:
    python scripts/run_prim_analysis.py

Dependencies:
    - src/workflow/4_PRIM/t3b_sdiscovery/experiment_data/ (from prim_files_creator)
    - src/workflow/4_PRIM/t3b_sdiscovery/Analysis_1/prim_structure.xlsx

Author: AFR_RDM Team
"""

import os
import sys
import json
import time
from pathlib import Path

def generate_metrics(sdiscovery_dir, metrics_file):
    """
    Generate metrics JSON file for DVC tracking.
    """
    metrics = {
        "stage": "prim_analysis",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sd_csv_files": 0,
        "predominant_ranges_files": 0,
        "pickle_files": 0
    }

    if sdiscovery_dir.exists():
        # Count scenario discovery CSV files
        sd_files = list(sdiscovery_dir.glob("sd_ana_*.csv"))
        metrics["sd_csv_files"] = len(sd_files)

        # Count predominant ranges Excel files
        range_files = list(sdiscovery_dir.glob("t3f4_predominant_ranges_*.xlsx"))
        metrics["predominant_ranges_files"] = len(range_files)

        # Count pickle files
        pickle_files = list(sdiscovery_dir.glob("**/*.pickle"))
        metrics["pickle_files"] = len(pickle_files)

    # Write metrics
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"Metrics written to {metrics_file}")
    print(f"  - Scenario discovery CSVs: {metrics['sd_csv_files']}")
    print(f"  - Predominant ranges files: {metrics['predominant_ranges_files']}")
    print(f"  - Pickle files: {metrics['pickle_files']}")

def run_script(script_path, working_dir):
    """Execute a Python script in the specified working directory."""
    import subprocess

    print(f"\nExecuting {script_path.name}...")
    print("-" * 50)
    sys.stdout.flush()  # Ensure output is displayed before subprocess

    original_dir = os.getcwd()
    os.chdir(working_dir)

    try:
        # Use -u flag for unbuffered Python output
        result = subprocess.run(
            [sys.executable, "-u", str(script_path)],
            check=True
        )
        print(f"{script_path.name} completed.")
    finally:
        os.chdir(original_dir)

def main():
    """Main execution function"""
    print("=" * 70)
    print("AFR_RDM - PRIM Analysis")
    print("=" * 70)

    # Paths
    project_root = Path(__file__).parent.parent
    prim_dir = project_root / 'src' / 'workflow' / '4_PRIM'
    sdiscovery_dir = prim_dir / 't3b_sdiscovery'
    metrics_file = prim_dir / 'prim_analysis_metrics.json'

    # Scripts to execute (in order)
    # Note: t3f1 and t3f2 are executed in prim_files_creator stage
    # This stage executes t3f3 and t3f4
    scripts = [
        (sdiscovery_dir / 't3f3_prim_manager.py', sdiscovery_dir),
        (sdiscovery_dir / 't3f4_range_finder_mapping.py', sdiscovery_dir),
    ]

    # Verify experiment_data exists
    experiment_data = sdiscovery_dir / 'experiment_data'
    if not experiment_data.exists():
        print(f"Error: {experiment_data} not found")
        print("Please run 'python run.py prim' with prim_files_creator stage first.")
        sys.exit(1)

    start_time = time.time()

    try:
        print(f"PRIM Scenario Discovery directory: {sdiscovery_dir}")
        print()
        print("Stages (continuation from prim_files_creator):")
        print("  3. t3f3_prim_manager.py - Execute PRIM analysis")
        print("  4. t3f4_range_finder_mapping.py - Map predominant ranges")
        print()

        # Execute each script in sequence
        for script_path, working_dir in scripts:
            if not script_path.exists():
                print(f"Warning: {script_path} not found, skipping...")
                continue
            run_script(script_path, working_dir)

        print("-" * 70)

        # Generate metrics
        elapsed_time = time.time() - start_time
        print(f"\nTotal execution time: {elapsed_time:.2f} seconds")

        generate_metrics(sdiscovery_dir, metrics_file)

        print("\nPRIM Analysis completed successfully!")

    except Exception as e:
        print(f"\nError during PRIM analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
