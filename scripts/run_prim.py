# -*- coding: utf-8 -*-
"""
PRIM Analysis Wrapper for DVC Pipeline

This script executes the PRIM (Patient Rule Induction Method) scenario discovery
analysis on the aggregated RDM results.

Usage:
    python scripts/run_prim.py

Manual execution:
    This script can be run independently to perform PRIM analysis.

DVC integration:
    Called automatically by DVC when executing the 'prim_analysis' stage.

Author: AFR_RDM Team
"""

import os
import sys
import json
import time
from pathlib import Path

def generate_metrics(prim_output_dir, metrics_file):
    """
    Generate metrics JSON file for DVC tracking.
    Tracks PRIM analysis outputs and statistics.
    """
    metrics = {
        "stage": "prim_analysis",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "output_files": 0,
        "excel_files": 0,
        "plot_files": 0,
        "total_size_mb": 0.0
    }

    # Count and categorize output files
    if prim_output_dir.exists():
        all_files = list(prim_output_dir.glob('*'))

        for file in all_files:
            if file.is_file():
                metrics["output_files"] += 1
                size_mb = file.stat().st_size / (1024 * 1024)
                metrics["total_size_mb"] += size_mb

                # Categorize by extension
                if file.suffix.lower() in ['.xlsx', '.xls']:
                    metrics["excel_files"] += 1
                elif file.suffix.lower() in ['.png', '.jpg', '.pdf']:
                    metrics["plot_files"] += 1

    # Round total size
    metrics["total_size_mb"] = round(metrics["total_size_mb"], 2)

    # Write metrics
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"✓ Metrics written to {metrics_file}")
    print(f"  - Total output files: {metrics['output_files']}")
    print(f"  - Excel files: {metrics['excel_files']}")
    print(f"  - Plot files: {metrics['plot_files']}")
    print(f"  - Total size: {metrics['total_size_mb']} MB")

def main():
    """Main execution function"""
    print("=" * 70)
    print("AFR_RDM - PRIM Scenario Discovery Analysis")
    print("=" * 70)

    # Paths
    project_root = Path(__file__).parent.parent
    prim_dir = project_root / 'src' / 'workflow' / '4_PRIM'
    prim_script = prim_dir / 'PRIM_new.py'
    prim_output_dir = prim_dir / 'Output'
    metrics_file = prim_output_dir / 'prim_plots.json'

    # Verify PRIM script exists
    if not prim_script.exists():
        print(f"❌ Error: {prim_script} not found")
        sys.exit(1)

    # Verify PRIM config exists
    prim_config = prim_dir / 'PRIM_config.xlsx'
    if not prim_config.exists():
        print(f"⚠️  Warning: {prim_config} not found")
        print("   PRIM analysis may fail without configuration file")

    start_time = time.time()

    try:
        print(f"📂 PRIM directory: {prim_dir}")
        print(f"📄 Script: {prim_script.name}")
        print(f"📊 Config: {prim_config.name if prim_config.exists() else 'Not found'}")
        print()

        # Change to PRIM directory
        original_dir = os.getcwd()
        os.chdir(prim_dir)

        print("🚀 Executing PRIM_new.py...")
        print("-" * 70)

        # Execute the PRIM script
        # This preserves the original script logic
        with open(prim_script, 'r', encoding='utf-8') as f:
            script_code = f.read()

        exec(compile(script_code, str(prim_script), 'exec'))

        print("-" * 70)

        # Change back to original directory
        os.chdir(original_dir)

        # Generate metrics
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Execution time: {elapsed_time:.2f} seconds")

        generate_metrics(prim_output_dir, metrics_file)

        print("\n✅ PRIM analysis completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during PRIM analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
