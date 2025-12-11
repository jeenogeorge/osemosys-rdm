# run.py
# -*- coding: utf-8 -*-
"""
DVC Pipeline Runner for AFR_RDM with Conda environment management.

Usage:
    python run.py rdm          # Execute RDM pipeline (base_future → rdm_experiment → postprocess)
    python run.py prim         # Execute PRIM analysis (requires Results/ from RDM)
    python run.py all          # Execute both RDM and PRIM sequentially

Features:
- Creates/verifies Conda environment from environment.yaml
- Checks and installs missing dependencies automatically
- Initializes DVC/Git repository if needed
- Executes 'dvc pull' if remote storage is configured
- Runs 'dvc repro' to execute the selected pipeline
- Tracks execution time and provides detailed progress feedback

Author: AFR_RDM Team
"""

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path
import json

# ---------- Default Configuration ----------
ENV_NAME_DEFAULT = "AFR-RDM-env"
ENV_FILE_DEFAULT = "environment.yaml"
DVC_FILE = "dvc.yaml"

# Stage names for selective execution
RDM_FINAL_STAGE = "postprocess"      # Last stage of RDM pipeline
PRIM_FINAL_STAGE = "prim_analysis"   # Last stage of PRIM pipeline

# Dependencies to verify/install
CONDA_DEPS = {
    # python_module: conda_package
    "pandas": "pandas",
    "numpy": "numpy",
    "openpyxl": "openpyxl",
    "yaml": "pyyaml",          # PyYAML imports as 'yaml'
    "xlsxwriter": "xlsxwriter",
    "pyarrow": "pyarrow",
    "scipy": "scipy",
    "sklearn": "scikit-learn"
}

PIP_DEPS = {
    # python_module: pip_package
    "dvc": "dvc>=3.0.0",
    "pyDOE": "pyDOE>=0.3.8",
}

# Additional dependencies for PRIM module
PRIM_DEPS = {
    # python_module: pip_package
    "prim": "prim",
}

# ---------- Shell Utilities ----------
def run(cmd: str) -> None:
    """Execute shell command with deterministic Python hash seed."""
    env = os.environ.copy()
    env['PYTHONHASHSEED'] = '0'
    subprocess.check_call(cmd, shell=True, env=env)

def check_tool_available(tool: str) -> None:
    """Verify that a required tool is available in PATH."""
    try:
        subprocess.check_call(f"{tool} --version", shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        raise RuntimeError(
            f"Required tool '{tool}' not found in PATH. "
            f"Please open an Anaconda/Miniconda Prompt or install the tool. "
            f"Original error: {exc}"
        )

# ---------- Conda Environment Management ----------
def env_exists(name: str) -> bool:
    """
    Check if a Conda environment exists.
    Returns True if an environment with the given name exists.
    Uses 'conda env list --json' with text fallback.
    """
    target = name.lower()

    # 1) Primary method: JSON output
    try:
        out = subprocess.check_output(
            ["conda", "env", "list", "--json"],
            text=True,
            stderr=subprocess.STDOUT
        )
        data = json.loads(out)
        envs = data.get("envs", []) or []
        return any(Path(p).name.lower() == target for p in envs)
    except Exception:
        pass

    # 2) Fallback: Parse text output from 'conda env list'
    try:
        txt = subprocess.check_output(
            ["conda", "env", "list"],
            text=True,
            stderr=subprocess.STDOUT
        )
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "conda environments:")):
                continue
            parts = line.split()
            if not parts:
                continue
            # Check if first column matches the target name
            cand = parts[0].lower()
            if cand == target:
                return True
        return False
    except Exception:
        return False

def guess_env_name_from_yaml(env_file: str) -> str | None:
    """Extract environment name from environment.yaml file."""
    p = Path(env_file)
    if not p.exists():
        return None
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.lower().startswith("name:"):
                val = line.split(":", 1)[1].strip().strip("'\"")
                return val or None
    except Exception:
        pass
    return None

