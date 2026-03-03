# -*- coding: utf-8 -*-
"""
@author: Luis Victor-Gallardo, Andrey Salazar-Vargas
"""



import multiprocessing as mp
import pandas as pd
import numpy as np
import os, os.path, sys, errno
import math, time
from copy import deepcopy
import random
import re, linecache, gc, csv, scipy, shutil
from pyDOE import * # SOURCE: https://pypi.org/project/lhsmdu/. https://pythonhosted.org/pyDOE/randomized.html#latin-hypercube
import pyarrow
import pickle

# Save a copy of the original sys.path
original_sys_path = sys.path.copy()

# Get the path of the "workflow" folder
workflow_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Get the path of the current script's directory (for local imports)
_script_dir = os.path.dirname(os.path.abspath(__file__))

# Temporarily add "workflow" to sys.path
sys.path.append(workflow_path)

try:
    # Import the module
    import z_auxiliar_code as AUX
finally:
    # Restore the original sys.path
    sys.path = original_sys_path

# Import local dataset creators from the same directory
sys.path.insert(0, _script_dir)
import local_dataset_creator_0
import local_dataset_creator_f

'''
We implement OSEMOSYS in a procedimental code
The main features are:
inherited_scenarios : implemented in procedimental code
function_C_mathprog_parallel : we will insert it all in a function to run in parallel
interpolation : implemented in a function for linear of non-linear time-series
'''

############################################################################################################################################################################################################
#
#  FIX: Post-perturbation sign correction for UDC EV penetration constraints
#
#  MATHEMATICAL CONTEXT:
#  ---------------------
#  The EV penetration UDCs encode a cap on electric vehicle share:
#
#      Cap_ELC / (Cap_CONV + Cap_ELC) <= p
#
#  Rearranged as a linear inequality for the solver:
#
#      -p * Cap_CONV + (1-p) * Cap_ELC <= 0       [UDCTag = 0, UDCConstant = 0]
#
#  Where p is the maximum allowed EV penetration fraction (e.g., 0.02 = 2%).
#
#  This means:
#    - Conventional technology coefficients (diesel/gasoline) MUST be negative (-p)
#    - Electric technology coefficients MUST be positive (1-p)
#
#  PROBLEM:
#  --------
#  LHS perturbations can add deltas to these coefficients that accumulate over
#  the model horizon. When the base coefficient is small (e.g., -0.02), the
#  delta can push it past zero, inverting the sign. With all positive coefficients
#  and RHS = 0, the only solution is zero capacity for all technologies in the
#  constraint, which contradicts existing demand and causes infeasibility.
#
#  Example (2TRAHTREVCAP in Scenario1_1):
#    Year 2045: coef_diesel = -0.0005 (barely negative, OK)
#    Year 2046: coef_diesel = +0.0005 (positive, BREAKS the constraint)
#    => Error: 'EBb4_EnergyBalanceEachYear4_ICR(RE1,TRAHTR,2046)': 0 >= 2.76937
#
#  FIX:
#  ----
#  After all perturbations are applied, scan UDC coefficients for the 7 EV
#  penetration constraints. If any coefficient has the wrong sign, clamp it
#  to a small epsilon preserving the mathematically required sign.
#
############################################################################################################################################################################################################


def fix_udc_ev_penetration_coefficients(inherited_scenarios, scenario_list, all_futures,
                                        ev_udcs, conventional_patterns, electric_pattern,
                                        log_dir=None):
    """
    Post-perturbation validation and correction of UDC EV penetration coefficients.

    Scans UDCMultiplierTotalCapacity, UDCMultiplierNewCapacity, and
    UDCMultiplierActivity for the EV penetration UDCs. If any conventional
    (diesel/gasoline) technology coefficient is non-negative, it is clamped to
    -EPSILON. If any electric technology coefficient is non-positive, it is
    clamped to +EPSILON.

    Parameters
    ----------
    inherited_scenarios : dict
        Nested dict: inherited_scenarios[scenario][future][parameter][key] = list
        where key in {'r', 't', 'u', 'y', 'value'}.
    scenario_list : list
        List of scenario names (e.g., ['Scenario1']).
    all_futures : list
        List of future indices (e.g., [1, 2, ..., N]).
    ev_udcs : list
        List of EV penetration UDC names (derived from B1_Model_Structure.xlsx,
        filtered by 'EVCAP' suffix).
    conventional_patterns : list
        Substring patterns that classify conventional technologies
        (e.g., ['DSL', 'DSH', 'GSL']). Read from Interface_RDM.xlsx Setup sheet.
    electric_pattern : str
        Substring pattern that classifies electric technologies
        (e.g., 'ELC'). Read from Interface_RDM.xlsx Setup sheet.
    log_dir : str or None
        If provided, correction logs are written per-future to this directory.

    Returns
    -------
    corrections_summary : dict
        Maps (scenario, future) to a list of correction tuples.
    """

    EV_UDCS = ev_udcs
    CONVENTIONAL_PATTERNS = conventional_patterns
    ELECTRIC_PATTERN = electric_pattern

    # -------------------------------------------------------------------------
    # Epsilon: the clamping value. Small enough to not materially change the
    # constraint economics, but large enough to avoid numerical noise.
    # With EPSILON = 0.001, the implied EV cap is ~0.1%, which is negligible
    # and preserves the directional intent of the original constraint.
    # -------------------------------------------------------------------------
    EPSILON = 0.001

    # -------------------------------------------------------------------------
    # UDC parameters that participate in the constraint
    # (all three appear in both UDC1 and UDC2 equations in the model)
    # -------------------------------------------------------------------------
    UDC_PARAMS = [
        'UDCMultiplierTotalCapacity',
        'UDCMultiplierNewCapacity',
        'UDCMultiplierActivity',
    ]

    corrections_summary = {}
    total_corrections = 0

    for scen in scenario_list:
        if scen not in inherited_scenarios:
            continue

        for fut in all_futures:
            if fut not in inherited_scenarios[scen]:
                continue

            corrections_key = (scen, fut)
            corrections_summary[corrections_key] = []

            for param_name in UDC_PARAMS:
                if param_name not in inherited_scenarios[scen][fut]:
                    continue

                data = inherited_scenarios[scen][fut][param_name]

                # Verify the expected data structure keys exist
                if 'u' not in data or 't' not in data or 'value' not in data:
                    continue

                n_entries = len(data['value'])
                udc_list = data['u']
                tech_list = data['t']
                year_list = data.get('y', ['?'] * n_entries)
                value_list = data['value']

                for i in range(n_entries):
                    udc_name = str(udc_list[i])

                    # Only check the 7 EV penetration UDCs
                    if udc_name not in EV_UDCS:
                        continue

                    tech_name = str(tech_list[i])
                    year = str(year_list[i])
                    value = float(value_list[i])

                    # Classify technology by substring pattern
                    is_conventional = any(pat in tech_name for pat in CONVENTIONAL_PATTERNS)
                    is_electric = ELECTRIC_PATTERN in tech_name

                    # ---------------------------------------------------------
                    # SIGN CHECK AND CORRECTION
                    # ---------------------------------------------------------
                    if is_conventional and value >= 0:
                        # Conventional coefficient MUST be negative.
                        # A non-negative value means the perturbation pushed
                        # it past zero, breaking the constraint logic.
                        old_value = value
                        data['value'][i] = -EPSILON
                        corrections_summary[corrections_key].append(
                            (udc_name, year, tech_name, param_name, old_value, -EPSILON)
                        )
                        total_corrections += 1

                    elif is_electric and value <= 0:
                        # Electric coefficient MUST be positive.
                        # A non-positive value would invert the constraint.
                        old_value = value
                        data['value'][i] = EPSILON
                        corrections_summary[corrections_key].append(
                            (udc_name, year, tech_name, param_name, old_value, EPSILON)
                        )
                        total_corrections += 1

    # -------------------------------------------------------------------------
    # Logging: write per-future correction logs
    # -------------------------------------------------------------------------
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        for (scen, fut), corr_list in corrections_summary.items():
            if corr_list:
                log_file = os.path.join(log_dir, f'{scen}_{fut}_udc_corrections.log')
                with open(log_file, 'w') as lf:
                    lf.write(f'UDC EV Penetration Sign Correction Log\n')
                    lf.write(f'Scenario: {scen}, Future: {fut}\n')
                    lf.write(f'Total corrections: {len(corr_list)}\n')
                    lf.write('-' * 90 + '\n')
                    lf.write(f'{"UDC":<20} {"Year":<6} {"Technology":<20} {"Parameter":<35} {"Old":>12} {"New":>12}\n')
                    lf.write('-' * 90 + '\n')
                    for udc, year, tech, param, old_val, new_val in corr_list:
                        lf.write(f'{udc:<20} {year:<6} {tech:<20} {param:<35} {old_val:>12.10f} {new_val:>12.10f}\n')

    # -------------------------------------------------------------------------
    # Console summary
    # -------------------------------------------------------------------------
    if total_corrections > 0:
        print(f'    UDC EV Sign Fix: Applied {total_corrections} correction(s) across all futures.')
        # Per-UDC summary
        udc_counts = {}
        for corr_list in corrections_summary.values():
            for udc, year, tech, param, old_val, new_val in corr_list:
                udc_counts[udc] = udc_counts.get(udc, 0) + 1
        for udc, count in sorted(udc_counts.items()):
            print(f'      {udc}: {count} correction(s)')
    else:
        print('    UDC EV Sign Fix: No corrections needed.')

    return corrections_summary


############################################################################################################################################################################################################
def set_first_list( Executed_Scenario ):
    #
    # Get the directory of the current script
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path to the Excel file, relative to the script's directory
    dir_futures = os.path.join(current_script_path, 'Experimental_Platform', 'Futures', Executed_Scenario)
    first_list_raw = os.listdir( dir_futures )
    #
    global first_list
    first_list = [e for e in first_list_raw if ( '.csv' not in e ) and ( 'Table' not in e ) and ( '.py' not in e ) and ( '__pycache__' not in e ) ]

############################################################################################################################################################################################################
def main_executer(n1, Executed_Scenario, time_vector, scenario_list,solver,osemosys_model,parameters_to_print):
    print('# ' + str(n1+1) + ' of ' + Executed_Scenario )
    set_first_list( Executed_Scenario )
    file_aboslute_address = os.path.abspath("0_experiment_manager.py")
    file_adress = os.path.dirname(os.path.abspath(__file__))
    #
    case_address = os.path.join(file_adress, 'Experimental_Platform', 'Futures', Executed_Scenario, first_list[n1] )
    #
    str_scen_fut = first_list[n1].split('_')
    str_scen, str_fut = str_scen_fut[0], str_scen_fut[-1]

    if str_scen in scenario_list:
        #
        this_case = [ e for e in os.listdir( case_address ) if '.txt' in e ]
        #
        str_start = "start /B start cmd.exe @cmd /k cd " + file_adress
        #
        data_file = case_address.replace('./','').replace('/','\\') + '\\' + str( this_case[0] )
        output_file = case_address.replace('./','').replace('/','\\') + '\\' + str( this_case[0] ).replace('.txt','') + '_Output'
        #
        model_file = os.path.join(file_adress.replace('1_Experiment',''), osemosys_model)
        
        if solver == 'glpk':
            str_solve = 'glpsol -m '+ str( model_file ) +' -d ' + str( data_file )  +  " -o " + str( output_file ) + '.txt'
        else:
            str_matrix = 'glpsol -m ' + str( model_file ) + ' -d ' + str( data_file ) + ' --wlp ' + str( output_file ) + '.lp --check'
            os.system( str_start and str_matrix )
            
            if solver == 'cbc':
                str_solve = 'cbc ' + str( output_file ) + '.lp solve -solu ' + str( output_file ) + '.sol'

            elif solver == 'cplex':
                if os.path.exists(output_file + '.sol'):
                    shutil.os.remove(output_file + '.sol')
                str_solve = 'cplex -c "read ' + str( output_file ) + '.lp" "set threads 2" "optimize" "write ' + str( output_file ) + '.sol"'

            elif solver == 'gurobi':
                if os.path.exists(output_file + '.sol'):
                    shutil.os.remove(output_file + '.sol')
                str_solve = 'gurobi_cl ResultFile=' + str( output_file ) + '.sol ' + str( output_file ) + '.lp'
        os.system( str_start and str_solve )
        time.sleep(1)
        #

        if solver == 'cbc' or solver == 'cplex' or solver == 'gurobi':
            AUX.data_processor_new(output_file + '.sol',
                                   './workflow/1_Experiment/0_From_Confection/B1_Model_Structure.xlsx',
                                   str_scen,
                                   str_fut,
                                   solver,
                                   parameters_to_print,
                                   'parquet')
        elif solver == 'glpk':
            AUX.data_processor_new(output_file + '.txt',
                                   './workflow/1_Experiment/0_From_Confection/B1_Model_Structure.xlsx',
                                   str_scen,
                                   str_fut,
                                   solver,
                                   parameters_to_print,
                                   'parquet')
        #
        # AUX.create_output_dataset_future_0(n1, str_scen, time_vector, first_list,'./workflow/1_Experiment/0_From_Confection/B1_Model_Structure.xlsx')
        #
        # AUX.create_output_dataset_future_00(0, time_vector, first_list,'./workflow/1_Experiment/0_From_Confection/B1_Model_Structure.xlsx')
    #
    else:
        print('!!! At execution, we skip: future ', str_fut, ' and scenario ', str_scen, ' !!!' )
        #
    #
