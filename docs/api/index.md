# API Reference

This section provides API documentation for OSeMOSYS-RDM's Python modules.

```{note}
This API reference is auto-generated from docstrings. 
For more detailed usage, see the [User Guide](../user-guide/workflow-overview.md).
```

## Core Modules

### z_auxiliar_code

The main utility module containing core functions.

```{eval-rst}
.. py:module:: src.workflow.z_auxiliar_code

.. py:function:: obtain_structure_file(scenario_file, output_file, structure_file, num_timeslices)

   Extract model structure from a scenario file.
   
   :param scenario_file: Path to the OSeMOSYS scenario file
   :param output_file: Path for the output Excel file
   :param structure_file: Path to the OSeMOSYS structure reference
   :param num_timeslices: Number of time slices in the model
   :return: Dictionary of sets
   
.. py:function:: isolate_params(scenario_file)

   Parse a scenario file and isolate parameters.
   
   :param scenario_file: Path to the scenario file
   :return: Tuple of (data_per_param dict, special_sets list)
   
.. py:function:: generate_df_per_param(scenario_name, data_per_param, num_timeslices)

   Generate DataFrames for each parameter.
   
   :param scenario_name: Name of the scenario
   :param data_per_param: Dictionary of parameter data
   :param num_timeslices: Number of time slices
   :return: Tuple of (list_dataframes, dict_dataframes, parameters_without_values)

.. py:function:: run_osemosys(solver, output_dir, data_file, model_file, output_base)

   Execute OSeMOSYS optimization.
   
   :param solver: Solver name ('glpk', 'cbc', 'cplex', 'gurobi')
   :param output_dir: Directory for output files
   :param data_file: Path to data file
   :param model_file: Path to model formulation
   :param output_base: Base name for output files

.. py:function:: data_processor_new(sol_file, structure_file, scenario, future, solver, params_to_print, output_format)

   Process solver output into standardized format.
   
   :param sol_file: Path to solution file
   :param structure_file: Path to model structure file
   :param scenario: Scenario name
   :param future: Future ID
   :param solver: Solver used
   :param params_to_print: DataFrame of parameters to export
   :param output_format: 'csv' or 'parquet'
```

### Interpolation Functions

```{eval-rst}
.. py:function:: interpolation_non_linear_final(time_list, value_list, multiplier, last_year, initial_year)

   Non-linear interpolation to a modified final value.
   
   :param time_list: List of years
   :param value_list: List of base values
   :param multiplier: Final value multiplier
   :param last_year: Last year of analysis
   :param initial_year: Year uncertainty begins
   :return: List of new values

.. py:function:: interpolation_constant_trajectory(time_list, value_list, initial_year)

   Maintain constant trajectory from initial year.
   
   :param time_list: List of years
   :param value_list: List of base values
   :param initial_year: Year to freeze values
   :return: List of constant values

.. py:function:: interpolation_linear(time_list, value_list, multiplier, last_year, initial_year)

   Linear interpolation to modified final value.
   
   :param time_list: List of years
   :param value_list: List of base values
   :param multiplier: Final value multiplier
   :param last_year: Last year of analysis
   :param initial_year: Year uncertainty begins
   :return: List of linearly interpolated values

.. py:function:: interpolation_logistic_trajectory(time_list, value_list, multiplier, last_year, initial_year)

   Logistic (S-curve) trajectory interpolation.
   
   :param time_list: List of years
   :param value_list: List of base values
   :param multiplier: Final value multiplier
   :param last_year: Last year of analysis
   :param initial_year: Year uncertainty begins
   :return: List of values following logistic curve
```

## Pipeline Scripts

### run.py

Main pipeline orchestrator.

```{eval-rst}
.. py:module:: run

.. py:function:: main()

   Main entry point for the OSeMOSYS-RDM pipeline.
   
   Command line arguments:
   
   - ``module``: 'rdm', 'prim', or 'all'
   - ``--force``: Force re-execution
   - ``--skip-pull``: Skip DVC pull
   - ``--env-name``: Custom environment name
   - ``--env-file``: Path to environment.yaml

.. py:function:: run_rdm_pipeline(env_name, force, skip_pull)

   Execute the RDM pipeline stages.
   
   :param env_name: Conda environment name
   :param force: Force re-execution of all stages
   :param skip_pull: Skip DVC pull operation

.. py:function:: run_prim_pipeline(env_name, force, skip_pull)

   Execute the PRIM analysis pipeline.
   
   :param env_name: Conda environment name
   :param force: Force re-execution of all stages
   :param skip_pull: Skip DVC pull operation
```