def create_env_if_missing(env_name: str, env_file: str) -> None:
    """Create Conda environment from YAML file if it doesn't exist."""
    if env_exists(env_name):
        print(f"✓ Conda environment '{env_name}' already exists.")
        return
    print(f"📦 Creating Conda environment '{env_name}' from {env_file}...")
    run(f"conda env create -n {env_name} -f {env_file} -y")
    print(f"✓ Environment '{env_name}' created successfully.")

def ensure_pip_available(env_name: str) -> None:
    """Ensure pip is installed in the Conda environment."""
    try:
        run(f"conda run -n {env_name} python -m pip --version")
    except subprocess.CalledProcessError:
        print("⚠️  pip not found in environment. Installing pip...")
        run(f"conda install -n {env_name} pip -y")
        print("✓ pip installed.")

def module_present(env_name: str, module: str) -> bool:
    """Check if a Python module is available in the environment."""
    code = (
        "import importlib,sys;"
        f"sys.exit(0) if importlib.util.find_spec('{module}') else sys.exit(1)"
    )
    try:
        run(f'conda run -n {env_name} python -c "{code}"')
        return True
    except subprocess.CalledProcessError:
        return False

def ensure_deps(env_name: str, include_prim: bool = False) -> None:
    """
    Verify and install missing dependencies in the environment.
    - Conda packages from conda-forge
    - Pip packages for DVC and pyDOE
    - PRIM package if include_prim=True
    """
    print("\n🔍 Checking dependencies...")

    # Merge pip deps with PRIM deps if needed
    pip_deps = PIP_DEPS.copy()
    if include_prim:
        pip_deps.update(PRIM_DEPS)

    # Check if pip will be needed
    need_pip = any(not module_present(env_name, m) for m in list(pip_deps.keys()))
    if need_pip:
        ensure_pip_available(env_name)

    # Install missing Conda packages
    missing_conda = [pkg for mod, pkg in CONDA_DEPS.items() if not module_present(env_name, mod)]
    if missing_conda:
        pkgs = " ".join(missing_conda)
        print(f"📦 Installing missing conda packages: {', '.join(missing_conda)}")
        run(f"conda install -n {env_name} -c conda-forge -y {pkgs}")
        print("✓ Conda packages installed.")
    else:
        print("✓ All conda packages are present.")

    # Install missing pip packages
    missing_pip = [pkg for mod, pkg in pip_deps.items() if not module_present(env_name, mod)]
    if missing_pip:
        for spec in missing_pip:
            print(f"📦 Installing missing pip package: {spec}")
            # Quote the spec to prevent shell interpretation of >= as redirect
            run(f'conda run -n {env_name} python -m pip install -U "{spec}"')
        print("✓ Pip packages installed.")
    else:
        print("✓ All pip packages are present.")

# ---------- Git Management ----------
def is_git_repo() -> bool:
    """Check if current directory is a Git repository."""
    return Path(".git").is_dir()

