# -*- coding: utf-8 -*-
"""
Reads the .sol file of each future and extracts the solution status.
Outputs a summary .txt file in the Results/ folder.

Supports CPLEX (.xml), CBC, Gurobi, and GLPK solver output formats.

@author: Andrey Salazar-Vargas
"""

import os
import re
import glob


def get_sol_status(sol_path):
    """Extract solution status from a .sol file."""
    with open(sol_path, 'r') as f:
        # Read first 15 lines (status is always near the top)
        lines = [f.readline() for _ in range(15)]

    content = ''.join(lines)

    # CPLEX XML format: solutionStatusString="optimal" or "infeasible"
    match = re.search(r'solutionStatusString="([^"]+)"', content)
    if match:
        return match.group(1)

    # Gurobi format: "# Solution for model ..." on line 1,
    # "# Objective value = ..." on line 2 (optimal), or "# Infeasible model"
    if '# Objective value' in content:
        return 'optimal'
    if '# infeasible' in content.lower():
        return 'infeasible'

    # CBC format: status is on the first line (e.g., "Optimal - objective value ...")
    first_lower = lines[0].strip().lower()
    if 'optimal' in first_lower:
        return 'optimal'
    if 'infeasible' in first_lower:
        return 'infeasible'

    return 'unknown'


def find_sol_file(directory):
    """Find the .sol file in a directory."""
    sol_files = glob.glob(os.path.join(directory, '*.sol'))
    return sol_files[0] if sol_files else None


def _delete_solver_files(sol_path):
    """Delete the .sol file and its companion .lp file if they exist."""
    if os.path.exists(sol_path):
        os.remove(sol_path)
    lp_path = sol_path.rsplit('.', 1)[0] + '.lp'
    if os.path.exists(lp_path):
        os.remove(lp_path)


def main():
    # Resolve paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

    base_dir = os.path.join(script_dir, '1_Experiment', 'Executables')
    futures_dir = os.path.join(script_dir, '1_Experiment', 'Experimental_Platform', 'Futures')
    results_dir = os.path.join(repo_root, 'Results')

    os.makedirs(results_dir, exist_ok=True)
    output_path = os.path.join(results_dir, 'solution_status.txt')

    results = []
    sol_files_to_delete = []

    # 1) Base future (Scenario*_0) in Executables/
    if os.path.isdir(base_dir):
        for folder in sorted(os.listdir(base_dir)):
            folder_path = os.path.join(base_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            sol_file = find_sol_file(folder_path)
            if sol_file:
                status = get_sol_status(sol_file)
                results.append((folder, status))
                sol_files_to_delete.append(sol_file)

    # 2) RDM futures in Experimental_Platform/Futures/
    if os.path.isdir(futures_dir):
        for scenario in sorted(os.listdir(futures_dir)):
            scenario_path = os.path.join(futures_dir, scenario)
            if not os.path.isdir(scenario_path):
                continue
            # Sort numerically by the future number
            future_dirs = sorted(
                [d for d in os.listdir(scenario_path) if os.path.isdir(os.path.join(scenario_path, d))],
                key=lambda x: int(x.split('_')[-1])
            )
            for future in future_dirs:
                future_path = os.path.join(scenario_path, future)
                sol_file = find_sol_file(future_path)
                if sol_file:
                    status = get_sol_status(sol_file)
                    results.append((future, status))
                    sol_files_to_delete.append(sol_file)

    # Write output
    with open(output_path, 'w') as f:
        f.write('Solution Status Summary\n')
        f.write('=' * 40 + '\n\n')

        optimal_count = sum(1 for _, s in results if s == 'optimal')
        infeasible_count = sum(1 for _, s in results if s == 'infeasible')
        other_count = len(results) - optimal_count - infeasible_count

        f.write(f'Total futures: {len(results)}\n')
        f.write(f'Optimal:      {optimal_count}\n')
        f.write(f'Infeasible:   {infeasible_count}\n')
        if other_count:
            f.write(f'Other:        {other_count}\n')
        f.write('\n' + '-' * 40 + '\n\n')

        for name, status in results:
            f.write(f'{name}: {status}\n')

    # Delete .sol and .lp files after reading all statuses
    for sol_path in sol_files_to_delete:
        _delete_solver_files(sol_path)

    print(f'Results written to: {output_path}')
    print(f'{len(results)} futures processed: {optimal_count} optimal, {infeasible_count} infeasible')


if __name__ == '__main__':
    main()