### DVC Wrapper Scripts

```{eval-rst}
.. py:module:: scripts.run_base_future

.. py:function:: main()

   Execute base future scenario (Future 0).
   
   Temporarily modifies Interface_RDM.xlsx to run only the base case,
   then restores the original configuration.

.. py:module:: scripts.run_rdm_experiment

.. py:function:: main()

   Execute RDM experiment with multiple futures.
   
   Configures for RDM-only execution and runs the experiment manager.

.. py:module:: scripts.run_postprocess

.. py:function:: main()

   Aggregate and concatenate results from all futures.
   
   Calls the output dataset creator to consolidate parquet files.

.. py:module:: scripts.run_prim_files_creator

.. py:function:: main()

   Create PRIM input files from RDM results.
   
   Executes t3f1_prim_structure.py and t3f2_prim_files_creator.py.

.. py:module:: scripts.run_prim_analysis

.. py:function:: main()

   Execute PRIM scenario discovery analysis.
   
   Runs t3f3_prim_manager.py and t3f4_range_finder_mapping.py.
```

## PRIM Module

### t3f2_prim_files_creator

```{eval-rst}
.. py:module:: src.workflow.4_PRIM.t3f2_prim_files_creator

.. py:function:: f1_create_prim_files(dir_elements, dirl, scen, dict_pfcp, analysis_list, dict_set_matching, period_control, all_exp_data, exp_id, params, dicPop)

   Create PRIM-ready files from experiment data.
   
   :param dir_elements: List of files in directory
   :param dirl: Directory path
   :param scen: Scenario name
   :param dict_pfcp: PRIM files creator parallel config
   :param analysis_list: List of analysis IDs
   :param dict_set_matching: Set matching dictionary
   :param period_control: Period configuration
   :param all_exp_data: All experiment data
   :param exp_id: Experiment ID
   :param params: YAML parameters
   :param dicPop: Population dictionary

.. py:function:: f2_exe_postproc(prim_tbl, prim_tbl_bau, period_list, yr_ini_list, yr_fin_list, list_acc_files, list_dfs, actor, name, set_type, source, col_name, col_sets, den_frml, mcod, num_frml, last_indicate, prms, set_argmnt, sup_sets, vmng, exp_data, future, scen, whole_period, df_sm, tbl_id, o_or_d, ana_ID, exp_id, params, dicPop)

   Execute post-processing for PRIM table creation.
   
   :param prim_tbl: PRIM table dictionary
   :param prim_tbl_bau: BAU reference table
   :param period_list: List of periods
   :param ...: Additional parameters
   :return: Updated PRIM table
```

## Data Structures

### Experiment Dictionary

```python
experiment_dictionary = {
    1: {  # X_Num
        'Category': str,           # Uncertainty category
        'Math_Type': str,          # Mathematical type
        'Exact_X': str,            # Description
        'Involved_Scenarios': list,
        'Involved_First_Sets_in_Osemosys': list,
        'Involved_Second_Sets_in_Osemosys': list,
        'Involved_Third_Sets_in_Osemosys': list,
        'Exact_Parameters_Involved_in_Osemosys': list,
        'Initial_Year_of_Uncertainty': int,
        'Explored_Parameter_of_X': str,
        'Futures': list,           # [1, 2, 3, ..., N]
        'Values': list,            # Sampled values per future
    },
    # ...
}
```

### Inherited Scenarios

```python
inherited_scenarios = {
    'Scenario1': {
        1: {  # Future ID
            'CapitalCost': {
                'r': [],      # Region
                't': [],      # Technology
                'y': [],      # Year
                'value': [],  # Values
            },
            # ... other parameters
        },
        # ... other futures
    },
    # ... other scenarios
}
```

### PRIM Files Dictionary

```python
pfd = {
    'o': {  # Outcomes
        1: {  # Table ID
            'period_name': {
                'column_name': {
                    'vl': [],    # Values list
                    'snl': [],   # Store num lists
                },
                'Fut_ID': [],
                'Scenario': [],
            },
        },
    },
    'd': {  # Drivers
        # Same structure as outcomes
    },
}
```