def function_C_mathprog_parallel( fut_index, scen, inherited_scenarios, unpackaged_useful_elements, num_time_slices_SDP):
    #
    scenario_list =                     unpackaged_useful_elements[0]
    S_DICT_sets_structure =             unpackaged_useful_elements[1]
    S_DICT_params_structure =           unpackaged_useful_elements[2]
    list_param_default_value =          unpackaged_useful_elements[3]
    print_adress =                      unpackaged_useful_elements[4]
    all_futures =                       unpackaged_useful_elements[5]
    parameters_in_the_model =           unpackaged_useful_elements[7]
    parameters_without_values =         unpackaged_useful_elements[8]
    special_sets =                      unpackaged_useful_elements[9]
    #
    list_param_default_value_params = list( list_param_default_value['Parameter'] )
    list_param_default_value_value = list( list_param_default_value['Default_Value'] )
    #
    if fut_index < len( all_futures ):
        fut = all_futures[fut_index]
        # scen = 0
    if fut_index >= len( all_futures ) and fut_index < 2*len( all_futures ):
        fut = all_futures[fut_index - len( all_futures ) ]
        # scen = 1
    if fut_index >= 2*len( all_futures ) and fut_index < 3*len( all_futures ):
        fut = all_futures[fut_index - 2*len( all_futures ) ]
        # scen = 2
    if fut_index >= 3*len( all_futures ) and fut_index < 4*len( all_futures ):
        fut = all_futures[fut_index - 3*len( all_futures ) ]
        # scen = 3
    if fut_index >= 4*len( all_futures ) and fut_index < 5*len( all_futures ):
        fut = all_futures[fut_index - 4*len( all_futures ) ]
        # scen = 4
    if fut_index >= 5*len( all_futures ) and fut_index < 6*len( all_futures ):
        fut = all_futures[fut_index - 5*len( all_futures ) ]
        # scen = 5
    if fut_index >= 6*len( all_futures ):
        fut = all_futures[fut_index - 6*len( all_futures ) ]
        # scen = 6
    #
    # header = ['Scenario','Parameter','REGION','TECHNOLOGY','COMMODITY','EMISSION','MODE_OF_OPERATION','TIMESLICE','YEAR','SEASON','DAYTYPE','DAILYTIMEBRACKET','STORAGE','STORAGEINTRADAY','STORAGEINTRAYEAR','Value']
    header_indices = ['Scenario','Parameter','r','t','f','e','m','l','y','ls','ld','lh','s','sd','sy','value']
    #
    fut = all_futures[fut_index - scen*len( all_futures ) ]
    #
    print('# This is future:', fut, ' and scenario ', scenario_list[scen] )
    #
    try:
        # Get the directory of the current script
        current_script_path = os.path.dirname(os.path.abspath(__file__))
        # Construct the full path to the Excel file, relative to the script's directory
        scen_file_dir = os.path.join(current_script_path, print_adress, str( scenario_list[scen] ), str( scenario_list[scen] ) + '_' + str( fut ))
        os.makedirs( scen_file_dir, exist_ok=True )
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        pass
    #
    this_scenario_data = inherited_scenarios[ scenario_list[scen] ][ fut ]
    #
    g_path = os.path.join(current_script_path, print_adress, str( scenario_list[scen] ), str( scenario_list[scen] ) + '_' + str( fut ),str( scenario_list[scen] ) + '_' + str( fut ) + '.txt')
    # print(g_path)
    g= open( g_path ,"w+")
    g.write( '###############\n#    Sets     #\n###############\n#\n' )
    # g.write( 'set DAILYTIMEBRACKET :=  ;\n' )
    # g.write( 'set DAYTYPE :=  ;\n' )
    # g.write( 'set SEASON :=  ;\n' )
    # g.write( 'set STORAGE :=  ;\n' )
    #
    for n1 in range( len( S_DICT_sets_structure['set'] ) ):
        if S_DICT_sets_structure['number_of_elements'][n1] >= 0:
            g.write( 'set ' + S_DICT_sets_structure['set'][n1] + ' := ' )
            #
            for n2 in range( S_DICT_sets_structure['number_of_elements'][n1] ):
                if S_DICT_sets_structure['set'][n1] == 'YEAR' or S_DICT_sets_structure['set'][n1] == 'MODE_OF_OPERATION':
                    g.write( str( int( S_DICT_sets_structure['elements_list'][n1][n2] ) ) + ' ' )
                else:
                    g.write( str( S_DICT_sets_structure['elements_list'][n1][n2] ) + ' ' )
            g.write( ';\n' )
    #
    g.write( '\n' )
    g.write( '###############\n#    Parameters     #\n###############\n#\n' )
    #
    for p in range( len( list( this_scenario_data.keys() ) ) ):
        #
        this_param = list( this_scenario_data.keys() )[p]
        #
        default_value_list_params_index = list_param_default_value_params.index( this_param )
        default_value = float( list_param_default_value_value[ default_value_list_params_index ] )
        #
        this_param_index = S_DICT_params_structure['parameter'].index( this_param )
        this_param_keys = S_DICT_params_structure['index_list'][this_param_index]
        #
        if len( this_scenario_data[ this_param ]['value'] ) != 0:
            #
            if len(this_param_keys) != 2:
                g.write( 'param ' + this_param + ' default ' + str( default_value ) + ' :=\n' )
            else:
                g.write( 'param ' + this_param + ' default ' + str( default_value ) + ' :\n' )
            #
            #-----------------------------------------#
            if len(this_param_keys) == 1: #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
                second_last_set_element = this_scenario_data[ this_param ][ this_param_keys[0] ] # header_indices.index( this_param_keys[-2] ) ]
                second_last_set_element_unique = [] # list( set( second_last_set_element ) )
                for u in range( len( second_last_set_element ) ):
                    if second_last_set_element[u] not in second_last_set_element_unique:
                        second_last_set_element_unique.append( second_last_set_element[u] )

                #
                for s in range( len( second_last_set_element_unique ) ):
                    g.write( second_last_set_element_unique[s] + ' ' )
                    value_indices = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[0] ] ) if x == str( second_last_set_element_unique[s] ) ]
                    these_values = []
                    for val in range( len( value_indices ) ):
                        these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                    for val in range( len( these_values ) ):
                        g.write( str( these_values[val] ) + ' ' )
                    g.write('\n') #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
            #-----------------------------------------#
            elif len(this_param_keys) == 2: #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
                # get the last and second last parameters of the list:
                last_set_element = this_scenario_data[ this_param ][ this_param_keys[-1] ] # header_indices.index( this_param_keys[-1] ) ]
                last_set_element_unique = [] # list( set( last_set_element ) )
                for u in range( len( last_set_element ) ):
                    if last_set_element[u] not in last_set_element_unique:
                        last_set_element_unique.append( last_set_element[u] )
                #
                for y in range( len( last_set_element_unique ) ):
                    g.write( str( last_set_element_unique[y] ) + ' ')
                g.write(':=\n')
                #
                second_last_set_element = this_scenario_data[ this_param ][ this_param_keys[-2] ] # header_indices.index( this_param_keys[-2] ) ]
                second_last_set_element_unique = [] # list( set( second_last_set_element ) )
                for u in range( len( second_last_set_element ) ):
                    if second_last_set_element[u] not in second_last_set_element_unique:
                        second_last_set_element_unique.append( second_last_set_element[u] )
                if this_param_keys[-2] == 'l':
                    second_last_set_element_unique_temp = second_last_set_element_unique
                    second_last_set_element_unique = []
                    for sdp in range(num_time_slices_SDP):
                        second_last_set_element_unique.append(second_last_set_element_unique_temp[sdp])
                #
                for s in range( len( second_last_set_element_unique ) ):
                    g.write( second_last_set_element_unique[s] + ' ' )
                    value_indices = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[-2] ] ) if x == str( second_last_set_element_unique[s] ) ]
                    these_values = []
                    for val in range( len( value_indices ) ):
                        these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                    for val in range( len( these_values ) ):
                        g.write( str( these_values[val] ) + ' ' )
                    g.write('\n') #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
            #%%%
            elif len(this_param_keys) == 3:
                this_set_element_unique_all = []
                for pkey in range( len(this_param_keys)-2 ):
                    for i in range( 2, len(header_indices)-1 ):
                        if header_indices[i] == this_param_keys[pkey]:
                            this_set_element = this_scenario_data[ this_param ][ header_indices[i] ]
                    this_set_element_unique_all.append( list( set( this_set_element ) ) )
                #
                this_set_element_unique_1 = deepcopy( this_set_element_unique_all[0] )
                #
                for n1 in range( len( this_set_element_unique_1 ) ): #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
                    g.write( '[' + str( this_set_element_unique_1[n1] ) + ',*,*]:\n' )
                    # get the last and second last parameters of the list:
                    last_set_element = this_scenario_data[ this_param ][ this_param_keys[-1] ] # header_indices.index( this_param_keys[-1] ) ]
                    last_set_element_unique = [] # list( set( last_set_element ) )
                    for u in range( len( last_set_element ) ):
                        if last_set_element[u] not in last_set_element_unique:
                            last_set_element_unique.append( last_set_element[u] )
                    #
                    for y in range( len( last_set_element_unique ) ):
                        g.write( str( last_set_element_unique[y] ) + ' ')
                    g.write(':=\n')
                    #
                    second_last_set_element = this_scenario_data[ this_param ][ this_param_keys[-2] ] #header_indices.index( this_param_keys[-2] ) ]
                    second_last_set_element_unique = [] # list( set( second_last_set_element ) )
                    for u in range( len( second_last_set_element ) ):
                        if second_last_set_element[u] not in second_last_set_element_unique:
                            second_last_set_element_unique.append( second_last_set_element[u] )
                    #
                    for s in range( len( second_last_set_element_unique ) ):
                        g.write( second_last_set_element_unique[s] + ' ' )
                        #
                        value_indices_s = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[-2] ] ) if x == str( second_last_set_element_unique[s] ) ]
                        value_indices_n1 = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[0] ] ) if x == str( this_set_element_unique_1[n1] ) ]
                        #
                        r_index = set(value_indices_s) & set(value_indices_n1)
                        #
                        value_indices = list( r_index )
                        value_indices.sort()
                        #
                        these_values = []
                        for val in range( len( value_indices ) ):
                            these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                        for val in range( len( these_values ) ):
                            g.write( str( these_values[val] ) + ' ' )
                        g.write('\n') #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
            #%%%
            elif len(this_param_keys) == 4:
                this_set_element_unique_all = []
                for pkey in range( len(this_param_keys)-2 ):
                    for i in range( 2, len(header_indices)-1 ):
                        if header_indices[i] == this_param_keys[pkey]:
                            this_set_element = this_scenario_data[ this_param ][ header_indices[i] ]
                            this_set_element_unique_all.append( list( set( this_set_element ) ) )
                #
                this_set_element_unique_1 = deepcopy( this_set_element_unique_all[0] )
                this_set_element_unique_2 = deepcopy( this_set_element_unique_all[1] )
                this_set_element_unique_2.sort()
                #
                for n1 in range( len( this_set_element_unique_1 ) ):
                    count_storage = 0
                    for n2 in range( len( this_set_element_unique_2 ) ): #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
                        g.write( '[' + str( this_set_element_unique_1[n1] ) + ',' + str( this_set_element_unique_2[n2] ) + ',*,*]:\n' )
                        # get the last and second last parameters of the list:
                        last_set_element = this_scenario_data[ this_param ][ this_param_keys[-1] ] # header_indices.index( this_param_keys[-1] ) ]
                        last_set_element_unique = [] # list( set( last_set_element ) )
                        #
                        second_last_set_element = this_scenario_data[ this_param ][ this_param_keys[-2] ] # header_indices.index( this_param_keys[-2] ) ]
                        second_last_set_element_unique = [] # list( set( second_last_set_element ) )
                        
                        for u in range( len( last_set_element ) ):
                            if last_set_element[u] not in last_set_element_unique:
                                last_set_element_unique.append( last_set_element[u] )
                        
                        for u in range( len( second_last_set_element ) ):
                            if second_last_set_element[u] not in second_last_set_element_unique:
                                second_last_set_element_unique.append( second_last_set_element[u] )
                        
                        #
                        if this_param == 'TechnologyToStorage' or this_param == 'TechnologyFromStorage':
                            last_set_element = this_scenario_data[ this_param ][ this_param_keys[-2] ]
                            last_set_element_unique = []
                            second_last_set_element = this_scenario_data[ this_param ][ this_param_keys[-1] ]
                            second_last_set_element_unique = [] 
                            for u in range( len( last_set_element ) ):
                                if last_set_element[u] not in last_set_element_unique:
                                    last_set_element_unique.append( last_set_element[u] )
                            
                            for u in range( len( second_last_set_element ) ):
                                if second_last_set_element[u] not in second_last_set_element_unique:
                                    second_last_set_element_unique.append( second_last_set_element[u] )
                                    
                                    
                        for y in range( len( last_set_element_unique ) ):
                            if this_param == 'TechnologyToStorage' or this_param == 'TechnologyFromStorage':
                                g.write( str( second_last_set_element_unique[count_storage]  ) + ' ')
                            else:
                                g.write( str( last_set_element_unique[y] ) + ' ')
                        if this_param != 'TechnologyToStorage' or this_param != 'TechnologyFromStorage':
                            g.write(':=\n')
                        else:
                            g.write( str( last_set_element_unique[y] ) + ' ')
                        
                        if this_param == 'TechnologyToStorage' or this_param == 'TechnologyFromStorage':
                            second_last_set_element_unique_iter = [this_set_element_unique_2[n2]]
                        else:
                            second_last_set_element_unique_iter = second_last_set_element_unique
                        
                        if this_param_keys[-2] == 'l':
                            second_last_set_element_unique_iter_temp = second_last_set_element_unique_iter
                            second_last_set_element_unique_iter = []
                            for sdp in range(num_time_slices_SDP):
                                second_last_set_element_unique_iter.append(second_last_set_element_unique_iter_temp[sdp])
                        
                        #
                        for s in range( len( second_last_set_element_unique_iter ) ):                                  
                            if (this_param == 'TechnologyToStorage' or this_param == 'TechnologyFromStorage'):
                                for p in range(len(second_last_set_element_unique_iter)):
                                    value_indices_s = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[-2] ] ) if x == str( second_last_set_element_unique[s] ) ]
                                    value_indices_n1 = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[0] ] ) if x == str( this_set_element_unique_1[n1] ) ]
                                    value_indices_n2 = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[1] ] ) if x == str( this_set_element_unique_2[n2] ) ]
                                    # r_index = set(value_indices_s) & set(value_indices_n1) & set(value_indices_n2)
                                    r_index = set(value_indices_n1) & set(value_indices_n2)
                                    value_indices = list( r_index )
                                    value_indices.sort()
                                    #
                                    these_values = []
                                    for val in range( len( value_indices ) ):
                                        these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                                    if these_values != []:
                                        if p == 0:
                                            # g.write( second_last_set_element_unique[count_storage] + ' ' )
                                            g.write( last_set_element_unique[y] + ' ' )
                                    for val in range( len( these_values ) ):
                                        g.write( str( these_values[val] ) + ' ' )
                                count_storage += 1
                            #
                            else:
                                value_indices_s = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[-2] ] ) if x == str( second_last_set_element_unique[s] ) ]
                                value_indices_n1 = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[0] ] ) if x == str( this_set_element_unique_1[n1] ) ]
                                value_indices_n2 = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[1] ] ) if x == str( this_set_element_unique_2[n2] ) ]
                                r_index = set(value_indices_s) & set(value_indices_n1) & set(value_indices_n2)
                                value_indices = list( r_index )
                                value_indices.sort()
                                #
                                these_values = []
                                for val in range( len( value_indices ) ):
                                    these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                                if these_values != []:
                                    g.write( second_last_set_element_unique[s] + ' ' )                                    
                                for val in range( len( these_values ) ):
                                    g.write( str( these_values[val] ) + ' ' )
                            if these_values != []:
                                g.write('\n') #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

            #%%%
            if len(this_param_keys) == 5:
                # print(5, p, this_param)
                this_set_element_unique_all = []
                last_set_element_unique = []
                second_last_set_element_unique = []
                for pkey in range(len(this_param_keys)-2):
                    for i in range(2, len(header_indices)-1):
                        if header_indices[i] == this_param_keys[pkey]:
                            this_set_element = this_scenario_data[this_param][header_indices[i]]
                            this_set_element_unique_all.append(list(set(this_set_element)))
                #
                this_set_element_unique_1 = deepcopy(this_set_element_unique_all[0])
                this_set_element_unique_2 = deepcopy(this_set_element_unique_all[1])

                last_set_element = np.array(this_scenario_data[this_param][this_param_keys[-1]])
                last_set_element_unique = np.unique(last_set_element)

                second_last_set_element = np.array(this_scenario_data[this_param][this_param_keys[-2]])
                second_last_set_element_unique = np.unique(second_last_set_element)

                long_list1 = this_scenario_data[this_param][this_param_keys[1]]
                long_list2 = this_scenario_data[this_param][this_param_keys[2]]
                concat_result = list(map(lambda x, y: x + '-' + y, long_list1, long_list2))
                concat_result_set = list(set(concat_result))
                
                # print('second_last_set_element',second_last_set_element)
                # sys.exit()
                n1_faster_temp = str()
                n2_faster_temp = str()
                second_last_set_element_unique_temp = str()
                nx_temp = 0.11
                
                for n1 in range(len(this_set_element_unique_1)):
                    for nx in range(len(concat_result_set)):
                        n1_faster = concat_result_set[nx].split('-')[0]
                        n2_faster = concat_result_set[nx].split('-')[1]

                        for s in range(len(second_last_set_element_unique)):
                            value_indices_s = [i for i, x in enumerate(this_scenario_data[this_param][this_param_keys[-2]]) if x == str(second_last_set_element_unique[s])]
                            value_indices_n1 = [i for i, x in enumerate(this_scenario_data[this_param][this_param_keys[0]]) if x == str(this_set_element_unique_1[n1])]
                            value_indices_n2 = [i for i, x in enumerate(this_scenario_data[this_param][this_param_keys[1]]) if x == str(n1_faster)]
                            value_indices_n3 = [i for i, x in enumerate(this_scenario_data[this_param][this_param_keys[2]]) if x == str(n2_faster)]

                            r_index = set(value_indices_s) & set(value_indices_n1) & set(value_indices_n2) & set(value_indices_n3)
                            value_indices = list(r_index)
                            value_indices.sort()
                            

                            if len(value_indices) != 0:
                                if nx != nx_temp:    
                                    g.write('[' + str(this_set_element_unique_1[n1]) + ',' + str(n1_faster) + ',' + str(n2_faster) + ',*,*]:\n')

                                    for y in range(len(last_set_element_unique)):
                                        g.write(str(last_set_element_unique[y]) + ' ')
                                    g.write(':=\n')

                                g.write(second_last_set_element_unique[s] + ' ')

                                these_values = []
                                for val in range(len(value_indices)):
                                    these_values.append(this_scenario_data[this_param]['value'][value_indices[val]])
                                for val in range(len(these_values)):
                                    g.write(str(these_values[val]) + ' ')
                                
                                nx_temp = nx
                                    
                                g.write('\n')


            #-----------------------------------------#
            g.write( ';\n\n' )

    #
    # remember the default values for printing:
    for param_without_values in parameters_without_values:
        this_param_default_value = list_param_default_value.loc[list_param_default_value["Parameter"] == param_without_values, "Default_Value"].values[0]
        g.write(f'param {param_without_values} default {this_param_default_value} :=\n;\n')
    # for new_final_set in special_sets:
    #     g.write(new_final_set)
    g.write('#\n' + 'end;\n')
    g.close()
    #
    # Pre-process the data file to add commodity-technology-mode sets and CRF/PvAnnuity
    from preprocess_data import main as preprocess_main
    preprocess_main(g_path, g_path)
    #
    ###########################################################################################################################
    # Furthermore, we must print the inputs separately for fast deployment of the input matrix:
    basic_header_elements = [ 'Future.ID', 'Strategy.ID', 'Strategy', 'Commodity', 'Technology', 'Emission', 'TimeSlice', 'Year']#, 'Season']
    #
    parameters_to_print = parameters_in_the_model
    #
    input_params_table_headers = basic_header_elements + parameters_to_print
    all_data_row = []
    all_data_row_partial = []
    #
    combination_list = []
    synthesized_all_data_row = []
    #
    # memory elements:
    f_unique_list, f_counter, f_counter_list, f_unique_counter_list = [], 1, [], []
    t_unique_list, t_counter, t_counter_list, t_unique_counter_list = [], 1, [], []
    e_unique_list, e_counter, e_counter_list, e_unique_counter_list = [], 1, [], []
    l_unique_list, l_counter, l_counter_list, l_unique_counter_list = [], 1, [], []
    y_unique_list, y_counter, y_counter_list, y_unique_counter_list = [], 1, [], []
    #
    for p in range( len( parameters_to_print ) ):
        #
        this_p_index = S_DICT_params_structure[ 'parameter' ].index( parameters_to_print[p] )
        this_p_index_list = S_DICT_params_structure[ 'index_list' ][ this_p_index ]
        # print('ACA')
        # print(parameters_to_print[p])
        # print(this_p_index_list)
        #
        for n in range( 0, len( this_scenario_data[ parameters_to_print[p] ][ 'value' ] ) ):
            #
            single_data_row = []
            single_data_row_partial = []
            #
            single_data_row.append( fut )
            single_data_row.append( scen )
            single_data_row.append( scenario_list[scen] )
            #
            strcode = ''
            #
            if 'f' in this_p_index_list:
                single_data_row.append( this_scenario_data[ parameters_to_print[p] ][ 'f' ][n] ) # Filling FUEL if necessary
                if single_data_row[-1] not in f_unique_list:
                    f_unique_list.append( single_data_row[-1] )
                    f_counter_list.append( f_counter )
                    f_unique_counter_list.append( f_counter )
                    f_counter += 1
                else:
                    f_counter_list.append( f_unique_counter_list[ f_unique_list.index( single_data_row[-1] ) ] )
                strcode += str(f_counter_list[-1])
            else:
                single_data_row.append( '' )
                strcode += '0'
            #
            if 't' in this_p_index_list:
                single_data_row.append( this_scenario_data[ parameters_to_print[p] ][ 't' ][n] ) # Filling TECHNOLOGY if necessary
                if single_data_row[-1] not in t_unique_list:
                    t_unique_list.append( single_data_row[-1] )
                    t_counter_list.append( t_counter )
                    t_unique_counter_list.append( t_counter )
                    t_counter += 1
                else:
                    t_counter_list.append( t_unique_counter_list[ t_unique_list.index( single_data_row[-1] ) ] )
                strcode += str(t_counter_list[-1])
            else:
                single_data_row.append( '' )
                strcode += '0'
            #
            if 'e' in this_p_index_list:
                single_data_row.append( this_scenario_data[ parameters_to_print[p] ][ 'e' ][n] ) # Filling EMISSION if necessary
                if single_data_row[-1] not in e_unique_list:
                    e_unique_list.append( single_data_row[-1] )
                    e_counter_list.append( e_counter )
                    e_unique_counter_list.append( e_counter )
                    e_counter += 1
                else:
                    e_counter_list.append( e_unique_counter_list[ e_unique_list.index( single_data_row[-1] ) ] )
                strcode += str(e_counter_list[-1])
            else:
                single_data_row.append( '' )
                strcode += '0'
            #
            if 'l' in this_p_index_list:
                single_data_row.append( this_scenario_data[ parameters_to_print[p] ][ 'l' ][n] ) # Filling SEASON if necessary
                if single_data_row[-1] not in l_unique_list:
                    l_unique_list.append( single_data_row[-1] )
                    l_counter_list.append( l_counter )
                    l_unique_counter_list.append( l_counter )
                    l_counter += 1
                else:
                    l_counter_list.append( l_unique_counter_list[ l_unique_list.index( single_data_row[-1] ) ] )
                strcode += str(l_counter_list[-1])
            else:
                single_data_row.append( '' )
                strcode += '000' # this is done to avoid repeated characters
            #
            if 'y' in this_p_index_list:
                single_data_row.append( this_scenario_data[ parameters_to_print[p] ][ 'y' ][n] ) # Filling YEAR if necessary
                if single_data_row[-1] not in y_unique_list:
                    y_unique_list.append( single_data_row[-1] )
                    y_counter_list.append( y_counter )
                    y_unique_counter_list.append( y_counter )
                    y_counter += 1
                else:
                    y_counter_list.append( y_unique_counter_list[ y_unique_list.index( single_data_row[-1] ) ] )
                strcode += str(y_counter_list[-1])
            else:
                single_data_row.append( '' )
                strcode += '0'
            #
            this_combination_str = str(1) + strcode # deepcopy( single_data_row )
            this_combination = int( this_combination_str )
            #
            for aux_p in range( len(basic_header_elements), len(basic_header_elements) + len( parameters_to_print ) ):
                if aux_p == p + len(basic_header_elements):
                    single_data_row.append( this_scenario_data[ parameters_to_print[p] ][ 'value' ][n] ) # Filling the correct data point
                    single_data_row_partial.append( this_scenario_data[ parameters_to_print[p] ][ 'value' ][n] )
                else:
                    single_data_row.append( '' )
                    single_data_row_partial.append( '' )
            #
            all_data_row.append( single_data_row )
            all_data_row_partial.append( single_data_row_partial )
            #
            if this_combination not in combination_list:
                combination_list.append( this_combination )
                synthesized_all_data_row.append( single_data_row )
            else:
                ref_combination_index = combination_list.index( this_combination )
                ref_parameter_index = input_params_table_headers.index( parameters_to_print[p] )
                synthesized_all_data_row[ ref_combination_index ][ ref_parameter_index ] = deepcopy( single_data_row_partial[ ref_parameter_index-len( basic_header_elements ) ] )
                #
            #
        #
    #
    ###########################################################################################################################

    # Make a DataFrame with the data
    param_parquet_path = os.path.join(current_script_path, 'Experimental_Platform', 'Futures', scenario_list[scen], str( scenario_list[scen] ) + '_' + str( fut ), str( scenario_list[scen] ) + '_' + str( fut ) + '_Input.parquet')
    data_dict = {header: [row[i] for row in synthesized_all_data_row] for i, header in enumerate(input_params_table_headers)}
    df = pd.DataFrame(data_dict)

    # Define the columns to exclude in lowercase
    columns_to_exclude = [
        'strategy', 'future.id', 'region', 'commodity', 'technology', 'emission',
        'timeslice', 'mode_of_operation', 'season', 'daytype',
        'dailytimebracket', 'storage', 'storageintraday', 'storageintrayear',
        'udc', 'scen_fut'
    ]
    
    # Loop through all columns, normalize names before comparing
    for col in df.columns:
        if col.lower() not in columns_to_exclude:  # Case-insensitive check
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')  # Convert to float, NaNs for invalids
                df[col] = df[col].fillna(0)  # Replace NaNs
                df = df.dropna(subset=[col])  # Drop rows with remaining NaNs
            except Exception as e:
                print(f"Warning: Could not convert column {col} to numeric: {e}")



    
    dic_columnas={'Commodity':'COMMODITY','Technology':'TECHNOLOGY','Emission':'EMISSION','Season':'SEASON','Year':'YEAR','TimeSlice':'TIMESLICE','Region':'REGION'}
    df = df.rename(columns=dic_columnas)
    # Save as Parquet file
    df.to_parquet(param_parquet_path, engine='pyarrow', index=False)
    df.to_csv(param_parquet_path.replace('parquet','csv'), index=False, sep=';')

    
    
    
    
    # param_txt_path = param_parquet_path.replace('_Input','.txt')
    
    # # Isolate params in subfiles
    # data_per_param, special_sets = AUX.isolate_params(param_txt_path)
    # # print(param_txt_path,scen)
    # # print(data_per_param)
    
    # # Generate CSV parameters files for each scenario
    # list_dataframes, dict_dataframes, parameters_without_values = AUX.generate_df_per_param(scenario_list[scen], 
    #                                     data_per_param,
    #                                     num_time_slices_SDP)

    # # Create future 0 input dataset'
    # AUX.create_input_dataset_future_0(list_dataframes,
    #                                   scenario_list[scen],
    #                                   scen,
    #                                   fut,
    #                                   g_path.replace('.txt',''))
    
    
    # return data_per_param