def is_git_available() -> bool:
    """Check if Git is installed and available in PATH."""
    try:
        subprocess.check_call(
            "git --version",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def ensure_git_repo() -> bool:
    """
    Ensure Git repository exists. Returns True if Git is available/initialized.

    - If .git/ exists: return True
    - If Git is available but no .git/: initialize and return True
    - If Git is not available: return False (will use DVC --no-scm)
    """
    if is_git_repo():
        print("✓ Git repository detected.")
        return True

    if not is_git_available():
        print("ℹ️  Git not installed. DVC will run without version control (--no-scm).")
        print("   Note: For full functionality, install Git from https://git-scm.com/")
        return False

    # Git is available but no .git/ directory - initialize it
    print("📦 Initializing Git repository (required for full DVC functionality)...")
    try:
        run("git init")
        run("git add .")
        run('git commit -m "Initial commit (auto-generated by run.py)"')
        print("✓ Git repository initialized.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not initialize Git repository: {e}")
        print("   DVC will run without version control (--no-scm).")
        return False

# ---------- DVC Management ----------
def is_dvc_repo() -> bool:
    """Check if current directory is a DVC repository."""
    return Path(".dvc").is_dir()

def ensure_dvc_repo(env_name: str, use_scm: bool = True) -> None:
    """
    Initialize DVC repository if not already initialized.

    Args:
        env_name: Conda environment name
        use_scm: If True, use Git integration. If False, use --no-scm flag.
    """
    if is_dvc_repo():
        print("✓ DVC repository detected (.dvc/ directory found).")
        return

    print("📦 Initializing DVC repository...")

    if use_scm:
        run(f"conda run -n {env_name} dvc init")
    else:
        run(f"conda run -n {env_name} dvc init --no-scm")

    if not is_dvc_repo():
        raise RuntimeError("Failed to initialize DVC repository (.dvc/ not created).")

    if use_scm:
        print("✓ DVC repository initialized (with Git integration).")
    else:
        print("✓ DVC repository initialized (without Git - standalone mode).")

def has_dvc_remote(env_name: str) -> bool:
    """Check if DVC has any remote storage configured."""
    try:
        out = subprocess.check_output(f"conda run -n {env_name} dvc remote list",
                                      shell=True, stderr=subprocess.STDOUT)
        return bool(out.decode("utf-8", errors="ignore").strip())
    except subprocess.CalledProcessError:
        return False

def dvc_command(env_name: str, args: str) -> None:
    """Execute a DVC command in the Conda environment."""
    run(f"conda run -n {env_name} dvc {args}")

# ---------- Pipeline Verification ----------
def verify_rdm_results() -> bool:
    """Check if RDM results exist (required for PRIM)."""
    results_dir = Path("src/Results")
    if not results_dir.exists():
        return False
    csv_files = list(results_dir.glob("*.csv"))
    return len(csv_files) >= 2  # At least Input and Output CSVs

# ---------- Duration Formatting ----------
def format_duration(start_time: dt.datetime, end_time: dt.datetime) -> str:
    """Format duration between two timestamps."""
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    duration_parts = []
    if hours > 0:
        duration_parts.append(f"{hours}h")
    if minutes > 0 or hours > 0:
        duration_parts.append(f"{minutes}m")
    duration_parts.append(f"{seconds}s")

    return " ".join(duration_parts)

# ---------- Pipeline Execution Functions ----------
def run_rdm_pipeline(env_name: str, force: bool, skip_pull: bool) -> None:
    """Execute the RDM pipeline (base_future → rdm_experiment → postprocess)."""
    print("\n" + "=" * 70)
    print("🔬 RDM Pipeline (Robust Decision Making)")
    print("=" * 70)
    print("Stages: base_future → rdm_experiment → postprocess")
    print("=" * 70)

    # Pull from remote if configured
    if not skip_pull and has_dvc_remote(env_name):
        print("\n📥 Pulling data from DVC remote...")
        dvc_command(env_name, "pull")
        print("✓ Data pulled successfully.")
    else:
        if skip_pull:
            print("\nℹ️  Skipping 'dvc pull' (--skip-pull flag set)")
        else:
            print("\nℹ️  No DVC remote configured. Skipping 'dvc pull'.")

    # Execute RDM pipeline by running the final stage (DVC handles dependencies)
    print("\n🔄 Executing RDM Pipeline...")
    print("-" * 70)
    start_time = dt.datetime.now()

    repro_args = f"repro {RDM_FINAL_STAGE}"
    if force:
        repro_args += " --force"
    dvc_command(env_name, repro_args)

    end_time = dt.datetime.now()
    duration = format_duration(start_time, end_time)

    print("-" * 70)
    print(f"✅ RDM Pipeline completed in {duration}!")

def run_prim_pipeline(env_name: str, force: bool, skip_pull: bool) -> None:
    """Execute the PRIM analysis pipeline."""
    print("\n" + "=" * 70)
    print("📊 PRIM Pipeline (Patient Rule Induction Method)")
    print("=" * 70)
    print("Stages: prim_files_creator → prim_analysis")
    print("=" * 70)

    # Verify RDM results exist
    if not verify_rdm_results():
        print("\n❌ Error: RDM results not found in src/Results/")
        print("   PRIM requires the output from RDM pipeline.")
        print("   Please run 'python run.py rdm' first.")
        sys.exit(1)

    print("\n✓ RDM results found in src/Results/")

    # Pull from remote if configured
    if not skip_pull and has_dvc_remote(env_name):
        print("\n📥 Pulling data from DVC remote...")
        dvc_command(env_name, "pull")
        print("✓ Data pulled successfully.")

    # Execute PRIM pipeline by running the final stage (DVC handles dependencies)
    print("\n🔄 Executing PRIM Pipeline...")
    print("-" * 70)
    start_time = dt.datetime.now()

    repro_args = f"repro {PRIM_FINAL_STAGE}"
    if force:
        repro_args += " --force"
    dvc_command(env_name, repro_args)

    end_time = dt.datetime.now()
    duration = format_duration(start_time, end_time)

    print("-" * 70)
    print(f"✅ PRIM Pipeline completed in {duration}!")

# ---------- Main Function ----------
def main():
    parser = argparse.ArgumentParser(
        description="AFR_RDM Pipeline Runner - Execute RDM and PRIM analysis pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py rdm          Execute RDM pipeline only
  python run.py prim         Execute PRIM analysis only (requires RDM results)
  python run.py all          Execute both RDM and PRIM sequentially
  python run.py rdm --force  Force re-execution of all RDM stages
        """
    )

    # Positional argument for module selection
    parser.add_argument(
        "module",
        choices=["rdm", "prim", "all"],
        help="Module to execute: 'rdm' (RDM pipeline), 'prim' (PRIM analysis), 'all' (both)"
    )

    # Optional arguments
    parser.add_argument(
        "--env-name",
        default=None,
        help="Conda environment name (if not provided, reads from environment.yaml)"
    )
    parser.add_argument(
        "--env-file",
        default=ENV_FILE_DEFAULT,
        help=f"Path to environment.yaml (default: {ENV_FILE_DEFAULT})"
    )
    parser.add_argument(
        "--skip-pull",
        action="store_true",
        help="Skip 'dvc pull' even if remote is configured"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reproduction of all stages"
    )

    args = parser.parse_args()

    # Determine environment name
    env_name = args.env_name or guess_env_name_from_yaml(args.env_file) or ENV_NAME_DEFAULT
    env_file = args.env_file

    # Determine if PRIM dependencies are needed
    include_prim = args.module in ["prim", "all"]

    # Header
    print("=" * 70)
    print("AFR_RDM Pipeline Runner")
    print("=" * 70)
    print(f"Module: {args.module.upper()}")
    print(f"Environment: {env_name}")
    print(f"Environment file: {env_file}")
    print("=" * 70)

    # Check prerequisites
    check_tool_available("conda")

    try:
        # 1) Create/verify Conda environment
        print("\n🔧 Step 1: Environment Setup")
        create_env_if_missing(env_name, env_file)

        # 2) Verify/install dependencies
        print("\n🔧 Step 2: Dependency Management")
        ensure_deps(env_name, include_prim=include_prim)

        # 3) Check/Initialize Git repository
        print("\n🔧 Step 3: Git Repository Check")
        has_git = ensure_git_repo()

        # 4) Initialize DVC repository
        print("\n🔧 Step 4: DVC Initialization")
        ensure_dvc_repo(env_name, use_scm=has_git)

        # 5) Execute selected pipeline(s)
        overall_start = dt.datetime.now()

        if args.module == "rdm":
            run_rdm_pipeline(env_name, args.force, args.skip_pull)

        elif args.module == "prim":
            run_prim_pipeline(env_name, args.force, args.skip_pull)

        elif args.module == "all":
            run_rdm_pipeline(env_name, args.force, args.skip_pull)
            run_prim_pipeline(env_name, args.force, args.skip_pull)

        overall_end = dt.datetime.now()
        overall_duration = format_duration(overall_start, overall_end)

        print("\n" + "=" * 70)
        print(f"✅ All pipelines completed successfully in {overall_duration}!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline execution interrupted by user.")
        sys.exit(130)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Command failed (exit code {e.returncode}): {e.cmd}", file=sys.stderr)
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
