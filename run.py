# run.py
# -*- coding: utf-8 -*-
"""
DVC Pipeline Runner for AFR_RDM with Conda environment management.

Features:
- Creates/verifies Conda environment from environment.yaml
- Checks and installs missing dependencies automatically
- Initializes DVC repository if needed
- Executes 'dvc pull' if remote storage is configured
- Runs 'dvc repro' to execute the full pipeline
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
DVC_FILE_DEFAULT = "dvc.yaml"

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

def ensure_deps(env_name: str) -> None:
    """
    Verify and install missing dependencies in the environment.
    - Conda packages from conda-forge
    - Pip packages for DVC and pyDOE
    """
    print("\n🔍 Checking dependencies...")

    # Check if pip will be needed
    need_pip = any(not module_present(env_name, m) for m in list(PIP_DEPS.keys()))
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
    missing_pip = [pkg for mod, pkg in PIP_DEPS.items() if not module_present(env_name, mod)]
    if missing_pip:
        for spec in missing_pip:
            print(f"📦 Installing missing pip package: {spec}")
            run(f"conda run -n {env_name} python -m pip install -U {spec}")
        print("✓ Pip packages installed.")
    else:
        print("✓ All pip packages are present.")

# ---------- DVC Management ----------
def is_dvc_repo() -> bool:
    """Check if current directory is a DVC repository."""
    return Path(".dvc").is_dir()

def ensure_dvc_repo(env_name: str) -> None:
    """Initialize DVC repository if not already initialized."""
    if is_dvc_repo():
        print("✓ DVC repository detected (.dvc/ directory found).")
        return
    print("📦 Initializing DVC repository...")
    run(f"conda run -n {env_name} dvc init")
    if not is_dvc_repo():
        raise RuntimeError("Failed to initialize DVC repository (.dvc/ not created).")
    print("✓ DVC repository initialized.")

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

# ---------- Main Function ----------
def main():
    parser = argparse.ArgumentParser(
        description="DVC pipeline runner for AFR_RDM with Conda environment management"
    )
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

    print("=" * 70)
    print("AFR_RDM DVC Pipeline Runner")
    print("=" * 70)
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
        ensure_deps(env_name)

        # 3) Initialize DVC repository
        print("\n🔧 Step 3: DVC Initialization")
        ensure_dvc_repo(env_name)

        # 4) Pull from remote if configured
        if not args.skip_pull and has_dvc_remote(env_name):
            print("\n📥 Step 4: Pulling data from DVC remote...")
            dvc_command(env_name, "pull")
            print("✓ Data pulled successfully.")
        else:
            if args.skip_pull:
                print("\nℹ️  Skipping 'dvc pull' (--skip-pull flag set)")
            else:
                print("\nℹ️  No DVC remote configured. Skipping 'dvc pull'.")

        # 5) Execute DVC pipeline
        print("\n🔄 Step 5: Executing DVC Pipeline")
        print("=" * 70)
        start_time = dt.datetime.now()

        repro_args = "repro --force" if args.force else "repro"
        dvc_command(env_name, repro_args)

        end_time = dt.datetime.now()

        # Calculate and display duration
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

        print("=" * 70)
        print(f"✅ Pipeline completed successfully in {' '.join(duration_parts)}!")
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