#

#
if __name__ == '__main__':
    
    # Take the solver from the script call
    main_path = sys.argv
    solver = main_path[1]
    osemosys_model = main_path[2]
    Interface_RDM = main_path[3]
    shape_file = main_path[4]
    
    # solver = 'cplex'
    # osemosys_model = 'model.v.5.4.txt'
    # Interface_RDM = r'C:\Users\ClimateLeadGroup\Desktop\CLG_repositories\osemosys-rdm\src\Interface_RDM.xlsx'
    # shape_file = r'C:\Users\ClimateLeadGroup\Desktop\CLG_repositories\osemosys-rdm\src\workflow\2_Miscellaneous\shape_of_demand.csv'

    book=pd.ExcelFile(Interface_RDM)
    '''
    Let us define parameters to print 
    '''
    parameters_to_print = book.parse( 'To_Print' , 0)
    
    '''
    Let us define some control inputs internally:
    '''
    # generator_or_executor = 'None'
    generator_or_executor = 'Both'
    # generator_or_executor = 'Generator'
    # generator_or_executor = 'Executor'
    inputs_txt_csv = 'Both'
    # inputs_txt_csv = 'csv'
    parallel_or_linear = 'Parallel'
    # parallel_or_linear = 'Linear'
    


    #############################################################################################################################
    '''
    # 1.A) We extract the strucute setup of the model based on 'Structure.xlsx'
    '''
    # Get the directory of the current script
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path to the Excel file, relative to the script's directory
    structure_filename = os.path.join(current_script_path, '0_From_Confection', 'B1_Model_Structure.xlsx')
    structure_file = pd.ExcelFile(structure_filename)
    structure_sheetnames = structure_file.sheet_names  # see all sheet names
    sheet_sets_structure = pd.read_excel(open(structure_filename, 'rb'),
                                         header=None,
                                         sheet_name=structure_sheetnames[0])
    sheet_params_structure = pd.read_excel(open(structure_filename, 'rb'),
                                           header=None,
                                           sheet_name=structure_sheetnames[1])
    sheet_vars_structure = pd.read_excel(open(structure_filename, 'rb'),
                                         header=None,
                                         sheet_name=structure_sheetnames[2])

    S_DICT_sets_structure = {'set':[],'initial':[],'number_of_elements':[],'elements_list':[]}
    for col in range(1,len(sheet_sets_structure.iloc[1, 1:].tolist())+1):
        S_DICT_sets_structure['set'].append( sheet_sets_structure.iat[0, col] )
        S_DICT_sets_structure['initial'].append( sheet_sets_structure.iat[1, col] )
        S_DICT_sets_structure['number_of_elements'].append( int( sheet_sets_structure.iat[2, col] ) )
        #
        element_number = int( sheet_sets_structure.iat[2, col] )
        this_elements_list = []
        if element_number >= 0:
            for n in range( 1, element_number+1 ):
                this_elements_list.append( sheet_sets_structure.iat[2+n, col] )
        S_DICT_sets_structure['elements_list'].append( this_elements_list )
    #
    S_DICT_params_structure = {'category':[],'parameter':[],'number_of_elements':[],'index_list':[]}
    param_category_list = []
    for col in range(1,len(sheet_params_structure.iloc[1, 1:].tolist())+1):
        if str( sheet_params_structure.iat[0, col] ) != '':
            param_category_list.append( sheet_params_structure.iat[0, col] )
        S_DICT_params_structure['category'].append( param_category_list[-1] )
        S_DICT_params_structure['parameter'].append( sheet_params_structure.iat[1, col] )
        S_DICT_params_structure['number_of_elements'].append( int( sheet_params_structure.iat[2, col] ) )
        #
        index_number = int( sheet_params_structure.iat[2, col] )
        this_index_list = []
        for n in range(1, index_number+1):
            this_index_list.append( sheet_params_structure.iat[2+n, col] )
        S_DICT_params_structure['index_list'].append( this_index_list )
    #
    S_DICT_vars_structure = {'category':[],'variable':[],'number_of_elements':[],'index_list':[]}
    var_category_list = []
    for col in range(1,len(sheet_vars_structure.iloc[1, 1:].tolist())+1):
        if str( sheet_vars_structure.iat[0, col] ) != '':
            var_category_list.append( sheet_vars_structure.iat[0, col] )
        S_DICT_vars_structure['category'].append( var_category_list[-1] )
        S_DICT_vars_structure['variable'].append( sheet_vars_structure.iat[1, col] )
        S_DICT_vars_structure['number_of_elements'].append( int( sheet_vars_structure.iat[2, col] ) )
        #
        index_number = int( sheet_vars_structure.iat[2, col] )
        this_index_list = []
        for n in range(1, index_number+1):
            this_index_list.append( sheet_vars_structure.iat[2+n, col] )
        S_DICT_vars_structure['index_list'].append( this_index_list )    
    #############################################################################################################################
    global time_range_vector # This is the variable that manages time throughout the experiment
    time_range_vector = [ int(i) for i in S_DICT_sets_structure[ 'elements_list' ][0] ]
    
    global final_year
    final_year = time_range_vector[-1]
    global initial_year
    initial_year = time_range_vector[0]
    
    '''
    For all effects, read all the user-defined scenarios in future 0, created by hand in Base_Runs_Generator.py ;
    These data parameters serve as the basis to implement the experiment.
    '''

    '''
    Part 1: the experiment data generator for N samplles that are DEFINED BY USER
    Part 2: read all relevant inputs based on the SPD heritage
    Part 3: the manipulation of the base data where applicable and generation of new data
        (read the column 'Explored_Parameter_is_Relative_to_Baseline' of Uncertainty_Table)
        NOTE: part 3 has a strict manipulation procedure
        NOTE: part 3 must execute the experiment entirely
    CONTROL ACTION 1: Select the scenario that you want to generate (USER INPUT).
    CONTROL ACTION 2: select all the futures that you want to process in this run, from beginning to end
    Part 4: print the new .txt files
    '''
    
    setup_table = book.parse( 'Setup' , 0)
    scenarios_to_reproduce = str( setup_table.loc[ 0 ,'Scenario_to_Reproduce'] )
    experiment_ID = str( setup_table.loc[ 0 ,'Experiment_ID'] )
    region = str( setup_table.loc[ 0 ,'Region'] )
    # EV sign-correction configuration (read from Setup sheet, semicolon-separated)
    _raw_conv = setup_table.loc[ 0 ,'EV_Conventional_Patterns']
    _raw_elec = setup_table.loc[ 0 ,'EV_Electric_Pattern']
    _raw_udcs = setup_table.loc[ 0 ,'EV_UDCs']
    ev_config_is_empty = (
        pd.isna(_raw_conv) or str(_raw_conv).strip() == '' or
        pd.isna(_raw_elec) or str(_raw_elec).strip() == '' or
        pd.isna(_raw_udcs) or str(_raw_udcs).strip() == ''
    )
    if ev_config_is_empty:
        conv_patterns = []
        elec_pattern  = ''
        ev_udcs       = []
        print('    WARNING: EV sign-correction config is incomplete in Setup sheet '
              '(EV_Conventional_Patterns, EV_Electric_Pattern, or EV_UDCs is empty). '
              'UDC EV sign correction will be SKIPPED.')
    else:
        conv_patterns = str(_raw_conv).split(';')
        elec_pattern  = str(_raw_elec).strip()
        ev_udcs       = str(_raw_udcs).split(';')
    df_Params_Sets_Vari = book.parse( 'Params_Sets_Vari' )
    # Step 1: Remove the 'parameter' column and store its values to use as index
    new_index = df_Params_Sets_Vari['parameter'].reset_index(drop=True)
    df_Params_Sets_Vari = df_Params_Sets_Vari.drop(columns='parameter')
    
    # Step 2: Replace NaN values in the index (empty cells) with meaningful labels
    new_index = new_index.fillna('')  # Replace NaN with empty strings
    new_index.iloc[0] = 'Number'      # Rename first row index
    new_index.iloc[1] = 'Set1'        # Rename second row index
    new_index.iloc[2] = 'Set2'        # Rename third row index
    new_index.iloc[3] = 'Set3'        # Rename fourth row index
    
    # Step 3: Assign the updated labels as the new index of the DataFrame
    df_Params_Sets_Vari.index = new_index
    
    # Step 4: Extract the mapping from the existing dictionary
    initials = S_DICT_sets_structure['initial']
    full_names = S_DICT_sets_structure['set']
    
    # Step 5: Create a dictionary for easy replacement: {'y': 'YEAR', ...}
    replacement_dict = dict(zip(initials, full_names))
    
    # Step 6: Define the rows (index values) that need to be processed
    rows_to_replace = ['Set1', 'Set2', 'Set3']
    
    # Step 7: Replace the values in those rows using the mapping
    for row in rows_to_replace:
        df_Params_Sets_Vari.loc[row] = df_Params_Sets_Vari.loc[row].replace(replacement_dict)

    #
    # global Initial_Year_of_Uncertainty
    # Initial_Year_of_Uncertainty = int( setup_table.loc[ 0 ,'Initial_Year_of_Uncertainty'] )
    
    '''''
    ################################# PART 1 #################################
    '''''
    print('1: I start by reading the Uncertainty Table and systematically perturbing the paramaters.')
    uncertainty_table = book.parse( 'Uncertainty_Table' )
    # use .loc to access [row, column name]
    # experiment_variables = list( uncertainty_table.columns )
    #
    np.random.seed( 555 )
    P = len( uncertainty_table.index ) # variables to vary
    N = int( setup_table.loc[ 0 ,'Number_of_Runs'] )  # number of samples

    # Here we need to define the number of elements that need to be included in the hypercube
    # list_xlrm_IDs = uncertainty_table['XLRM_ID']
    # ignore_indices = [p for p in range(len(list_xlrm_IDs)) if list_xlrm_IDs[p] == 'none']  # these are positions where we should not ask for a lhs sample
    ignore_indices = []                  
    subtracter = 0
    col_idx = {}
    for p in range( P ):
        if p in ignore_indices:
            subtracter += 1
            col_idx.update({p:'none'})
        else:
            col_idx.update({p:p-subtracter})

    hypercube = lhs( P-subtracter , samples = N )
    # hypercube[p] gives vector with values of variable p across the N futures, hence len( hypercube[p] ) = N
    experiment_dictionary = {}
    # all_dataset_address = './1_Baseline_Modelling/'

    # Ciclo para N futuros
    for n in range( N ):
        this_future_X_change_direction = [] # up or down
        this_future_X_change = [] # this is relative to baseline
        this_future_X_param = [] # this is NOT relative to baseline
        this_future_X_change_direction_year = [] # up or down
        this_future_X_change_year = [] # this is relative to baseline
        this_future_X_param_year = [] # this is NOT relative to baseline
        #
        X_Num_unique = []
        X_Num = []
        X_Cat = []
        # Exact_Param_Num = []
        
        # Ciclo para P lineas de uncertidumbre
        for p in range( P ):
            # Here we extract crucial infromation for each row:
            #
            math_type = str( uncertainty_table.loc[ p ,'X_Mathematical_Type'] )
            Explored_Parameter_of_X = str( uncertainty_table.loc[ p ,'Explored_Parameter_of_X'] )
            #
            Involved_Scenarios = str( uncertainty_table.loc[ p ,'Involved_Scenarios'] ).replace(' ','').split(';')
            Involved_First_Sets_in_Osemosys = str( uncertainty_table.loc[ p ,'Involved_First_Sets_in_Osemosys'] ).replace(' ','').split(';')
            Involved_Second_Sets_in_Osemosys = str( uncertainty_table.loc[ p ,'Involved_Second_Sets_in_Osemosys'] ).replace(' ','').split(';')
            Involved_Third_Sets_in_Osemosys = str( uncertainty_table.loc[ p ,'Involved_Third_Sets_in_Osemosys'] ).replace(' ','').split(';')
            # Emission_Involved = str( uncertainty_table.loc[ p ,'Emission_Involved'] ).replace(' ','').split(';')
            # Emission_Mode_Operations = str( uncertainty_table.loc[ p ,'Emission_Mode_Operations'] ).replace(' ','').split(';')
            Exact_Parameters_Involved_in_Osemosys = str( uncertainty_table.loc[ p ,'Exact_Parameters_Involved_in_Osemosys'] ).replace(' ','').split(';')
            Exact_X = str( uncertainty_table.loc[ p ,'X_Plain_English_Description'] )
            Initial_Year_of_Uncertainty_EP = int( uncertainty_table.loc[ p ,'Initial_Year_of_Uncertainty'] )
            # Emssion_year_0 = str( uncertainty_table.loc[ p ,'Emssion_year_0'] )

            # Read Dependency column (for complementary dependencies between consecutive rows)
            try:
                Dependency_Flag = str(uncertainty_table.loc[p, 'Dependency']).strip().upper()
            except KeyError:
                # Column doesn't exist in older versions - default to NO
                Dependency_Flag = 'NO'

            # Validate Dependency configuration
            # Note: Row 0 CAN have Dependency=YES (it means row 1 depends on row 0)
            if p == P-1 and Dependency_Flag in ['YES', 'SI'] and n == 0:
                # Only print warning once (when n == 0)
                print(f"WARNING: Last row (X_Num={X_Num[-1]}) has Dependency=YES but there's no next row to depend on it")

            #
            #######################################################################
            # print(1,p)
            # print(2,p)
            # print(3,p)
            # sys.exit(3)
            X_Num.append( int( uncertainty_table.loc[ p ,'X_Num'] ) )
            X_Cat.append( str( uncertainty_table.loc[ p ,'X_Category'] ) )
            # Exact_Param_Num.append( int( uncertainty_table.loc[ p ,'Explored_Parameter_Number'] ) )
            #
            this_min = uncertainty_table.loc[ p , 'Min_Value' ]
            this_max = uncertainty_table.loc[ p , 'Max_Value' ]
            #
            this_loc = this_min
            this_loc_scale = this_max - this_min
            
            #
            hyper_col_idx = col_idx[p]
            if hyper_col_idx != 'none':
                evaluation_value_preliminary = hypercube[n].item(hyper_col_idx)
            else:
                evaluation_value_preliminary = 1
            #
            evaluation_value = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc, this_loc_scale)
            #
            
            # this_min_year = uncertainty_table.loc[ p , 'Emis_min_year' ]
            # this_max_year = uncertainty_table.loc[ p , 'Emis_max_year' ]
            # #
            # if this_min_year != '-' and this_max_year != '-':
            #     this_loc_year = this_min_year
            #     this_loc_scale_year = this_max_year - this_min_year
            #     evaluation_value_year = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc_year, this_loc_scale_year)
            #
            #######################################################################
            # here, we program the direction dependencies:
            # this_depending_on_X_list = str( uncertainty_table.loc[ p ,'Sign_Dependency_on_Specified_Xs'] ).replace(' ','').split(';')
            # if ( p > 1 ) and ( str( uncertainty_table.loc[ p ,'Sign_Dependency_on_Specified_Xs'] ) != 'n.a.' ) and ( len(this_depending_on_X_list) == 1 ):
            #     #
            #     depending_on_X = int( uncertainty_table.loc[ p ,'Sign_Dependency_on_Specified_Xs'] )
            #     #
            #     depending_on_X_index = X_Num.index( depending_on_X )
            #     # we modify the direction by changing this_loc and this_loc_scale:
            #     # we apply the correction only if the original probability is incompatible
            #     if str(this_future_X_change_direction[depending_on_X_index]) == 'down' and evaluation_value > 1: # this approach serves for symmentrical or assymetrical experiments
            #         this_loc_scale = 0.5*(this_max - this_min)
            #     elif str(this_future_X_change_direction[depending_on_X_index]) == 'up' and evaluation_value < 1: # this approach serves for symmentrical or assymetrical experiments
            #         this_loc = this_min + 0.5*(this_max - this_min)
            #     #
            #     evaluation_value = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc, this_loc_scale)
            # #
            # #######################################################################
            # #
            # if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline' ] ) == 'YES':
            #     if evaluation_value > 1:
            #         this_future_X_change_direction.append('up')
            #     else:
            #         this_future_X_change_direction.append('down')
            #     #
            #     this_future_X_change.append( evaluation_value )
            #     #
            #     this_future_X_param.append('n.a.')
            #     #

            ######################################################################
            # here, we program the direction dependencies:
            # we modify the direction by changing this_loc and this_loc_scale:
            # we apply the correction only if the original probability is incompatible
            if evaluation_value > 1: # this approach serves for symmentrical or assymetrical experiments
                this_loc_scale = 0.5*(this_max - this_min)
            elif evaluation_value < 1: # this approach serves for symmentrical or assymetrical experiments
                this_loc = this_min + 0.5*(this_max - this_min)
            #
            evaluation_value = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc, this_loc_scale)
            #
            #######################################################################
            # NOTE: Complementary dependency (Dependency=YES) is now enforced
            # at value-level in Step 3 (application phase), not here in Step 1.
            # The dependent row's evaluation_value from LHS is kept but will be
            # overridden during application to preserve share constraints.
            #######################################################################
            if evaluation_value > 1:
                this_future_X_change_direction.append('up')
            else:
                this_future_X_change_direction.append('down')
            #
            this_future_X_change.append( evaluation_value )
            #
            this_future_X_param.append('n.a.')
            #
            #
            # if this_min_year != '-' and this_max_year != '-':
            #     if evaluation_value_year > 1: # this approach serves for symmentrical or assymetrical experiments
            #         this_loc_scale = 0.5*(this_max_year - this_min_year)
            #     elif evaluation_value_year < 1: # this approach serves for symmentrical or assymetrical experiments
            #         this_loc_year = this_min_year + 0.5*(this_max_year - this_min_year)
            #     #
            #     evaluation_value_year = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc_year, this_loc_scale_year)
            #     #
            #     #######################################################################
            #     if evaluation_value_year > 1:
            #         this_future_X_change_direction_year.append('up')
            #     else:
            #         this_future_X_change_direction_year.append('down')
            #     #
            #     this_future_X_change_year.append( evaluation_value_year )
            #     #
            #     this_future_X_param_year.append('n.a.')
             #   
            #
            #######################################################################
            # We can now store all the information for each future in a dictionary:
            if n == 0: # the dictionary is created only when the first future appears
                #
                ###################################################################################################################################
                if int( uncertainty_table.loc[ p ,'X_Num'] ) not in X_Num_unique: #elif
                    #
                    X_Num_unique.append( int( uncertainty_table.loc[ p ,'X_Num'] ) )
                    #
                    # Relative_to_Baseline = str( uncertainty_table.loc[ p ,'Explored_Parameter_is_Relative_to_Baseline'] )
                    #
                    # experiment_dictionary.update( { X_Num_unique[-1]:{ 'Category':X_Cat[-1], 'Math_Type':math_type, 'Relative_to_Baseline':Relative_to_Baseline, 'Exact_X':Exact_X } } )
                    experiment_dictionary.update( { X_Num_unique[-1]:{ 'Category':X_Cat[-1], 'Math_Type':math_type, 'Exact_X':Exact_X } } )                                                                                                                       
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Involved_Scenarios':Involved_Scenarios })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Involved_First_Sets_in_Osemosys':Involved_First_Sets_in_Osemosys })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Involved_Second_Sets_in_Osemosys':Involved_Second_Sets_in_Osemosys })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Involved_Third_Sets_in_Osemosys':Involved_Third_Sets_in_Osemosys })
                    # experiment_dictionary[ X_Num_unique[-1] ].update({ 'Emission_Involved':Emission_Involved })
                    # experiment_dictionary[ X_Num_unique[-1] ].update({ 'Emission_Mode_Operations':Emission_Mode_Operations })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Exact_Parameters_Involved_in_Osemosys':Exact_Parameters_Involved_in_Osemosys })
                    
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Initial_Year_of_Uncertainty':Initial_Year_of_Uncertainty_EP })
                    # experiment_dictionary[ X_Num_unique[-1] ].update({ 'Emssion_year_0':Emssion_year_0 })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Dependency_Flag': Dependency_Flag })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Futures':[x for x in range( 1, N+1 ) ] })
                    #
                    if math_type in ['Time_Series', 'Discrete_Investments', 'Mult_Adoption_Curve', 'Mult_Restriction', 'Mult_Restriction_Start', 'Mult_Restriction_End', 'Timeslices_Curve', 'Constant', 'Logistic', 'Linear', 'Step']:
                        experiment_dictionary[ X_Num_unique[-1] ].update({ 'Explored_Parameter_of_X':Explored_Parameter_of_X } )
                        experiment_dictionary[ X_Num_unique[-1] ].update({ 'Values':[0.0 for x in range( 1, N+1 ) ] })
                        experiment_dictionary[ X_Num_unique[-1] ].update({ 'Emission_Years':[0.0 for x in range( 1, N+1 ) ] })
                        # # We fill the data for future n=1 // it is important to note that the future n=0 can have completely different parameters when values are not relative to baseline
                        # if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'YES':
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0] = this_future_X_change[-1] # here n=0

                            
                        # elif str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'NO':
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0] = this_future_X_param[-1] # here n=0
                            #
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0] = this_future_X_change[-1] # here n=0
                        # if this_min_year != '-' and this_max_year != '-':
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Emission_Years' ][0] = int(round(this_future_X_change_year[-1],0)) # here n=0
                        # else:
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Emission_Years' ][0] = '-'
                        #
                    #
                #
            #
            ###################################################################################################################################
            else:
                ###################################################################################################################################
                if int( uncertainty_table.loc[ p ,'X_Num'] ) not in X_Num_unique:
                    #
                    X_Num_unique.append( int( uncertainty_table.loc[ p ,'X_Num'] ) )
                    #
                    if math_type in ['Time_Series', 'Discrete_Investments', 'Mult_Adoption_Curve', 'Mult_Restriction', 'Mult_Restriction_Start', 'Mult_Restriction_End', 'Timeslices_Curve', 'Constant', 'Logistic', 'Linear', 'Step']:
                        # if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'YES':
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] = this_future_X_change[-1]
                        # elif str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'NO':
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] = this_future_X_param[-1]
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] = this_future_X_change[-1]
                        # if this_min_year != '-' and this_max_year != '-':
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Emission_Years' ][0] = int(round(this_future_X_change_year[-1],0)) # here n=0
                        # else:
                        #     experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Emission_Years' ][0] = '-'
                    #

                u = int( uncertainty_table.loc[ p ,'X_Num'] )
                print(u, len(experiment_dictionary[u].keys()),
                      experiment_dictionary[u]['Category'],
                      # len([i for i in experiment_dictionary[u]['Values'] if float(i) != 0.0])
                      )
    # Diccionario con tabla de incertidumbre con N valores
    #print(experiment_dictionary)
    #sys.exit()
    
    '''''
    ################################# PART 2 #################################
    '''''
    print('2: That is done. Now I initialize some key structural data.')
    '''
    # 2.B) We finish this sub-part, and proceed to read all the base scenarios.
    '''
    header_row = ['PARAMETER','Scenario','REGION','TECHNOLOGY','COMMODITY','EMISSION','MODE_OF_OPERATION','TIMESLICE','YEAR','SEASON','DAYTYPE','DAILYTIMEBRACKET','STORAGE','STORAGEINTRADAY','STORAGEINTRAYEAR','UDC','Value']
    #
    scenario_list = []
    # if scenarios_to_reproduce == 'All':
    #     stable_scenario_list_raw = os.listdir( '1_Baseline_Modelling' )
    #     for n in range( len( stable_scenario_list_raw ) ):
    #         if stable_scenario_list_raw[n] not in ['_Base_Dataset', '_BACKUP'] and '.txt' not in stable_scenario_list_raw[n]:
    #             scenario_list.append( stable_scenario_list_raw[n] )
    if scenarios_to_reproduce == 'Experiment':
        # Get the directory of the current script
        current_script_path = os.path.dirname(os.path.abspath(__file__))
        # Construct the full path to the Excel file, relative to the script's directory
        dir_executables = os.path.join(current_script_path, 'Executables')
        scenario_list = [f.replace('_0', '') for f in os.listdir(dir_executables) if not (f.endswith('.py') or f.endswith('.csv') or f.endswith('__pycache__'))]
    elif scenarios_to_reproduce != 'All' and scenarios_to_reproduce != 'Experiment':
        scenario_list.append( scenarios_to_reproduce )
    #                   
    # This section reads a reference data from executables and frames Structure-OSEMOSYS.xlsx

    # Define the dictionary for calibrated database:
    stable_scenarios = {}
    dict_special_sets = {}
    dict_rows = {}
    dict_S_DICT_params_structure = {}
    dict_S_DICT_sets_structure = {}
    dict_parameters_without_values = {}
    dict_parameters_in_the_model = {}
    for scen in scenario_list:
        stable_scenarios.update( { scen.replace('_0',''):{} } )
    #
    for scen in range( len( scenario_list ) ):
        #
        # Read executable files
        # Isolate params in subfiles
        if scenario_list[scen] != "__pycache__" and not scenario_list[scen].endswith('.csv'):
            scen_file = os.path.join(dir_executables, scenario_list[scen] + '_0/', scenario_list[scen] + '_0.txt')
        data_per_param, special_sets = AUX.isolate_params(scen_file)
        dict_special_sets[scenario_list[scen]] = special_sets
        
        # Create an empty list to store the rows
        rows = []
        
        # Iterate through each key and list in the dictionary
        for key, lines in data_per_param.items():
            if not lines:
                continue  # Skip if the list is empty
        
            first_line = lines[0]
            
            # Example: "param AccumulatedAnnualDemand default 0 :="
            parts = first_line.strip().split()
        
            try:
                # Find "param" and "default" positions
                param_index = parts.index("param") + 1
                default_index = parts.index("default") + 1
        
                parameter = parts[param_index]
                default_value = parts[default_index]
        
                rows.append({"Parameter": parameter, "Default_Value": default_value})
            
            except (ValueError, IndexError):
                # Skip if format is incorrect
                continue
        dict_rows[scenario_list[scen]] = pd.DataFrame(rows)
        
        num_time_slices_SDP = int( setup_table.loc[ 0 ,'Timeslices_model'] )
        
        # Generate CSV parameters files for each scenario
        list_dataframes, dict_dataframes, parameters_without_values = AUX.generate_df_per_param(scenario_list[scen], 
                                            data_per_param,
                                            num_time_slices_SDP)
        
        parameters_without_values.sort()
        dict_parameters_without_values[scenario_list[scen]] = parameters_without_values
        parameters_in_the_model = list(dict_dataframes.keys())
        dict_parameters_in_the_model[scenario_list[scen]] = parameters_in_the_model
        #
        # sys.exit()
        # for param in parameters_to_print_stable:
        for param in parameters_in_the_model:
            stable_scenarios[ scenario_list[scen] ].update( { param:{} } )
            # To extract the parameter input data:
            all_params_list_index = S_DICT_params_structure['parameter'].index(param)
            this_number_of_elements = S_DICT_params_structure['number_of_elements'][all_params_list_index]
            this_index_list = S_DICT_params_structure['index_list'][all_params_list_index]
            #
            for k in range(this_number_of_elements):
                stable_scenarios[ scenario_list[scen] ][ param ].update({this_index_list[k]:[]})
            stable_scenarios[ scenario_list[scen] ][ param ].update({'value':[]})
        #
        for param, value in dict_dataframes.items():            
            # Extract data:
            for index, row_df in value.iterrows():
                row = row_df.to_dict()
                row['Value'] = row.pop(param)
                if row[ header_row[-1] ] != None and row[ header_row[-1] ] != '':
                    #
                    for h in range( 2, len(header_row)-1 ):
                        if row[ header_row[h] ] != None and row[ header_row[h] ] != '':
                            set_index  = S_DICT_sets_structure['set'].index( header_row[h] )
                            set_initial = S_DICT_sets_structure['initial'][ set_index ]
                            stable_scenarios[ scenario_list[scen] ][ param ][ set_initial ].append( row[ header_row[h] ] )
                    stable_scenarios[ scenario_list[scen] ][ param ][ 'value' ].append( row[ header_row[-1] ] )
        
        dict_S_DICT_params_structure[scenario_list[scen]] = S_DICT_params_structure
        dict_S_DICT_sets_structure[scenario_list[scen]] = S_DICT_sets_structure
                    
    # sys.exit(4)
    '''
    # 2.C) We call the default parameters for later use:
    '''
    # Construct the full path to the Excel file, relative to the script's directory

    '''''
    ################################# PART 3 #################################
    '''''
    # We perturb the system that re-applies the uncertainty across parameters using the 'experiment_disctionary'
    '''
    # 3.A) We create a copy of all the scenarios
    '''
    all_futures = [n for n in range(1,N+1)]
    inherited_scenarios = {}
    for n1 in range( len( scenario_list ) ):
        inherited_scenarios.update( { scenario_list[n1]:{} } )
        #
        for n2 in range( len( all_futures ) ):
            copy_stable_dictionary = deepcopy( stable_scenarios[ scenario_list[n1] ] )
            inherited_scenarios[ scenario_list[n1] ].update( { all_futures[n2]:copy_stable_dictionary } )
    '''
    # 3.B) We iterate over the experiment dictionary for the 1 to N futures additional to future 0, implementing the orderly manipulation
    '''
    print('3: That is done. Now I systematically perturb the model parameters.')
    # Broadly speaking, we must perfrom the same calculation across futures, as all futres are independent.
    #
    # We need to store some values for some adjustments:
    spec_store_freheaele = {}
    #
    series_iguales=list()
    
    
    # Ciclo para escenarios S1, S2, S3 u otro
    for s in range( len( scenario_list ) ):
        this_s = s
        fut_id = 0
        #
        S_DICT_params_structure = dict_S_DICT_params_structure[scenario_list[s]]
        S_DICT_sets_structure = dict_S_DICT_sets_structure[scenario_list[s]]
        
        # Get timeslices list
        timeslice_index = S_DICT_sets_structure['set'].index('TIMESLICE')
        all_timeslices = S_DICT_sets_structure['elements_list'][timeslice_index]
            
        # Ciclo para futuros BAU y NDP
        for f in range( 1, len( all_futures )+1 ):
            this_f = f
            spec_store_freheaele.update({this_f:[]})
            #
            # NOTE 0: TotalDemand and Mode Shift must take the BAU SpeecifiedAnnualDemand for coherence.
            TotalDemand = []
            TotalDemand_BASE_BAU = []
            
            # if s==0:
            #     hoja_serie_especial= book.parse( 'Special_TimeSeries' )
            #     encab_series_especiales = list( hoja_serie_especial.columns )[1:]
            #     #unique_count=unique_count+1
            #     number = random.randint(encab_series_especiales[0], encab_series_especiales[len(encab_series_especiales)-1])
            #     series_iguales.append(list(hoja_serie_especial[number]))
            
            # Ciclo para las incertidumbres
            for u in range( 1, len(experiment_dictionary)+1 ):

                #######################################################################
                # DEPENDENCY CHECK: If previous row (u-1) has Dependency_Flag=YES,
                # then THIS row (u) is the dependent row. We skip normal interpolation
                # and instead compute values to preserve the additive constraint:
                #   new_dep(t) = baseline_dep(t) + (new_primary(t) - baseline_primary(t))
                #######################################################################
                if u > 1:
                    prev_dep_flag = str(experiment_dictionary[u-1].get('Dependency_Flag', 'NO')).strip().upper()
                    if prev_dep_flag in ['YES', 'SI']:
                        # This row (u) is DEPENDENT on row (u-1)
                        dep_info = experiment_dictionary[u]
                        pri_info = experiment_dictionary[u-1]

                        dep_scenarios = dep_info['Involved_Scenarios']
                        if str(scenario_list[s]) not in dep_scenarios:
                            continue

                        dep_params = dep_info['Exact_Parameters_Involved_in_Osemosys']
                        dep_first_sets = deepcopy(dep_info['Involved_First_Sets_in_Osemosys'])
                        dep_second_sets = dep_info.get('Involved_Second_Sets_in_Osemosys', [])
                        dep_third_sets = dep_info.get('Involved_Third_Sets_in_Osemosys', [])
                        pri_params = pri_info['Exact_Parameters_Involved_in_Osemosys']
                        pri_first_sets = deepcopy(pri_info['Involved_First_Sets_in_Osemosys'])
                        pri_second_sets = pri_info.get('Involved_Second_Sets_in_Osemosys', [])
                        pri_third_sets = pri_info.get('Involved_Third_Sets_in_Osemosys', [])

                        round_dep = 10

                        for p_idx in range(len(dep_params)):
                            dep_parameter = dep_params[p_idx]
                            pri_parameter = pri_params[min(p_idx, len(pri_params)-1)]

                            number_sets_dep = df_Params_Sets_Vari.loc['Number', dep_parameter]

                            # --- 1-set case ---
                            if number_sets_dep == 1:
                                set1_dep = df_Params_Sets_Vari.loc['Set1', dep_parameter]
                                tsfirst_dep = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set1_dep)]

                                set1_pri = df_Params_Sets_Vari.loc['Set1', pri_parameter]
                                tsfirst_pri = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set1_pri)]

                                for f_set_dep in range(len(dep_first_sets)):
                                    this_set_dep = dep_first_sets[f_set_dep]
                                    dep_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][dep_parameter][tsfirst_dep]) if x == str(this_set_dep)]
                                    if not dep_indices:
                                        continue
                                    dep_indices.sort()

                                    # Read dependent baseline from stable_scenarios
                                    dep_baseline = [float(v) for v in stable_scenarios[scenario_list[s]][dep_parameter]['value'][dep_indices[0]:dep_indices[-1]+1]]

                                    # Read primary's indices (use first primary set for delta)
                                    pri_set = pri_first_sets[min(f_set_dep, len(pri_first_sets)-1)]
                                    pri_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][pri_parameter][tsfirst_pri]) if x == str(pri_set)]
                                    if not pri_indices:
                                        continue
                                    pri_indices.sort()

                                    # Primary modified values (already processed by row u-1)
                                    pri_new = [float(v) for v in inherited_scenarios[scenario_list[s]][f][pri_parameter]['value'][pri_indices[0]:pri_indices[-1]+1]]
                                    # Primary baseline from stable_scenarios
                                    pri_baseline = [float(v) for v in stable_scenarios[scenario_list[s]][pri_parameter]['value'][pri_indices[0]:pri_indices[-1]+1]]

                                    # Apply additive constraint: same delta as primary
                                    n_vals = min(len(dep_baseline), len(pri_baseline))
                                    new_dep_values = [
                                        round(dep_baseline[i] + (pri_new[i] - pri_baseline[i]), round_dep)
                                        for i in range(n_vals)
                                    ]

                                    inherited_scenarios[scenario_list[s]][f][dep_parameter]['value'][dep_indices[0]:dep_indices[0]+n_vals] = deepcopy(new_dep_values)

                            # --- 2-set case ---
                            elif number_sets_dep == 2:
                                set1_dep = df_Params_Sets_Vari.loc['Set1', dep_parameter]
                                set2_dep = df_Params_Sets_Vari.loc['Set2', dep_parameter]
                                tsfirst_dep = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set1_dep)]
                                tssecond_dep = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set2_dep)]

                                set1_pri = df_Params_Sets_Vari.loc['Set1', pri_parameter]
                                set2_pri = df_Params_Sets_Vari.loc['Set2', pri_parameter]
                                tsfirst_pri = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set1_pri)]
                                tssecond_pri = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set2_pri)]

                                for f_set_dep in range(len(dep_first_sets)):
                                    this_set_first_dep = dep_first_sets[f_set_dep]
                                    dep_indices_first = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][dep_parameter][tsfirst_dep]) if x == str(this_set_first_dep)]

                                    dep_second_sets_iter = dep_second_sets if dep_second_sets else ['']
                                    for s_set_dep in range(len(dep_second_sets_iter)):
                                        this_set_second_dep = dep_second_sets_iter[s_set_dep]
                                        dep_indices_second = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][dep_parameter][tssecond_dep]) if x == str(this_set_second_dep)]

                                        dep_indices = sorted(set(dep_indices_first) & set(dep_indices_second))
                                        if not dep_indices:
                                            continue

                                        dep_baseline = [float(v) for v in stable_scenarios[scenario_list[s]][dep_parameter]['value'][dep_indices[0]:dep_indices[-1]+1]]

                                        # Primary indices
                                        pri_set_first = pri_first_sets[min(f_set_dep, len(pri_first_sets)-1)]
                                        pri_indices_first = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][pri_parameter][tsfirst_pri]) if x == str(pri_set_first)]

                                        pri_second_sets_iter = pri_second_sets if pri_second_sets else ['']
                                        pri_set_second = pri_second_sets_iter[min(s_set_dep, len(pri_second_sets_iter)-1)]
                                        pri_indices_second = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][pri_parameter][tssecond_pri]) if x == str(pri_set_second)]

                                        pri_indices = sorted(set(pri_indices_first) & set(pri_indices_second))
                                        if not pri_indices:
                                            continue

                                        pri_new = [float(v) for v in inherited_scenarios[scenario_list[s]][f][pri_parameter]['value'][pri_indices[0]:pri_indices[-1]+1]]
                                        pri_baseline = [float(v) for v in stable_scenarios[scenario_list[s]][pri_parameter]['value'][pri_indices[0]:pri_indices[-1]+1]]

                                        n_vals = min(len(dep_baseline), len(pri_baseline))
                                        new_dep_values = [
                                            round(dep_baseline[i] + (pri_new[i] - pri_baseline[i]), round_dep)
                                            for i in range(n_vals)
                                        ]

                                        inherited_scenarios[scenario_list[s]][f][dep_parameter]['value'][dep_indices[0]:dep_indices[0]+n_vals] = deepcopy(new_dep_values)

                            # --- 3-set case ---
                            elif number_sets_dep == 3:
                                set1_dep = df_Params_Sets_Vari.loc['Set1', dep_parameter]
                                set2_dep = df_Params_Sets_Vari.loc['Set2', dep_parameter]
                                set3_dep = df_Params_Sets_Vari.loc['Set3', dep_parameter]
                                tsfirst_dep = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set1_dep)]
                                tssecond_dep = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set2_dep)]
                                tsthird_dep = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set3_dep)]

                                set1_pri = df_Params_Sets_Vari.loc['Set1', pri_parameter]
                                set2_pri = df_Params_Sets_Vari.loc['Set2', pri_parameter]
                                set3_pri = df_Params_Sets_Vari.loc['Set3', pri_parameter]
                                tsfirst_pri = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set1_pri)]
                                tssecond_pri = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set2_pri)]
                                tsthird_pri = S_DICT_sets_structure['initial'][S_DICT_sets_structure['set'].index(set3_pri)]

                                for f_set_dep in range(len(dep_first_sets)):
                                    this_set_first_dep = dep_first_sets[f_set_dep]
                                    dep_indices_first = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][dep_parameter][tsfirst_dep]) if x == str(this_set_first_dep)]

                                    dep_second_sets_iter = dep_second_sets if dep_second_sets else ['']
                                    for s_set_dep in range(len(dep_second_sets_iter)):
                                        this_set_second_dep = dep_second_sets_iter[s_set_dep]
                                        dep_indices_second = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][dep_parameter][tssecond_dep]) if x == str(this_set_second_dep)]

                                        dep_third_sets_iter = dep_third_sets if dep_third_sets else ['']
                                        for t_set_dep in range(len(dep_third_sets_iter)):
                                            this_set_third_dep = dep_third_sets_iter[t_set_dep]
                                            dep_indices_third = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][dep_parameter][tsthird_dep]) if x == str(this_set_third_dep)]

                                            dep_indices = sorted(set(dep_indices_first) & set(dep_indices_second) & set(dep_indices_third))
                                            if not dep_indices:
                                                continue

                                            dep_baseline = [float(v) for v in stable_scenarios[scenario_list[s]][dep_parameter]['value'][dep_indices[0]:dep_indices[-1]+1]]

                                            # Primary indices
                                            pri_set_first = pri_first_sets[min(f_set_dep, len(pri_first_sets)-1)]
                                            pri_indices_first = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][pri_parameter][tsfirst_pri]) if x == str(pri_set_first)]

                                            pri_second_sets_iter = pri_second_sets if pri_second_sets else ['']
                                            pri_set_second = pri_second_sets_iter[min(s_set_dep, len(pri_second_sets_iter)-1)]
                                            pri_indices_second = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][pri_parameter][tssecond_pri]) if x == str(pri_set_second)]

                                            pri_third_sets_iter = pri_third_sets if pri_third_sets else ['']
                                            pri_set_third = pri_third_sets_iter[min(t_set_dep, len(pri_third_sets_iter)-1)]
                                            pri_indices_third = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][pri_parameter][tsthird_pri]) if x == str(pri_set_third)]

                                            pri_indices = sorted(set(pri_indices_first) & set(pri_indices_second) & set(pri_indices_third))
                                            if not pri_indices:
                                                continue

                                            pri_new = [float(v) for v in inherited_scenarios[scenario_list[s]][f][pri_parameter]['value'][pri_indices[0]:pri_indices[-1]+1]]
                                            pri_baseline = [float(v) for v in stable_scenarios[scenario_list[s]][pri_parameter]['value'][pri_indices[0]:pri_indices[-1]+1]]

                                            n_vals = min(len(dep_baseline), len(pri_baseline))
                                            new_dep_values = [
                                                round(dep_baseline[i] + (pri_new[i] - pri_baseline[i]), round_dep)
                                                for i in range(n_vals)
                                            ]

                                            inherited_scenarios[scenario_list[s]][f][dep_parameter]['value'][dep_indices[0]:dep_indices[0]+n_vals] = deepcopy(new_dep_values)

                        # Debug output for first future
                        if f == 1:
                            print(f"  Dependency (value-level): Row {u} dependent on Row {u-1} | Scenario {scenario_list[s]} Future {f}")

                        continue  # Skip normal interpolation for this dependent row
                #######################################################################

                Exact_X = experiment_dictionary[u]['Exact_X']
                X_Cat = experiment_dictionary[u]['Category']
                Initial_Year_of_Uncertainty = experiment_dictionary[u]['Initial_Year_of_Uncertainty']
                # Extract crucial sets and parameters to be manipulated in the model:
                Parameters_Involved = experiment_dictionary[u]['Exact_Parameters_Involved_in_Osemosys']
                First_Involved = deepcopy( experiment_dictionary[u]['Involved_First_Sets_in_Osemosys'] )
                Second_Involved = experiment_dictionary[u]['Involved_Second_Sets_in_Osemosys']
                Third_Involved = experiment_dictionary[u]['Involved_Third_Sets_in_Osemosys']
                # Emission_Involved_Involved = deepcopy( experiment_dictionary[u]['Emission_Involved'] )
                # Emission_Mode_Operations_Involved = deepcopy( experiment_dictionary[u]['Emission_Mode_Operations'] )
                # Emssion_year_0_Involved = deepcopy( experiment_dictionary[u]['Emssion_year_0'] )
                #
                Scenarios_Involved = experiment_dictionary[u]['Involved_Scenarios']
                # Extract crucial identifiers:
                Explored_Parameter_of_X = experiment_dictionary[u]['Explored_Parameter_of_X']
                Math_Type = experiment_dictionary[u]['Math_Type']
                # Relative_to_Baseline = experiment_dictionary[u]['Relative_to_Baseline']
                # Extract the values:
                Values_per_Future =  experiment_dictionary[u]['Values']
                # Emission_Years_per_Future =  experiment_dictionary[u]['Emission_Years']
                # For the manipulation, we deploy consecutive actions on the system depending on every X parameter:
                # NOTE 1: we will perform the changes in the consecutive order of the Uncertainty_Table, using distance as a final adjustment.
                # NOTE 2: we go ahead with the manipulation of the uncertainty if it is applicable to the scenario we are interested in reproducing.

                ##############################                
                ##############################
                ### Last year of the analysis
                last_year_analysis=time_range_vector[-1]
                ##############################                
                ##############################
                # Lista para asignarle a 'PWRHYDRESI' lo mismo que a 'PWRHYDRESII'
                list_in_memory=list()
                
                round_cs = 10

                if str( scenario_list[s] ) in Scenarios_Involved:
                    # We iterate over the involved parameters of the model here:
                    for p in range( len( Parameters_Involved ) ):
                        this_parameter = Parameters_Involved[p]
                        
                        # if f == 2:
                            
                        #     this_nvs_indices = [
                        #         i for i, (x, y) in enumerate(zip(inherited_scenarios[scenario_list[s]][f]['CapacityFactor']['t'],
                        #                                          inherited_scenarios[scenario_list[s]][f]['CapacityFactor']['l']))
                        #         if x == 'PWRWND016' and y == 'TS02'
                        #     ]
        
                        #     value_list = deepcopy(inherited_scenarios[scenario_list[s]][f]['CapacityFactor']['value'][this_nvs_indices[0]:this_nvs_indices[-1]+1])
                        #     print('Esta',u,X_Cat,value_list)
                        #     # if f == 10 and u == 49:
                        #         # sys.exit()
                        
                        #------------------------------------------------------------------------------------------------------------------------------------------#
                        if Math_Type in ['Time_Series', 'Constant', 'Logistic', 'Linear', 'Step'] and Explored_Parameter_of_X=='Final_Value':
                            
                            
                            
                            number_sets_by_param = df_Params_Sets_Vari.loc['Number', this_parameter]
                              
                            
                            if number_sets_by_param == 1:
                                set1_by_param = df_Params_Sets_Vari.loc['Set1', this_parameter]
                                
                                # if user select all timeslices
                                if set1_by_param == 'TIMESLICE' and any(option in First_Involved for option in ['All', 'all', 'ALL']):
                                    First_Involved = all_timeslices
                                
                                for f_set in range( len( First_Involved ) ):
                                    tsfirst = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set1_by_param) ]
                                    this_set_first = First_Involved[f_set]
                                    this_set_range_indices_first = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsfirst ] ) if x == str( this_set_first ) ]
                                    #
                                    # find elements in common
                                    this_set_range_indices = this_set_range_indices_first
                                    this_set_range_indices.sort()
                                    # for each index we extract the time and value in a list:
                                    # extracting time:
                                    time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                    # extracting value:
                                    value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                    #--------------------------------------------------------------------#
                                    if this_parameter == 'TotalTechnologyAnnualActivityLowerLimit':
                                        this_set_range_indices_upper = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ][ tsfirst ] ) if x == str( this_set_first ) ]
                                        # find elements in common
                                        this_set_range_indices_upper.sort()
                                        if this_set_range_indices_upper != []:
                                            value_list_upper = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['value'][ this_set_range_indices_upper[0]:this_set_range_indices_upper[-1]+1 ] )
                                            # Get gap between Upper and Lower Limit
                                            gap_list = [upper - lower for upper, lower in zip(value_list_upper, value_list)]
                                    #--------------------------------------------------------------------#
                                    # now that the value is extracted, we must manipulate the result and assign back
                                    if Math_Type == 'Time_Series':
                                        new_value_list = deepcopy(AUX.interpolation_non_linear_final(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                    elif Math_Type == 'Constant':
                                        new_value_list = deepcopy(AUX.interpolation_constant_trajectory(time_list, value_list, Initial_Year_of_Uncertainty))
                                    elif Math_Type == 'Linear':
                                        new_value_list = deepcopy(AUX.interpolation_linear(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                    elif Math_Type == 'Logistic':
                                        new_value_list = deepcopy(AUX.interpolation_logistic_trajectory(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                    elif Math_Type == 'Step':
                                        new_value_list = deepcopy(AUX.interpolation_step(time_list, value_list, float(Values_per_Future[fut_id]), Initial_Year_of_Uncertainty))




                                        # import matplotlib.pyplot as plt
                                        # new_value_list_constant = deepcopy(AUX.interpolation_constant_trajectory(time_list, value_list, Initial_Year_of_Uncertainty))
                                        # new_value_list_non_linear = deepcopy(AUX.interpolation_non_linear_final(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                        # new_value_list_linear = deepcopy(AUX.interpolation_linear(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                        
                                        
                                        # # Plot original vs interpolated logistic values
                                        # plt.figure(figsize=(12, 6))
                                        # plt.plot(time_list, value_list, label='Original value_list', linestyle='--', marker='o')
                                        # plt.plot(time_list, new_value_list, label='Logistic new_value_list', linestyle='-', marker='x')
                                        # plt.plot(time_list, new_value_list_constant, label='Constant new_value_list', linestyle='-', marker='x')
                                        # plt.plot(time_list, new_value_list_non_linear, label='Non linear new_value_list', linestyle='-', marker='x')
                                        # plt.plot(time_list, new_value_list_linear, label='Linear new_value_list', linestyle='-', marker='x')
                                        
                                        # # Optional vertical line to mark start of logistic behavior
                                        # plt.axvline(x=Initial_Year_of_Uncertainty, color='gray', linestyle=':', label='Start of Uncertainties')
                                        
                                        # # Plot aesthetics
                                        # plt.title(f'Comparison of trajectories to {this_parameter}/{this_set_first}')
                                        # plt.xlabel('Year')
                                        # plt.ylabel('Value')
                                        # plt.grid(True)
                                        # plt.legend()
                                        # plt.tight_layout()
                                        
                                        # plt.show()
                                        
                                        # sys.exit(34)

                                    # print('time_list=',time_list)
                                    # print('value_list=',value_list)
                                    # print('float(Values_per_Future[fut_id])=',float(Values_per_Future[fut_id]))
                                    # print('last_year_analysis=',last_year_analysis)
                                    # print('Initial_Year_of_Uncertainty=',Initial_Year_of_Uncertainty)
                                    
                                    # print('new_value_list=',new_value_list)
                                    # print('new_value_list_2=',new_value_list_2)
                                    # sys.exit(34)
                                        #
                                    new_value_list_rounded = [ round(elem, round_cs) for elem in new_value_list ]
                                    #--------------------------------------------------------------------#
                                    
                                    if this_parameter == 'TotalTechnologyAnnualActivityLowerLimit':
                                        if this_set_range_indices_upper != []:
                                            # Compute new_gap_list
                                            new_gap_list = [upper - lower for upper, lower in zip(value_list_upper, new_value_list_rounded)]
                                            
                                            # Check if there are any negative values
                                            if any(val < 0 for val in new_gap_list):
                                                # Create a corrected list by adding the original gap
                                                corrected_new_value_list = [rounded + gap for rounded, gap in zip(new_value_list_rounded, gap_list)]
                                                
                                                # Save new Upper Limit
                                                inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][
                                                    this_set_range_indices_upper[0]:this_set_range_indices_upper[-1] + 1
                                                ] = deepcopy(corrected_new_value_list)
                                    #--------------------------------------------------------------------#
                                    # Assign parameters back: for these subset of uncertainties
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                    # inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                            
                            elif number_sets_by_param == 2:
                                set1_by_param = df_Params_Sets_Vari.loc['Set1', this_parameter]
                                set2_by_param = df_Params_Sets_Vari.loc['Set2', this_parameter]
                                
                                # if user select all timeslices
                                if set1_by_param == 'TIMESLICE' and any(option in First_Involved for option in ['All', 'all', 'ALL']):
                                    First_Involved = all_timeslices
                                elif set2_by_param == 'TIMESLICE' and any(option in Second_Involved for option in ['All', 'all', 'ALL']):
                                    Second_Involved = all_timeslices
                                
                                for f_set in range( len( First_Involved ) ):
                                    tsfirst = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set1_by_param) ]
                                    this_set_first = First_Involved[f_set]
                                    this_set_range_indices_first = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsfirst ] ) if x == str( this_set_first ) ]
                                    #
                                    for s_set in range( len( Second_Involved ) ):
                                        tssecond = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set2_by_param) ]
                                        this_set_second = Second_Involved[s_set]
                                        this_set_range_indices_second = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tssecond ] ) if x == str( this_set_second ) ]
                                        #
                                        # find elements in common
                                        this_set_range_indices = list(set(this_set_range_indices_first) & set(this_set_range_indices_second))
                                        if this_set_range_indices != []:
                                            this_set_range_indices.sort()
                                            # for each index we extract the time and value in a list:
                                            # extracting time:
                                            time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                            time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                            # extracting value:
                                            value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                            value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                            #--------------------------------------------------------------------#
                                            # now that the value is extracted, we must manipulate the result and assign back
                                            if Math_Type == 'Time_Series':
                                                new_value_list = deepcopy(AUX.interpolation_non_linear_final(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                            elif Math_Type == 'Constant':
                                                new_value_list = deepcopy(AUX.interpolation_constant_trajectory(time_list, value_list, Initial_Year_of_Uncertainty))
                                            elif Math_Type == 'Logistic':
                                                new_value_list = deepcopy(AUX.interpolation_logistic_trajectory(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                            elif Math_Type == 'Step':
                                                new_value_list = deepcopy(AUX.interpolation_step(time_list, value_list, float(Values_per_Future[fut_id]), Initial_Year_of_Uncertainty))
                                            #
                                            new_value_list_rounded = [ round(elem, round_cs) for elem in new_value_list ]
                                            #--------------------------------------------------------------------#``
                                            # Assign parameters back: for these subset of uncertainties
                                            inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                            # inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                        else:
                                            print(f'Combination of {set1_by_param}:{this_set_first} and {set2_by_param}:{this_set_second} to {this_parameter} does not have any values.')  
                                        
                            elif number_sets_by_param == 3:  
                                set1_by_param = df_Params_Sets_Vari.loc['Set1', this_parameter]
                                set2_by_param = df_Params_Sets_Vari.loc['Set2', this_parameter]
                                set3_by_param = df_Params_Sets_Vari.loc['Set3', this_parameter]
                                
                                # if user select all timeslices
                                if set1_by_param == 'TIMESLICE' and any(option in First_Involved for option in ['All', 'all', 'ALL']):
                                    First_Involved = all_timeslices
                                elif set2_by_param == 'TIMESLICE' and any(option in Second_Involved for option in ['All', 'all', 'ALL']):
                                    Second_Involved = all_timeslices
                                elif set3_by_param == 'TIMESLICE' and any(option in Third_Involved for option in ['All', 'all', 'ALL']):
                                    Third_Involved = all_timeslices
                                
                                for f_set in range( len( First_Involved ) ):
                                    tsfirst = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set1_by_param) ]
                                    this_set_first = First_Involved[f_set]
                                    this_set_range_indices_first = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsfirst ] ) if x == str( this_set_first ) ]
                                    #
                                    for s_set in range( len( Second_Involved ) ):
                                        tssecond = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set2_by_param) ]
                                        this_set_second = Second_Involved[s_set]
                                        this_set_range_indices_second = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tssecond ] ) if x == str( this_set_second ) ]
                                        #
                                        for t_set in range( len( Third_Involved ) ):
                                            tsthird = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set3_by_param) ]
                                            this_set_third = Third_Involved[t_set]
                                            this_set_range_indices_third = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsthird ] ) if x == str( this_set_third ) ]
                                            #
                                            # find elements in common
                                            this_set_range_indices = list(set(this_set_range_indices_first) & set(this_set_range_indices_second) & set(this_set_range_indices_third))
                                            if this_set_range_indices != []:
                                                this_set_range_indices.sort()
                                                # for each index we extract the time and value in a list:
                                                # extracting time:
                                                time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                                time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                                # extracting value:
                                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                                value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                                #--------------------------------------------------------------------#
                                                # now that the value is extracted, we must manipulate the result and assign back
                                                if Math_Type == 'Time_Series':
                                                    new_value_list = deepcopy(AUX.interpolation_non_linear_final(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                                elif Math_Type == 'Constant':
                                                    new_value_list = deepcopy(AUX.interpolation_constant_trajectory(time_list, value_list, Initial_Year_of_Uncertainty))
                                                elif Math_Type == 'Logistic':
                                                    new_value_list = deepcopy(AUX.interpolation_logistic_trajectory(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                                elif Math_Type == 'Step':
                                                    new_value_list = deepcopy(AUX.interpolation_step(time_list, value_list, float(Values_per_Future[fut_id]), Initial_Year_of_Uncertainty))
                                                #
                                                new_value_list_rounded = [ round(elem, round_cs) for elem in new_value_list ]
                                                #--------------------------------------------------------------------#``
                                                # Assign parameters back: for these subset of uncertainties
                                                inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                                # inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                            else:
                                                print(f'Combination of {set1_by_param}:{this_set_first}, {set2_by_param}:{this_set_second} and {set3_by_param}:{this_set_third} to {this_parameter} does not have any values.')                            
                                                        
                                                        
                        
                        if Math_Type=='Timeslices_Curve' and Explored_Parameter_of_X=='Change_Curve':
                            set1_by_param = df_Params_Sets_Vari.loc['Set1', this_parameter]
                            set2_by_param = df_Params_Sets_Vari.loc['Set2', this_parameter]
                            for f_set in range( len( First_Involved ) ):
                                tsfirst = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set1_by_param) ]
                                #
                                this_set_first = First_Involved[f_set]
                                # Read "shape_of_demand.xlsx"
                                df_shapes = pd.read_csv(shape_file)
                                ts_min_value = uncertainty_table.loc[uncertainty_table['X_Num'] == u, 'Min_Value'].values
                                ts_min_value = float(ts_min_value[0])
                                ts_max_value = uncertainty_table.loc[uncertainty_table['X_Num'] == u, 'Max_Value'].values
                                ts_max_value = float(ts_max_value[0])
                                
                                curve_columns = df_shapes.columns.tolist()
                                num_curves = len(curve_columns)
                                
                                # Ensure valueLHS is within the defined range
                                valueLHS = max(min(Values_per_Future[0], ts_max_value), ts_min_value)
                                
                                # Calculate the width of each interval
                                interval_width = (ts_max_value - ts_min_value) / num_curves
                                
                                # Determine which interval valueLHS falls into
                                selected_index = int((valueLHS - ts_min_value) / interval_width)
                                
                                # Handle edge case when valueLHS == tsMaxValue
                                if selected_index == num_curves:
                                    selected_index -= 1
                                
                                # Get the name and data of the selected curve
                                selected_curve_name = curve_columns[selected_index]
                                selected_curve = df_shapes[selected_curve_name].tolist()
                                
                                # if user select all timeslices
                                if any(option in Second_Involved for option in ['All', 'all', 'ALL']):
                                    Second_Involved = all_timeslices
                                
                                if this_parameter == 'SpecifiedDemandProfile':
                                    for s_set in range( len( Second_Involved ) ):
                                        #
                                        this_set_second = Second_Involved[s_set]
                                        #
                                        tssecond = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set2_by_param) ]
                                        this_set_range_indices_fuel = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsfirst ] ) if x == str( this_set_first ) ]
                                        this_set_range_indices_ts = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tssecond ] ) if x == str( this_set_second ) ]
                                        
                                        # find elements in common
                                        this_set_range_indices = list(set(this_set_range_indices_fuel) & set(this_set_range_indices_ts))
                                        this_set_range_indices.sort()
                                        # for each index we extract the time and value in a list:
                                        # extracting time:
                                        time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                        # extracting value:
                                        value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                        #--------------------------------------------------------------------#
                                        # now that the value is extracted, we must manipulate the result and assign back
                                        new_value_list = [selected_curve[int(all_timeslices.index(this_set_second)) - 1]] * len(value_list)

                                        
                                        
                                        # new_value_list = selected_curve
                                        
                                        # # Adjust new_value_list to match the length of value_list
                                        # original_length = len(value_list)
                                        # new_length = len(new_value_list)
                                        
                                        # if new_length > original_length:
                                        #     # Trim the list if it has too many elements
                                        #     new_value_list = new_value_list[:original_length]
                                        #     print(f"Warning: new_value_list had more elements than value_list. Extra values were removed. For demand shape select.")
                                        # elif new_length < original_length:
                                        #     # Extend the list by repeating the last element
                                        #     if new_value_list:  # Ensure it's not empty
                                        #         last_value = new_value_list[-1]
                                        #         new_value_list += [last_value] * (original_length - new_length)
                                        #         print(f"Warning: new_value_list had fewer elements than value_list. Last value was repeated to match length. For demand shape select.")
                                        #     else:
                                        #         print("Warning: new_value_list is empty and cannot be extended. For demand shape select.")

                                    
                                        #
                                        new_value_list_rounded = [ round(elem, round_cs) for elem in new_value_list ]
                                        #--------------------------------------------------------------------#``
                                        # Assign parameters back: for these subset of uncertainties
                                        inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                        # inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                
                        # if Math_Type=='Time_Series' and Explored_Parameter_of_X=='Emission_Curve':
                        #     set1_by_param = df_Params_Sets_Vari.loc['Set1', this_parameter]
                        #     set2_by_param = df_Params_Sets_Vari.loc['Set2', this_parameter]
                        #     set3_by_param = df_Params_Sets_Vari.loc['Set3', this_parameter]
                            
                        #     for f_set in range( len( First_Involved ) ):
                        #         tsfirst = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set1_by_param) ]
                        #         this_set_first = First_Involved[f_set]
                        #         this_set_range_indices_first = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsfirst ] ) if x == str( this_set_first ) ]
                        #         #
                        #         for s_set in range( len( Second_Involved ) ):
                        #             tssecond = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set2_by_param) ]
                        #             this_set_second = Second_Involved[s_set]
                        #             this_set_range_indices_second = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tssecond ] ) if x == str( this_set_second ) ]
                        #             #
                        #             for t_set in range( len( Third_Involved ) ):
                        #                 tsthird = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index(set3_by_param) ]
                        #                 this_set_third = Third_Involved[t_set]
                        #                 this_set_range_indices_third = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsthird ] ) if x == str( this_set_third ) ]
                        #                 #
                        #                 # find elements in common
                        #                 this_set_range_indices = list(set(this_set_range_indices_first) & set(this_set_range_indices_second) & set(this_set_range_indices_third))
                        #                 if this_set_range_indices != []:
                        #                     this_set_range_indices.sort()
                        #                     # for each index we extract the time and value in a list:
                        #                     # extracting time:
                        #                     time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                        #                     time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                        #                     # extracting value:
                        #                     value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                        #                     value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                        #                     #--------------------------------------------------------------------#
                                        
                                        
                                        
                        #                     #--------------------------------------------------------------------#
                        #                     # now that the value is extracted, we must manipulate the result and assign back
                        #                     new_value_list = deepcopy(AUX.interpolation_non_linear_final(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                        #                         #
                        #                     new_value_list_rounded = [ round(elem, round_cs) for elem in new_value_list ]
                        #                     #--------------------------------------------------------------------#``
                        #                     # Assign parameters back: for these subset of uncertainties
                        #                     inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                        #                     # inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                        #                 else:
                        #                     print(f'Combination of {set1_by_param}:{this_set_first}, {set2_by_param}:{this_set_second} and {set3_by_param}:{this_set_third} to {this_parameter} does not have any values.')  
                            
                        '''    
                            
                        if Math_Type=='Time_Series' and Explored_Parameter_of_X=='Multiplier':
                            for a_set in range( len( First_Involved ) ):
                                tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                #
                                this_set = First_Involved[a_set]
                            
                                if X_Cat == "Floating Solar Capacity" and this_parameter in ['TotalAnnualMaxCapacity', 'TotalAnnualMinCapacity']:
                                    
                                    if this_parameter == 'TotalAnnualMaxCapacity':
                                        this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                        this_set_range_indices2 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMinCapacity' ][ tsti ] ) if x == str( this_set ) ]
                                        # for each index we extract the time and value in a list:
                                        # extracting time:
                                        time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                        # extracting value:
                                        value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                        #--------------------------------------------------------------------#
                                        # now that the value is extracted, we must manipulate the result and assign back
                                        ####################
                                        ### Si se quisiera a partir de Initial_Year_of_Uncertainty
                                        ####################
                                        # auxiliar_list=list()
                                        # for elemento in range(len(time_list)):
                                        #     if time_list[elemento] >= Initial_Year_of_Uncertainty:
                                        #         print(time_list[elemento])
                                        #         auxiliar_list.append(value_list[elemento]*Values_per_Future[fut_id])
                                        #     else:
                                        #         auxiliar_list.append(value_list[elemento])
                                        
                                        # Asignar restriccion
                                        # max_capacity=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'] )
                                        # technology=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['t'] )
                                        # anios=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['y'] )
                                        # region=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['r'] )
                                        #############################
                                        ####### ESTO ES INNECESARIO
                                        #############################
                                        # list_aux_min_capacity=list()
                                        # list_aux_technology=list()
                                        # list_aux_anios=list()
                                        # list_aux_region=list()
                                        # for ite in range(len(technology)):
                                        #     if technology[ite] == this_set:
                                        #         list_aux_region.append(region[ite])
                                        #         list_aux_anios.append(anios[ite])
                                        #         list_aux_technology.append(technology[ite])
                                        #         list_aux_min_capacity.append(0)
                                        # for ite in range(len(list_aux_min_capacity)):
                                        #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['r'].append(list_aux_region[ite])
                                        #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['y'].append(list_aux_anios[ite])
                                        #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['t'].append(list_aux_technology[ite])
                                        #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['value'].append(list_aux_min_capacity[ite])
                                            
                                        
                                        new_value_list = [ite * float(Values_per_Future[fut_id]) for ite in value_list]
                                        new_value_list2 = [ elem*0.99 for elem in new_value_list ]
                                        #new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                        #--------------------------------------------------------------------#``
                                        # Assign parameters back: for these subset of uncertainties
                                        #inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                        inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                        inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['value'][ this_set_range_indices2[0]:this_set_range_indices2[-1]+1 ] = deepcopy(new_value_list2)
                                    
                                    else:
                                        pass
                            
                        if Math_Type=='Time_Series' and Explored_Parameter_of_X=='Special_TimeSeries':
                            # if unique_count==0:
                            #     hoja_serie_especial= book.parse( 'Special_TimeSeries' )
                            #     encab_series_especiales = list( hoja_serie_especial.columns )[1:]
                            #     unique_count=unique_count+1
                            #     number = random.randint(encab_series_especiales[0], encab_series_especiales[len(encab_series_especiales)-1])
                            #     serie_especial=list(hoja_serie_especial[number])
                                
                            for a_set in range( len( First_Involved ) ):
                                tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                #
                                this_set = First_Involved[a_set]
                                    
                                if this_parameter == 'TotalTechnologyAnnualActivityUpperLimit' and this_set == 'PWRHYDRESI':
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                    this_set_range_indices2 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == 'PWRHYDRESII' ]
                                    # for each index we extract the time and value in a list:
                                    # extracting time:
                                    time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                    # extracting value:
                                    value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                    #--------------------------------------------------------------------#
                                    # now that the value is extracted, we must manipulate the result and assign back
                                    ####################
                                    ### Si se quisiera a partir de Initial_Year_of_Uncertainty
                                    ####################
                                    # auxiliar_list=list()
                                    # for elemento in range(len(time_list)):
                                    #     if time_list[elemento] >= Initial_Year_of_Uncertainty:
                                    #         print(time_list[elemento])
                                    #         auxiliar_list.append(value_list[elemento]*Values_per_Future[fut_id])
                                    #     else:
                                    #         auxiliar_list.append(value_list[elemento])
                                    
                                    # Asignar restriccion
                                    # max_capacity=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'] )
                                    # technology=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['t'] )
                                    # anios=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['y'] )
                                    # region=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['r'] )
                                    #############################
                                    ####### ESTO ES INNECESARIO
                                    #############################
                                    # list_aux_min_capacity=list()
                                    # list_aux_technology=list()
                                    # list_aux_anios=list()
                                    # list_aux_region=list()
                                    # for ite in range(len(technology)):
                                    #     if technology[ite] == this_set:
                                    #         list_aux_region.append(region[ite])
                                    #         list_aux_anios.append(anios[ite])
                                    #         list_aux_technology.append(technology[ite])
                                    #         list_aux_min_capacity.append(0)
                                    # for ite in range(len(list_aux_min_capacity)):
                                    #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['r'].append(list_aux_region[ite])
                                    #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['y'].append(list_aux_anios[ite])
                                    #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['t'].append(list_aux_technology[ite])
                                    #     inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMinCapacity' ]['value'].append(list_aux_min_capacity[ite])
                                        
                                    
                                    #new_value_list = [ite * float(Values_per_Future[fut_id]) for ite in value_list]
                                    
                                    new_value_list = [ite1 * ite2 for ite1, ite2 in zip(value_list, series_iguales[f-1])]
                                    
                                    
                                    #new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                    #--------------------------------------------------------------------#``
                                    # Assign parameters back: for these subset of uncertainties
                                    #inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices2[0]:this_set_range_indices2[-1]+1 ] = deepcopy(new_value_list)
                                
                                elif this_parameter == 'CapacityFactor':
                                    this_timeslice_cf = CF_Timeslices_Involved[a_set]
                                    #print(this_parameter,this_set,this_commodity_eff)
                                    this_set_range_indices=list()
                                    for i in range(len(inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ])):
                                        if inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ][i] == str( this_set ) and inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 'l' ][i] == str( this_timeslice_cf ):
                                            this_set_range_indices.append(i)
                                    #print(len(this_set_range_indices))
                                    # for each index we extract the time and value in a list:
                                    # extracting time:
                                    time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                    # extracting value:
                                    value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                    #--------------------------------------------------------------------#
                                    # now that the value is extracted, we must manipulate the result and assign back
                                    #new_value_list = deepcopy(AUX.interpolation_non_linear_final(time_list, value_list, float(Values_per_Future[fut_id]), last_year_analysis, Initial_Year_of_Uncertainty))
                                    
                                    lista_auxiliar=list()
                                    for ite1 in range(len(series_iguales[f-1])):
                                        if series_iguales[f-1][ite1] == 1:
                                            lista_auxiliar.append(1)
                                        elif series_iguales[f-1][ite1] < 1:
                                            lista_auxiliar.append(Values_per_Future[fut_id])
                                        else:
                                            lista_auxiliar.append(1/Values_per_Future[fut_id])
                                            
                                            
                                    new_value_list = [ite1 * ite2 for ite1, ite2 in zip(value_list, lista_auxiliar)]
                                        #
                                    #new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                    #--------------------------------------------------------------------#``
                                    # Assign parameters back: for these subset of uncertainties
                                    #inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                #--------------------------------------------------------------------#
                            #--------------------------------------------------------------------#
                        '''
                        #--------------------------------------------------------------------#
                    #--------------------------------------------------------------------#
            fut_id += 1

    print( '    We have finished the experiment and inheritance' )

    # =========================================================================
    # FIX: Correct UDC EV penetration coefficient signs (in-memory, pre-write)
    # =========================================================================
    # At this point, PART 3 has finished: all LHS perturbations have been
    # applied to `inherited_scenarios` in memory, but NO files have been
    # written yet (pickle serialization and .txt generation happen below).
    #
    # Some perturbations may have flipped the sign of UDC coefficients
    # (e.g., a diesel coefficient going from -0.02 to +0.0005), which
    # makes the EV penetration cap constraint mathematically infeasible.
    #
    # We fix the signs here, so the corrected values flow into pickle
    # serialization (below) and .txt file generation (PART 4).
    # =========================================================================
    current_script_path_fix = os.path.dirname(os.path.abspath(__file__))
    udc_log_dir = os.path.join(current_script_path_fix, 'Experimental_Platform', 'Logs', 'UDC_Corrections')
    if ev_config_is_empty:
        udc_corrections = {}
    else:
        udc_corrections = fix_udc_ev_penetration_coefficients(
            inherited_scenarios, scenario_list, all_futures,
            ev_udcs=ev_udcs,
            conventional_patterns=conv_patterns,
            electric_pattern=elec_pattern,
            log_dir=udc_log_dir
        )
    # =========================================================================

    #
    time_list = []
    #
    # scenario_list_print = scenario_list
    scenario_list_print = [scen for scen in scenario_list if scen != '__pycache__']

    # Before printing the experiment dictionary, be sure to add future 0:
    experiment_dictionary[1]['Futures'] = [0] + experiment_dictionary[1]['Futures']
    experiment_dictionary[1]['Values'] = [3] + experiment_dictionary[1]['Values']

    # Save the dictionary in chunks by scenario and future into Pickle files
    directory_path = "data_inherited_scenarios"
    max_x_per_iter = int(setup_table.loc[0, 'Parallel_Use'])  # Get the number of scenarios per file
    items = list(inherited_scenarios.items())  # Convert inherited_scenarios to a list of items (scenarios)
    total_items = len(items)  # Get the total number of items (scenarios)
    num_files = math.ceil(total_items / max_x_per_iter)  # Calculate the number of files needed
    
    # Iterate through the chunks of scenarios and save each part into a separate file
    for idx in range(num_files):
        start_idx = idx * max_x_per_iter  # Calculate the start index for the chunk of scenarios
        end_idx = min(start_idx + max_x_per_iter, total_items)  # Calculate the end index for the chunk of scenarios
        chunk = dict(items[start_idx:end_idx])  # Create a chunk of the dictionary for the scenarios
        
        # Now we separate each scenario into its futures and save them
        for scenario, futures_dict in chunk.items():  # Iterate over each scenario
            # Convert futures_dict into items (futures)
            items_2 = list(futures_dict.items())  # Convert the futures of each scenario into a list of items
            total_futures = len(items_2)  # Get the total number of futures
            num_futures_files = math.ceil(total_futures / max_x_per_iter)  # Calculate how many files are needed for futures
            
            # Iterate through the chunks of futures for this scenario and save each part into a separate file
            for f_idx in range(num_futures_files):
                start_f_idx = f_idx * max_x_per_iter  # Calculate the start index for the chunk of futures
                end_f_idx = min(start_f_idx + max_x_per_iter, total_futures)  # Calculate the end index for the chunk of futures
                futures_chunk = {scenario:dict(items_2[start_f_idx:end_f_idx])}  # Create a chunk of the dictionary for the futures
                
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)
                    print(f"Directory created: {directory_path}")
                # Save the chunk of futures into a Pickle file
                file_name = f"data_inherited_scenarios/{scenario}_futures_part_{f_idx + 1}.pkl"  # Define the file name with the scenario and future part
                with open(file_name, 'wb') as f:
                    pickle.dump(futures_chunk, f)  # Save the futures chunk into the file
                print(f"Saved: {file_name}")

    # Empty the original dictionary to free memory
    inherited_scenarios.clear()  # Clear the original dictionary to free memory
    print("The 'inherited_scenarios' dictionary has been cleared.")
               

    if generator_or_executor == 'Generator' or generator_or_executor == 'Both':
        print('4: We will now print the input .txt files of diverse future scenarios.')
    
        print_adress = './Experimental_Platform/Futures/'
    
        
    
        if parallel_or_linear == 'Parallel':
            print('Entered Parallelization')
            
            for fut_id_new in range(len(scenario_list_print)):
                # Collect the elements needed for parallelization
                # Create a DataFrame
                list_param_default_value = pd.DataFrame(dict_rows[scenario_list[fut_id_new]])
                S_DICT_params_structure = dict_S_DICT_params_structure[scenario_list[fut_id_new]]
                S_DICT_sets_structure = dict_S_DICT_sets_structure[scenario_list[fut_id_new]]
                packaged_useful_elements = [scenario_list_print, S_DICT_sets_structure, S_DICT_params_structure,
                                            list_param_default_value,
                                            print_adress, all_futures, time_range_vector,dict_parameters_in_the_model[scenario_list_print[fut_id_new]],
                                            dict_parameters_without_values[scenario_list_print[fut_id_new]], dict_special_sets[scenario_list_print[fut_id_new]]]
                
                # x = len(all_futures) * len(scenario_list_print)
                x = len(all_futures)
                max_x_per_iter = int(setup_table.loc[0, 'Parallel_Use'])  # Number of futures per file
                y = x / max_x_per_iter
                y_ceil = math.ceil(y)
        
                # Iterate over the chunks based on the number of scenarios
                for n in range(0, y_ceil):
                    n_ini = n * max_x_per_iter  # Start index for each chunk
                    processes = []
                    start1 = time.time()
        
                    if n_ini + max_x_per_iter <= x:
                        max_iter = n_ini + max_x_per_iter
                    else:
                        max_iter = x
        
                    # Process each future within the current chunk
                    for n2 in range(n_ini, max_iter):
                        
                        # let's apply the filter here for faster results:
                        fut_index = n2
                        if fut_index < len( all_futures ):
                            fut = all_futures[fut_index]
                            scen = 0
                        if fut_index >= len( all_futures ) and fut_index < 2*len( all_futures ):
                            fut = all_futures[fut_index - len( all_futures ) ]
                            scen = 1
                        if fut_index >= 2*len( all_futures ) and fut_index < 3*len( all_futures ):
                            fut = all_futures[fut_index - 2*len( all_futures ) ]
                            scen = 2
                        if fut_index >= 3*len( all_futures ) and fut_index < 4*len( all_futures ):
                            fut = all_futures[fut_index - 3*len( all_futures ) ]
                            scen = 3
                        if fut_index >= 4*len( all_futures ) and fut_index < 5*len( all_futures ):
                            fut = all_futures[fut_index - 4*len( all_futures ) ]
                            scen = 4
                        if fut_index >= 5*len( all_futures ) and fut_index < 6*len( all_futures ):
                            fut = all_futures[fut_index - 5*len( all_futures ) ]
                            scen = 5
                        if fut_index >= 6*len( all_futures ):
                            fut = all_futures[fut_index - 6*len( all_futures ) ]
                            scen = 6
                        #
                        fut = all_futures[fut_index - scen*len( all_futures ) ]
        
                        # Load the appropriate chunk of the 'inherited_scenarios' based on scenario and future
                        file_name = f"data_inherited_scenarios/{scenario_list_print[fut_id_new]}_futures_part_{(fut_index // max_x_per_iter) + 1}.pkl"
                        # print(scenario_list_print[fut_id_new],fut_index,max_x_per_iter)
                        with open(file_name, 'rb') as f:
                            inherited_scenarios = pickle.load(f)  # Load the required part of the scenarios and futures
        
                        # Call the function to process each future and scenario
                        if scenario_list_print[fut_id_new] in scenario_list:
                            # synthesized_all_data_row = function_C_mathprog_parallel(n2, inherited_scenarios, packaged_useful_elements, num_time_slices_SDP)
                            # sys.exit(6)
                            p = mp.Process(target=function_C_mathprog_parallel, args=(n2, fut_id_new, inherited_scenarios, packaged_useful_elements, num_time_slices_SDP))
                            processes.append(p)
                            p.start()
                        else:
                            print(f'!!! At generation, we skip: future {fut} and scenario {scenario_list[fut_id_new]} !!!')
        
                    # Wait for all processes to finish
                    for process in processes:
                        process.join()
        
                    end_1 = time.time()
                    time_elapsed_1 = end_1 - start1
                    print(f"Time elapsed for chunk {n+1}: {time_elapsed_1} seconds")
                    time_list.append(time_elapsed_1)
    
            print(f"The total time for printing input .txt files: {sum(time_list)} seconds")
    
        if parallel_or_linear == 'Linear':
            print('Started Linear Runs')
            for fut_id_new in range(len(scenario_list_print)):
                x = len(all_futures)# * len(scenario_list_print)
                for n in range(x):
                    function_C_mathprog_parallel(n, fut_id_new, inherited_scenarios, packaged_useful_elements, num_time_slices_SDP)


        '''
        ##########################################################################
        '''

        # --- Generate consolidated Energy_Input.csv after all txt files ---
        print('Generating consolidated OSEMOSYS Energy Input CSV...')

        dir_executables_path = os.path.join(current_script_path, 'Executables')
        dir_futures_path = os.path.join(current_script_path, 'Experimental_Platform', 'Futures')

        local_dataset_creator_0.execute_local_dataset_creator_0_inputs(dir_executables_path)
        local_dataset_creator_f.execute_local_dataset_creator_f_inputs(dir_futures_path)

        # Read aggregated baseline inputs
        input_dataset_0_path = os.path.join(dir_executables_path, 'input_dataset_0.csv')
        df_0_input = pd.read_csv(input_dataset_0_path, index_col=None, header=0, low_memory=False)
        df_0_input['Scen_fut'] = df_0_input['Strategy'].astype(str) + "_" + df_0_input['Future.ID'].astype(str)

        # Read aggregated futures inputs
        input_dataset_f_path = os.path.join(dir_futures_path, 'input_dataset_f.parquet')
        df_f_input = pd.read_parquet(input_dataset_f_path, engine='pyarrow')

        # Concatenate
        df_input = pd.concat([df_0_input, df_f_input], axis=0, ignore_index=True)

        # Clean YEAR column
        df_input['YEAR'] = pd.to_numeric(df_input['YEAR'], errors='coerce')
        df_input['YEAR'] = df_input['YEAR'].fillna(0)
        df_input['YEAR'] = df_input['YEAR'].astype(int)

        # Sort
        df_input.sort_values(by=[
            'Strategy', 'Future.ID', 'REGION', 'COMMODITY', 'TECHNOLOGY', 'EMISSION',
            'YEAR', 'TIMESLICE', 'MODE_OF_OPERATION', 'SEASON', 'DAYTYPE',
            'DAILYTIMEBRACKET', 'STORAGE', 'STORAGEINTRADAY', 'STORAGEINTRAYEAR', 'UDC'
        ], inplace=True)

        # Create Results folder if needed
        if not os.path.exists('Results'):
            os.makedirs('Results')
            print("Folder 'Results' created.")

        # Save
        input_csv_path = os.path.join('Results', f'OSEMOSYS_{region}_Energy_Input.csv')
        df_input.to_csv(input_csv_path, index=None, header=True)
        print(f'Energy Input CSV saved: {input_csv_path}')

    #########################################################################################
    #
    if generator_or_executor == 'Executor' or generator_or_executor == 'Both':
        #
        # Empty the original dictionary to free memory
        inherited_scenarios.clear()  # Clear the original dictionary to free memory
        print("The 'inherited_scenarios' dictionary has been cleared.")
        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            shutil.rmtree(directory_path)
            print(f"Directory deleted: {directory_path}")
        #
        print('5: We will produce the outputs and store the data.')
        #
        for a_scen in range( len( scenario_list_print ) ):
            #
            Executed_Scenario = scenario_list_print[ a_scen ]
            set_first_list(Executed_Scenario)
            #
            x = len(first_list)
            #
            y = x / max_x_per_iter
            y_ceil = math.ceil( y )
            
            for n in range(0,y_ceil):
                print('###')
                n_ini = n*max_x_per_iter
                processes = []
                #
                start1 = time.time()
                #
                if n_ini + max_x_per_iter <= x:
                    max_iter = n_ini + max_x_per_iter
                else:
                    max_iter = x
                #
                for n2 in range( n_ini , max_iter ):

                    p = mp.Process(target=main_executer, args=(n2,Executed_Scenario,time_range_vector,scenario_list_print,solver,osemosys_model,parameters_to_print) )
                    processes.append(p)
                    p.start()
                #
                for process in processes:
                    process.join()
                #
                end_1 = time.time()   
                time_elapsed_1 = -start1 + end_1
                print( str( time_elapsed_1 ) + ' seconds' )
                time_list.append( time_elapsed_1 )
                #
            #
        #
    #
    print('   The total time producing outputs and storing data has been: ' + str( sum( time_list ) ) + ' seconds')
    '''
    ##########################################################################
    '''
    print( 'For all effects, this has been the end. It all took: ' + str( sum( time_list ) ) + ' seconds')
    