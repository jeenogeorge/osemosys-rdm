# -*- coding: utf-8 -*-
"""
Postprocessing Wrapper for DVC Pipeline

This script executes the postprocessing stage that aggregates and concatenates
results from all RDM futures into final CSV files.

Usage:
    python scripts/run_postprocess.py

Manual execution:
    This script can be run independently to regenerate aggregated results.

DVC integration:
    Called automatically by DVC when executing the 'postprocess' stage.

Author: AFR_RDM Team
"""

import os
import sys
import json
import time
from pathlib import Path

def generate_metrics(results_dir, metrics_file):
    """
    Generate metrics JSON file for DVC tracking.
    Tracks number of output CSV files and their sizes.
    """
    metrics = {
        "stage": "postprocess",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "output_files": 0,
        "total_size_mb": 0.0,
        "files_list": []
    }

    # Count and measure output files
    if results_dir.exists():
        csv_files = list(results_dir.glob('*.csv'))
        metrics["output_files"] = len(csv_files)

        for csv_file in csv_files:
            size_mb = csv_file.stat().st_size / (1024 * 1024)
            metrics["total_size_mb"] += size_mb
            metrics["files_list"].append({
                "filename": csv_file.name,
                "size_mb": round(size_mb, 2)
            })

    # Round total size
    metrics["total_size_mb"] = round(metrics["total_size_mb"], 2)

    # Write metrics
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"✓ Metrics written to {metrics_file}")
    print(f"  - Output CSV files: {metrics['output_files']}")
    print(f"  - Total size: {metrics['total_size_mb']} MB")

def main():
    """Main execution function"""
    print("=" * 70)
    print("AFR_RDM - Postprocessing (Results Aggregation)")
    print("=" * 70)

    # Paths
    project_root = Path(__file__).parent.parent
    postprocess_dir = project_root / 'src' / 'workflow' / '3_Postprocessing'
    postprocess_script = postprocess_dir / 'create_csv_concatenate.py'
    results_dir = project_root / 'src' / 'Results'
    metrics_file = results_dir / 'postprocess_metrics.json'

    # Verify postprocessing script exists
    if not postprocess_script.exists():
        print(f"❌ Error: {postprocess_script} not found")
        sys.exit(1)

    start_time = time.time()

    try:
        print(f"📂 Postprocessing directory: {postprocess_dir}")
        print(f"📄 Script: {postprocess_script.name}")
        print()

        # Change to postprocessing directory
        original_dir = os.getcwd()
        os.chdir(postprocess_dir)

        print("🚀 Executing create_csv_concatenate.py...")
        print("-" * 70)

        # Execute the postprocessing script
        # This preserves the original script logic
        with open(postprocess_script, 'r', encoding='utf-8') as f:
            script_code = f.read()

        exec(compile(script_code, str(postprocess_script), 'exec'))

        print("-" * 70)

        # Change back to original directory
        os.chdir(original_dir)

        # Generate metrics
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Execution time: {elapsed_time:.2f} seconds")

        generate_metrics(results_dir, metrics_file)

        print("\n✅ Postprocessing completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during postprocessing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
