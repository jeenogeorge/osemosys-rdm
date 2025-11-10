# -*- coding: utf-8 -*-
"""
Created on Wed May  5 16:45:01 2021

@author: luisf
"""

import sys
import pandas as pd
import os
from copy import deepcopy
import prim
import time
import math
import pickle
import multiprocessing as mp
import yaml
from pathlib import Path
# Follow: https://www.python.org/dev/peps/pep-0008/
# Reminder 1:
# https://stackoverflow.com/questions/24251219/pandas-read-csv-low-memory-and-dtype-options

''' ///////////////////////////////////////////////////////////////////
Function 1 (f1): open the files from the indicated directory and
execute the post-processing functions. '''


def f1_create_prim_files(dir_elements, dirl, scen, dict_pfcp, analysis_list,
                         dict_set_matching, period_control, all_exp_data,
                         exp_id, params, dicPop):
    '''
    Reviewing the inputs:
        scen: indicates what scenario is being analyzed
        dirl: location of inputs and outputs of functions
        dir_elements: list of all inputs inside dirl (not clean)
        prim_files_creator_parallel: controls output creation}
    Steps:
        0) Define the outputs for this function
        1) Clean the file lists from *dir_elements*
        2) Create clean access directories for each element of interest
        3) Begin the post-processing instructions workflow
        4) Populate the outcomes of this function
        5) Print the dataframes as .csv for subsequent control
    '''
    # We process the timeframe structures:
    period_list = period_control['period_list']
    yr_ini_list = period_control['yr_ini']
    yr_fin_list = period_control['yr_fin']

    whole_per_index = period_list.index('all')
    whole_per_yr_ini = yr_ini_list[whole_per_index]
    whole_per_yr_fin = yr_fin_list[whole_per_index]

    del period_list[whole_per_index]
    del yr_ini_list[whole_per_index]
    del yr_fin_list[whole_per_index]

    whole_period = [y for y in range(whole_per_yr_ini, whole_per_yr_fin+1)]

    # # Extract future according to directory:
    # future = int([e.replace('.txt', '').split('_')[1] for e
    #              in dir_elements if 'txt' in e.lower()][0])}
    # Extract future according to directory:
    # print(dir_elements)
    # future = int([e.replace('.csv', '').split('_')[1] for e
    #              in dir_elements if 'csv' in e.lower()][0])
    # Define valid file extensions we care about
    valid_ext = ('.csv', '.parquet')
    
    # Filter only files that end with .csv or .parquet (case insensitive)
    valid_files = [f for f in dir_elements if Path(f).suffix.lower() in valid_ext]
    
    if valid_files:
        # Take the first matching file
        file_name = Path(valid_files[0]).stem  # file name without extension
    
        # Split the file name into parts (e.g., 'Scenario1_10_Input' → ['Scenario1', '10', 'Input'])
        parts = file_name.split('_')
    
        # Extract the first numeric part and convert it to integer
        future = next((int(p) for p in parts if p.isdigit()), None)
    # print(future)
    # sys.exit()

    # PRINT STATUS:
    print('\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    print('Status ==> Reading files once ' + '// Scenario: ' + str(scen) +
          ' // Future: ' + str(future))

    # For efficiency, open all pandas dataframes and store for later use:
    elmnt_input = [e for e in dir_elements if params['input'] in e.lower()]
    elmnt_output = [e for e in dir_elements if params['output'] in e.lower()]
    elmnt_tem = [e for e in dir_elements if params['tem'] in e.lower() and
                params['gini'] not in e.lower() and params['reg'] not in e.lower()]
    elmnt_utem = [e for e in elmnt_tem if params['upg'] in e.lower()]
    elmnt_regtem = [e for e in elmnt_tem if params['upg'] not in e.lower()]
    elmnt_regions = [e for e in dir_elements if params['regf'] in e.lower()]

    #      Granting access to files:
    acc_input   = [os.path.join(dirl, e) for e in elmnt_input]
    acc_output  = [os.path.join(dirl, e) for e in elmnt_output]
    acc_tem     = [os.path.join(dirl, e) for e in elmnt_tem]
    acc_utem    = [os.path.join(dirl, e) for e in elmnt_utem]
    acc_regtem  = [os.path.join(dirl, e) for e in elmnt_regtem]
    acc_regions = [os.path.join(dirl, e) for e in elmnt_regions]

    #       Gathering the dtypes for the files:
    rep_fn_prim_fcc = open(params['Prim_files_crea_cntrl'], 'rb')
    dtype_dfs = pd.read_excel(rep_fn_prim_fcc, sheet_name=params['dType'])

    #           For inputs:
    use_dtype_inp = {}
    df_dtype_inp = dtype_dfs.loc[(dtype_dfs['File'] == params['ose_inputs'])]
    df_cols_inp = df_dtype_inp['Column'].tolist()
    df_types_inp = df_dtype_inp['Type'].tolist()
    for n in range(len(df_cols_inp)):
        use_dtype_inp.update({df_cols_inp[n]: df_types_inp[n]})
    df_input = []
    
    # for afile in acc_input:
    #     a_df = pd.read_csv(afile, dtype=use_dtype_inp)
    #     # We have to make some adjustments to the input file; has non-year data
    #     a_df[params['Year']] = a_df[params['Year']].fillna(0)
    #     a_df.Year = a_df.Year.astype(int)
    #     df_input.append(deepcopy(a_df))

    for afile in acc_input:
        afile_path = Path(afile)
        # Detectar extensión (minúsculas por seguridad)
        ext = afile_path.suffix.lower()
    
        if ext == '.csv':
            a_df = pd.read_csv(afile_path, dtype=use_dtype_inp,low_memory=False)
        elif ext == '.parquet':
            a_df = pd.read_parquet(afile_path)
        else:
            print(f"⚠️ Tipo de archivo no soportado: {afile_path}")
            continue  # salta al siguiente archivo
        if "_1" in str(afile_path):
            # Definir el nombre de salida (puedes personalizarlo)
            print(1111111111111111,acc_input)
            # output_path = str(afile_path).replace(".parquet", ".xlsx")
            
            # # Guardar el DataFrame como archivo Excel
            # a_df.to_excel(output_path, index=False)
        # Ajustes comunes a ambos tipos
        if params['Year'] in a_df.columns:
            a_df[params['Year']] = a_df[params['Year']].fillna(0).astype(int)
    
        df_input.append(deepcopy(a_df))

    #           For outputs:
    use_dtype_out = {}
    df_dtype_out = dtype_dfs.loc[(dtype_dfs['File'] == params['ose_oupts'])]
    df_cols_out = df_dtype_out['Column'].tolist()
    df_types_out = df_dtype_out['Type'].tolist()
    for n in range(len(df_cols_out)):
        use_dtype_out.update({df_cols_out[n]: df_types_out[n]})
    # df_output = [pd.read_csv(afile, dtype=use_dtype_out) for afile in
    #              acc_output]
    
    df_output = []
    for f in acc_output:
        try:
            file_path = Path(f)
            ext = file_path.suffix.lower()
        
            if ext == '.csv':
                df = pd.read_csv(file_path, dtype=use_dtype_out)
            elif ext == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                raise ValueError(f"❌ Tipo de archivo no soportado: {ext}")
            
            if params['Year'] in df.columns:
                df[params['Year']] = df[params['Year']].fillna(0).astype(int)

            df_output.append(df)
        except Exception as e:
            print(f"⚠️ Error al leer {f}: {e}")


    #           For TEM:
    use_dtype_tem = {}
    df_dtype_tem = dtype_dfs.loc[(dtype_dfs['File'] == params['tem_out'])]
    df_cols_tem = df_dtype_tem['Column'].tolist()
    df_types_tem = df_dtype_tem['Type'].tolist()
    for n in range(len(df_cols_tem)):
        use_dtype_tem.update({df_cols_tem[n]: df_types_tem[n]})
    df_tem = [pd.read_csv(afile, dtype=use_dtype_tem) for afile in acc_tem]
    df_utem = [pd.read_csv(afile, dtype=use_dtype_tem) for afile in acc_utem]
    df_regtem = [pd.read_csv(afile, dtype=use_dtype_tem) for afile in
                 acc_regtem]

    #           For Region:
    use_dtype_region = {}
    df_dtype_region = dtype_dfs.loc[(dtype_dfs['File'] == params['tem_reg'])]
    df_cols_region = df_dtype_region['Column'].tolist()
    df_types_region = df_dtype_region['Type'].tolist()
    for n in range(len(df_cols_region)):
        use_dtype_region.update({df_cols_region[n]: df_types_region[n]})
    df_region = [pd.read_csv(afile, dtype=use_dtype_region)
                 for afile in acc_regions]

    # Storing the list of dataframes to be used below // df_'s are lists:
    list_acc_files = [acc_input, acc_output, acc_tem, acc_utem, acc_regtem,
                      acc_regions]
    list_dfs = [df_input, df_output, df_tem, df_utem, df_regtem, df_region]

    if len(analysis_list) == 0:
        print('Experiment ' + str(exp_id) + ' does not have an assigned' +
              'Analysis; its runs will not be processed.')

    # Select the experiment data:
    exp_data = all_exp_data[exp_id]

    # Proceed iterating across the desired analyses.
    for a in range(len(analysis_list)):
        prim_files_creator_parallel = dict_pfcp[analysis_list[a]]

        df_prim_set_matching = dict_set_matching[analysis_list[a]]
        ana_ID = analysis_list[a]

        # Open the BAU pickle if we are not in the NDP scenario:
        if scen != params['BAU']:
            apply_suffix = '_' + params['BAU'] + '_' + str(future) + '_' + str(ana_ID)
            dirl_bau = dirl.replace(scen, params['BAU'])
            fn_pfd_bau = dirl_bau + '/pfd' + apply_suffix + '.pickle'
            file_pfd_bau = open(fn_pfd_bau, 'rb')
            pfd_bau = pickle.load(file_pfd_bau)
            file_pfd_bau.close()

        # OBJECTIVE: we need to define i) an empty dataframe for each ID table,
        #           per period; ii) the dictionary that stores each PRIM table
        pfd = {}  # this dictionary stores every PRIM table
        pfd.update({'o': {}})  # outcome
        pfd.update({'d': {}})  # driver // be sure to store the unique only

        # OBJECTIVE: unpack and iterate across *prim_files_creator_parallel*
        prim_fc_p_o = prim_files_creator_parallel['Outcome']
        prim_fc_p_d = prim_files_creator_parallel['Driver_U']
        # picking *Driver_U* reduces execution time

        # Both internal dictionaries have the same IDs for iteration
        #   These IDs are an indication of the tables that need to be created
        outcome_ID_list = list(prim_files_creator_parallel['Outcome'].keys())
        outcome_ID_list.sort()
        udriver_ID_list = list(prim_files_creator_parallel['Driver_U'].keys())
        udriver_ID_list.sort()

        #   This is an ID applicable for outcomes (o):
        for i in outcome_ID_list:
            # PRINT STATUS:
            print('Status => Done reading files. // Analysis ID: '
                  + str(ana_ID) + ' // Table ID: ' + str(i) +
                  ' // Scenario: ' + str(scen) + ' // Future: '
                  + str(future))

            # Select the BAU pickle if we are not in the NDP scenario:
            if scen != params['BAU']:
                prim_tbl_o_bau = pfd_bau['o'][i]
                prim_tbl_d_bau = 'none'
            else:
                prim_tbl_o_bau, prim_tbl_d_bau = 'none', 'none'

            # Creating an empty dict for table of ID i and period y:
            prim_tbl_o = {}
            # Iterate across years to obtain the values:
            for py in range(len(period_list)):
                # Creating a key for the period in the results dictionary:
                per_name = period_list[py]
                prim_tbl_o.update({per_name: {}})

            # Extracting the *outcome (o)* controllers:
            o_actor = prim_fc_p_o[i]['Actor']
            o_name = prim_fc_p_o[i]['Name']
            o_proc = prim_fc_p_o[i]['Processing']
            o_set_type = prim_fc_p_o[i]['Set_Type']
            o_source = prim_fc_p_o[i]['Source']
            # Iterate across outcome column names for more controllers
            for c in range(len(o_proc['all_column_names'])):
                tcn = o_proc['all_column_names'][c]
                o_col_sets = o_proc['column_sets'][tcn]
                o_den_frml = o_proc['denominator_frml'][tcn]
                o_mcod = o_proc['meaning_codification'][tcn]
                o_num_frml = o_proc['numerator_frml'][tcn]
                o_last = o_proc['indicate_last_value']
                o_prms = o_proc['params'][tcn]
                o_set_argmnt = o_proc['set_arrangement'][tcn]
                o_sup_sets = o_proc['supporting_sets'][tcn]
                o_vmng = o_proc['variable_Management'][tcn]

                # Only execute the function if necessary:
                if scen in o_vmng['scenarios']:
                    prim_tbl_o = f2_exe_postproc(prim_tbl_o,
                                                 prim_tbl_o_bau,
                                                 period_list,
                                                 yr_ini_list,
                                                 yr_fin_list,
                                                 list_acc_files,
                                                 list_dfs,
                                                 o_actor, o_name,
                                                 o_set_type,
                                                 o_source, tcn, o_col_sets,
                                                 o_den_frml, o_mcod,
                                                 o_num_frml, o_last, o_prms,
                                                 o_set_argmnt, o_sup_sets,
                                                 o_vmng, exp_data, future,
                                                 scen, whole_period,
                                                 df_prim_set_matching, i,
                                                 'outcome', ana_ID, exp_id,
                                                 params, dicPop)
                    # return prim_tbl_o
                else:
                    print('     **Scenario ' + str(scen) +
                          ' not in outcome ' + o_name)

            pfd['o'].update({i: deepcopy(prim_tbl_o)})

        #   This is an ID applicable for *unique* drivers (d):

        # print('check udriver_IDs')
        # print(udriver_ID_list)
        # sys.exit()

        for i in udriver_ID_list:
            # PRINT STATUS:
            print('Status => Done reading files. // Analysis ID: '
                  + str(ana_ID) + ' // unique driver ID: ' + str(i) +
                  ' // Scenario: ' + str(scen) + ' // Future: '
                  + str(future))

            # Select the BAU pickle if we are not in the NDP scenario:
            if scen != params['BAU']:
                prim_tbl_o_bau = 'none'
                prim_tbl_d_bau = pfd_bau['d'][i]
            else:
                prim_tbl_o_bau, prim_tbl_d_bau = 'none', 'none'

            # Creating an empty dict for table of ID i and period y:
            prim_tbl_d = {}

            # Iterate across years to obtain the values:
            for py in range(len(period_list)):
                # Creating a key for the period in the results dictionary:
                per_name = period_list[py]
                prim_tbl_d.update({per_name: {}})

            # Extracting the *driver (d)* controllers:
            d_actor = prim_fc_p_d[i]['Actor']
            d_name = prim_fc_p_d[i]['Name']
            d_proc = prim_fc_p_d[i]['Processing']
            d_set_type = prim_fc_p_d[i]['Set_Type']
            d_source = prim_fc_p_d[i]['Source']
            # Iterate across driver column names for more controllers
            for c in range(len(d_proc['all_column_names'])):
                tcn = d_proc['all_column_names'][c]
                d_col_sets = d_proc['column_sets'][tcn]
                d_den_frml = d_proc['denominator_frml'][tcn]
                d_mcod = d_proc['meaning_codification'][tcn]
                d_num_frml = d_proc['numerator_frml'][tcn]
                d_last = d_proc['indicate_last_value']
                d_prms = d_proc['params'][tcn]
                d_set_argmnt = d_proc['set_arrangement'][tcn]
                d_sup_sets = d_proc['supporting_sets'][tcn]
                d_vmng = d_proc['variable_Management'][tcn]
               
                # Only execute the function if necessary:
                if scen in d_vmng['scenarios']:
                    prim_tbl_d = f2_exe_postproc(prim_tbl_d,
                                                 prim_tbl_d_bau,
                                                 period_list,
                                                 yr_ini_list,
                                                 yr_fin_list,
                                                 list_acc_files,
                                                 list_dfs,
                                                 d_actor, d_name,
                                                 d_set_type, d_source,
                                                 tcn, d_col_sets,
                                                 d_den_frml, d_mcod,
                                                 d_num_frml, d_last, d_prms,
                                                 d_set_argmnt,
                                                 d_sup_sets,
                                                 d_vmng, exp_data,
                                                 future, scen,
                                                 whole_period,
                                                 df_prim_set_matching,
                                                 i, 'driver', ana_ID, exp_id,
                                                 params, dicPop)
                    # return prim_tbl_d
                else:
                    print('     **Scenario ' + str(scen) +
                          ' not in driver ' + d_name)

            pfd['d'].update({i: deepcopy(prim_tbl_d)})
            # print(pfd['o'])
            # print(prim_tbl_d)
            # print(dirl + '/pfd' + '_' + scen + '_' + str(future) + '_' + str(ana_ID))
            # sys.exit()

        # # Print the resulting pickle with the PRIM-ready dataframes:
        # apply_suffix = '_' + scen + '_' + str(future) + '_' + str(ana_ID)
        # with open(dirl + '/pfd' + apply_suffix + '.pickle', 'wb') as outf:
        #     pickle.dump(pfd, outf, protocol=pickle.HIGHEST_PROTOCOL)
        # #outf.close()
        
        apply_suffix = '_' + scen + '_' + str(future) + '_' + str(ana_ID)
        # if future==1:
        #     print(dirl)
        #     print(apply_suffix)
        #     sys.exit()
        # if future==1:
        #     print('########')
        #     print('########')
        #     print(pfd)
        #     print('########')
        #     print('########')
        #     sys.exit()
        try:
            with open(dirl + '/pfd' + apply_suffix + '.pickle', 'wb') as outf:
                pickle.dump(pfd, outf, protocol=pickle.HIGHEST_PROTOCOL)
                print(dirl + '/pfd' + apply_suffix + '.pickle')
        except Exception as e:
            print("Error al guardar el archivo:", e)
                
''' ///////////////////////////////////////////////////////////////////
Function 2 (f2): execute the specific post-processing functions.

USE METHOD 1 OF
https://www.geeksforgeeks.org/how-to-create-dataframe-from-dictionary-in-python-pandas/
TO GENERATE THE TABLE DICTIONARY

The function "clean_regions" is a feature to eliminate errors.
'''


def clean_regions(col_sets_ref, params):
    col_sets = []
    dict_2_replace_stuck_regions = params['dict_2_replace_stuck_regions']
    stuck_reg_possible = list(dict_2_replace_stuck_regions.keys())
    for i in col_sets_ref:
        if i in stuck_reg_possible:
            col_sets.append(dict_2_replace_stuck_regions[i])
        else:
            col_sets.append(i)
    return col_sets


def f2_exe_postproc(prim_tbl, prim_tbl_bau,
                    period_list, yr_ini_list, yr_fin_list, list_acc_files,
                    list_dfs, actor, name, set_type,
                    source, col_name, col_sets,
                    den_frml, mcod, num_frml, last_indicate, prms, set_argmnt,
                    sup_sets, vmng, exp_data, future, scen, whole_period,
                    df_sm, tbl_id, o_or_d, ana_ID, exp_ID, params, dicPop):
    # There is a principle of having single-block string sets, except for these
    # regions: reg_1, reg_2, reg_3 // clean this:
    if (params['reg_1'] in col_sets or params['reg_2'] in col_sets or
            params['reg_3'] in col_sets):
        col_sets = clean_regions(col_sets, params)

    # Let's unpack the file directories:
    acc_input, acc_output = list_acc_files[0], list_acc_files[1]
    #print(acc_input, acc_output)
    acc_tem, acc_utem = list_acc_files[2], list_acc_files[3]
    acc_regtem, acc_regions = list_acc_files[4], list_acc_files[5]
    # Let's unpack the dataframes:
    df_input, df_output = list_dfs[0], list_dfs[1]
    df_tem, df_utem = list_dfs[2], list_dfs[3]
    df_regtem, df_region = list_dfs[4], list_dfs[5]

    # Controlling the file type:
    file_is_csv = True
    source_list = source.split(' ; ')
    if params['ose_inputs'] in source_list and len(source_list) == 1:
        df_data_list = df_input  # this is a list of dataframes
        file_data_list = acc_input
        source = source_list[0]
        ''' Header names for this .csv:
            Fuel; Technology; Emission; Season; Year '''

    elif params['ose_oupts'] in source_list and len(source_list) == 1:
        df_data_list = df_output  # this is a list of dataframes
        file_data_list = acc_output
        source = source_list[0]
        ''' Header names for this .csv:
            Fuel; Technology; Emission; Year '''

    elif params['tem_out_fis'] in source_list and len(source_list) == 1:
        df_data_list = df_tem  # this is a list of dataframes
        file_data_list = acc_tem
        source = source_list[0]
        ''' Header names for this .csv:
            Technology; Fuel; Fuel_Surname; Year; Age; Actor; Actor_Type;
            Owner; GorS '''

    elif params['tem_reg'] in source_list and len(source_list) == 1:
        df_data_list = df_region  # this is a list of dataframes
        file_data_list = acc_regions
        source = source_list[0]

    elif params['tem_out'] in source_list and len(source_list) == 1:
        if scen == params['BAU']:
            df_data_list = df_regtem
            file_data_list = acc_regtem
        else:  # 'e.g. NDP'
            # these are lists of dataframes
            df_data_list = df_regtem + [df_utem[0]]
            file_data_list = acc_regtem + [acc_utem[0]]
        source = source_list[0]
        ''' Header names for this .csv:
            Technology; Fuel; Fuel_Surname; Year; Age; Actor; Actor_Type;
            Owner; GorS '''

    elif params['exp_data'] in source_list and len(source_list) == 1:
        df_data_list = [exp_data]
        file_data_list = [params['exp_data']]
        source = source_list[0]
        file_is_csv = False

    elif len(source_list) > 1:
        print(222222222222222444444444444,source_list)
        if (len(source_list) == 3 and params['ose_oupts'] in source_list
                and params['tem_out'] in source_list and params['ose_inputs'] in
                source_list):
            # This is an ad hoc solution; new combinations should be added
            df_data_list = df_output
            df_data_list_2 = df_regtem
            df_data_list_3 = df_input
            source = source_list[0]
            # source_2 = source_list[1]  # never used in this or prior versions
            # We need to select the correct source file below when there is
            # more than 1 possible source
            # NOTE: In this combination, the needed parameter is Q, which
            # is found in TEM files and is indepenent of TEM strategy IDs.
        else:
            print('PRIM file creator error: there is no prevision for the '
                  + 'source combination: ' + str(source_list))
            sys.exit()

    # Defining the possible file headers to select sets:
    set_selector_headers = params['set_selector_headers']

    # # Extract GDP data; it is always helpful to have around:
    # this_gdp_allyr = exp_data['GDP_dict'][future]  # list with all GDPs

    # PRINT STATUS:
    print('         ' + o_or_d + '_ID: ' + str(tbl_id) +
          ' // Name: ' + str(name) + ' // Number of files: ' +
          str(len(df_data_list)))

    # Define ID columns;
    # these lists will always overwrite, but that is not a problem
    fut_id_list = []
    run_strat_id_list = []
    scenario_list = []
    tem_strat_id_list = []

    # Define a value list:
    value_list = {}  # Has the processed data
    store_num_lists = {}

    # Iterate across years to have value lists per period:
    for py in range(len(period_list)):
        per_name = period_list[py]
        value_list.update({per_name: []})
        store_num_lists.update({per_name: []})

    # Iterating across the file *df_data_list*:
    for f in range(len(df_data_list)):  # f: file iterable
        # Run ID calculation; "fut_id" is the basic:
        fut_id = int(future)
        fut_id_list.append(fut_id)
        # Calculate ID for TEM (multiple strategies):
        run_strat_id = int(future)*len(df_data_list) + f  # this may change
        run_strat_id_list.append(run_strat_id)
        # Create an appropiately sized list:
        scenario_list.append(scen)
        # Store the *strategy ID* to link to TEM:
        if ((source == params['tem_out']) or (source == params['tem_out_fis']) or
                (source == params['tem_reg'])):
            try:
                tem_strat_id = file_data_list[f
                                              ].replace('./', ''
                                                        ).split('.'
                                                                )[0
                                                                  ].split('_'
                                                                          )[-1]
                tem_strat_id_list.append(int(tem_strat_id))
            except Exception:
                tem_strat_id_list.append('none')

        else:
            tem_strat_id_list.append('none')

        # Extract data from .csv files:
        if file_is_csv is True:  # Helpful for standard .csv extractions
            file_data = df_data_list[f]
            #print(df_data_list[f])

            # Selecting the file header to select sets:
            fssh = set_selector_headers[set_type]
            # print(file_data)
            # return file_data
            try:
                # Creating the base mask with *sets* and *time*:
                this_mask_st = (file_data[fssh].isin(col_sets))
            except:
                print('check', tbl_id, name)
                print(fssh, col_sets, source)
                print(file_data.columns.tolist())
                sys.exit()

            # The next file_data is a *dataframe*; f1 is for "1st filter"
            file_data_f1 = deepcopy(file_data.loc[this_mask_st])

            # WARNING!!! Add a condition for fuels:
            if fssh == params['Fuel']:
                unique_techs = list(set(file_data_f1[params['Technology']].tolist()))

            # WARNING!!! Add a condition for emissions:
            if 'AnnualTechnologyEmission' in prms:
                #print(sup_sets)
                this_mask_st = (file_data[fssh].isin(col_sets) &
                                file_data[params['Emission']].isin(sup_sets))
                file_data_f1 = deepcopy(file_data.loc[this_mask_st])

            # WARNING!!! Add a condition for fleet:
            if params['q_tot'] in prms:
                this_mask_st = (file_data[fssh].isin(col_sets) &
                                file_data['Owner'].isna())
                file_data_f1 = deepcopy(file_data.loc[this_mask_st])

            if params['fle'] in prms:
                this_mask_st = (file_data[fssh].isin(col_sets))
                file_data_f1 = deepcopy(file_data.loc[this_mask_st])

            # WARNING! AN EXCEPTION IS NEEDED BELOW FOR SOURCE SELECTION
            # This is needed when iterating across parameters
            if (len(source_list) == 3 and params['ose_oupts'] in source_list
                    and params['tem_out'] in source_list and params['ose_inputs'] in
                    source_list):
                # This is an ad hoc solution; new combinations should be added
                file_data_2 = df_data_list_2[f]
                this_mask_st_2 = (file_data_2[fssh].isin(col_sets))
                file_data_f1_2 = deepcopy(file_data_2.loc[this_mask_st_2])

                file_data_3 = df_data_list_3[f]
                this_mask_st_3 = (file_data_3[fssh].isin(col_sets))
                file_data_f1_3 = deepcopy(file_data_3.loc[this_mask_st_3])

            # WARNING! AN EXCEPTION IS NEEDED BELOW FOR SPECIAL METRICS
            if params['spe_fiscal_cost'] in num_frml:
                file_data_temref = df_regtem[0]
                this_mask_st_temref = (file_data_temref[fssh].isin(col_sets))
                file_data_f1_temref = deepcopy(file_data_temref.
                                               loc[this_mask_st_temref])

        # Extract data from other files that are not .csv:
        else:  # These are ad-hoc conditions:
            if num_frml == params['spe_biofuel']:  # ad-hoc condition 1
                idcs = col_sets[0].replace(' ', '').split('then')
                id0, id1, id2 = idcs[0], idcs[1], idcs[2]
                exp_data = df_data_list[0]
                if fut_id != 0:  # !!!THIS IS PROVISIONAL!!!
                    file_data = exp_data['Blend_Shares'][id0][fut_id][id1][id2]
                else:
                    file_data = exp_data['Blend_Shares'][id0][1][id1][id2]
                # The next file_data is a *list* // repeat down below
                # file_data_f1 = [file_data[i] for i in apyr_ind]

            elif num_frml == params['gdp_growth']:  # ad-hoc condition 2
                file_data = df_data_list[0]['experiment_dictionary'][1]
                # The next file_data is an *integer*
                file_data_f1 = file_data['Values'][fut_id]

        # Iterate across years to obtain the values:
        for py in range(len(period_list)):
            # Parameterize period:
            per_name = period_list[py]
            yr_ini = yr_ini_list[py]
            yr_fin = yr_fin_list[py]

            # Calculating the applicable year list (apyr)
            apyr = [y for y in range(yr_ini, yr_fin+1)]
            apyr_ind = [i for i, val in enumerate(whole_period)
                        if val in set(apyr)]

            # Subselect the period's GDP:
            #this_gdp_apyr = [this_gdp_allyr[i] for i in apyr_ind]  # period GDP

            # Defining the value to append and initializing it with zero:
            this_value = 0

            # Define "res_lists_sum" that is as long as the number of years
            # in the period:
            res_lists_sum = [0 for y in range(len(apyr))]

            # /////////// Working with *numerator formulas* ///////////
            if params['gdp'] in num_frml:
                # This is GDP growth; can be extracted directly
                this_value += file_data_f1

            # The conditions below are attended with pandas filters:
            if ((params['average'] in num_frml or params['direct'] in num_frml or params['sum'] in
                 num_frml or params['spe_fiscal_cost'] in num_frml or params['cumulative']
                 in num_frml or params['spe_EaImp'] in num_frml or
                 params['spe_ExM'] in num_frml or
                 params['spe_gen'] == num_frml or
                 params['spe_t&d'] == num_frml or
                 params['spe_psc'] == num_frml) and
                (params['multiply'] not in num_frml)):
                # NOTE 1: for "average" the denominator is the number of sets
                # NOTE 2: *direct* always has only 1 param and 1 set;
                # NOTE 3: for *direct*, assume last-year-of-period extraction
                # NOTE 4: we have to control the numerator expression, i.e.,
                # whether we use sums or subtractions
                
                local_num = [0 for y in range(len(apyr))]
                local_den = [0 for y in range(len(apyr))]
                if params['spe_fiscal_cost'] in num_frml:  # tr: tem reference
                    ln_tr = [0 for y in range(len(apyr))]  # ln: local_num
                    ld_tr = [0 for y in range(len(apyr))]  # ld: local_den

                exception_below = False
                for prm in range(len(prms)):  # iterating with an integer
                    # WARNING! CREATING AN EXCEPTION FOR SOURCE SELECTION
                    if (len(source_list) == 3 and params['ose_oupts'] in
                            source_list and params['tem_out'] in source_list and
                            params['ose_inputs'] in source_list):
                        if prms[prm] in file_data_f1.columns.tolist():
                            pass
                            # No action is needed and the code can proceed
                        elif prms[prm] in file_data_2.columns.tolist():
                            # Reselect file to match param source
                            file_data_f1 = deepcopy(file_data_f1_2)
                        elif prms[prm] in file_data_3.columns.tolist():
                            # Reselect file to match param source
                            file_data_f1 = deepcopy(file_data_f1_3)
                        else:
                            print('There is a problem with matching'
                                  + 'parameters ' + 'and files: ', prms[prm],
                                  ' // ID: ', tbl_id)
                            sys.exit()

                    try:
                        this_mask_p = (~file_data_f1[prms[prm]].isna())
                        file_data_f2 = deepcopy(file_data_f1.loc[this_mask_p])
                        # Storing the *local* yearly data:
                        for y in range(len(apyr)):
                            if params['com_set_type'] in num_frml:
                                apply_supp_col = sup_sets[0].split('-')[-1]
                                apply_supp_set = sup_sets[0].split('-')[0]
                                this_mask_p_y = (file_data_f2
                                                 [params['Year']].isin([apyr[y]])) & \
                                    (file_data_f2[apply_supp_col]
                                     .isin([apply_supp_set]))
                            else:
                                
                                this_mask_p_y = (file_data_f2
                                                 [params['Year']].isin([apyr[y]]))
                                
                            file_data_f3 = file_data_f2.loc[this_mask_p_y,
                                                            prms[prm]]

                            try:
                                use_this_val = sum(file_data_f3)
                            except Exception:
                                print('The parameter must be a float.',
                                      ' Change and re-run.')

                            local_num, local_den = f3_num_locals(local_num,
                                                                 local_den, y,
                                                                 use_this_val,
                                                                 prms[prm],
                                                                 file_data_f1,
                                                                 set_argmnt)

                        # WARNING! EXCEPTION BELOW FOR SPECIAL METRICS
                        if params['spe_fiscal_cost'] in num_frml:
                            # use tr: for temref
                            this_mask_p_tr = (~file_data_f1_temref[prms
                                                                   [prm]
                                                                   ].isna())
                            file_data_f2_tr = deepcopy(file_data_f1_temref.
                                                       loc[this_mask_p_tr])
                            # Storing the *local* yearly data /
                            # use tm: for this_mask
                            for y in range(len(apyr)):
                                if params['com_set_type'] in num_frml:
                                    apply_supp_col = sup_sets[0].split('-')[-1]
                                    apply_supp_set = sup_sets[0].split('-')[0]
                                    tmp_tr_y = (file_data_f2_tr
                                                [params['Year']].isin([apyr[y]])) & \
                                        (file_data_f2_tr[apply_supp_col]
                                         .isin([apply_supp_set]))
                                else:
                                    tmp_tr_y = (file_data_f2_tr
                                                [params['Year']].isin([apyr[y]]))

                                file_data_f3_tr = file_data_f2_tr.loc[tmp_tr_y,
                                                                      prms[prm]
                                                                      ]
                                # Shortening variable names:
                                # ut: use_this // fd: file_data
                                ut_value = sum(file_data_f3_tr)
                                fd_f1_tr = deepcopy(file_data_f1_temref)
                                ln_tr, ld_tr = f3_num_locals(ln_tr, ld_tr, y,
                                                             ut_value,
                                                             prms[prm],
                                                             fd_f1_tr,
                                                             set_argmnt)

                    except Exception:
                        exception_below = True
                        print(' PRIM file creator error: you introduced an '
                              + 'incorrect source for this '
                              + o_or_d + ' because the column (parameter) does'
                              + ' not exist in file // Scenario: ' + scen +
                              ' // Future: ' + str(future))
                        print('     ' + o_or_d + ' ID: ' + str(tbl_id))
                        print('     ' + o_or_d + ' name: ' + str(name))
                        print('     ' + o_or_d + ' source (incorrect): '
                              + str(source))
                        print('     ' + o_or_d + ' parameter: '
                              + str(prms[prm]))
                        print(prms)
                        print(num_frml)
                        print(' - Manually fix the process and re-run -')
                        if len(source_list) == 3:
                            print('     Multiple sources: ' + source_list)
                            print(prms[prm])
                            print(prms[prm] in file_data_f1.columns.tolist())
                            print(prms[prm] in file_data_2.columns.tolist())
                            print(prms[prm] in file_data_3.columns.tolist())
                        print('\n')
                        sys.exit()

                for y in range(len(apyr)):
                    # If no changes were made to the denominator, convert to 1s
                    if local_den[y] == 0:
                        local_den[y] = 1
                    # Besides exceptions, store the results:
                    if params['spe_fiscal_cost'] in num_frml:
                        res_lists_sum[y] = -1*(local_num[y]-ln_tr[y])/local_den[y]
                    # if needed, add more conditions with "elif"
                    else:
                        res_lists_sum[y] = local_num[y]/local_den[y]

            # The condition below requires *dividing by the number of sets*
            if (params['average'] in num_frml):
                for y in range(len(apyr)):
                    try:
                        if fssh == params['Fuel']:
                            res_lists_sum[y] = \
                                res_lists_sum[y] / len(unique_techs)
                        elif params['rel'] in num_frml:  # don't act to avoid issues
                            pass
                        else:
                            res_lists_sum[y] = res_lists_sum[y] / len(col_sets)
                    except:
                        pass  # this is likely H2 not in sets!!!

            # The condition below handles shares:
            if params['share'] in num_frml:
                if params['electric'] in num_frml:
                    sup_sets = [i for i in col_sets if params['ele'] in i]
                elif params['h2'] in num_frml:
                    sup_sets = [i for i in col_sets if params['hyd'] in i]
                elif params['lpg'] in num_frml:
                    sup_sets = [i for i in col_sets if params['lpg'] in i]
                elif params['zev'] in num_frml:
                    sup_sets = [i for i in col_sets if params['ele'] in i or
                                params['hyd'] in i]
                elif params['forest'] in num_frml:
                    sup_sets = [i for i in col_sets if params['for'] in i ]
                elif params['clinker'] in num_frml:
                    sup_sets = [i for i in col_sets if params['clk'] in i ]
                    sup_sets_2 = [i for i in col_sets if params['cem'] in i ]
                    # print(sup_sets,sup_sets_2)
                    # sys.exit()
                elif params['renewable_gen'] in num_frml:
                    sup_sets = params['re_gen']
                elif params['renewable_total'] in num_frml:
                    sup_sets = params['re_total']
                    
                elif params['per_cap_gen_sol'] in num_frml:
                    sup_sets = [i for i in col_sets if params['sol_dem'] in i ]
                elif params['per_cap_gen_wat'] in num_frml:
                    sup_sets = [i for i in col_sets if params['wat_dem'] in i ]
                    
                elif params['circ_econ_sol'] in num_frml:
                    sup_sets = params['green_sol']
                elif params['treat_wat'] in num_frml:
                    sup_sets = params['green_wat']
                    
                sup_mask_st = (file_data[fssh].isin(sup_sets))
                sup_data_f1 = deepcopy(file_data.loc[sup_mask_st])

                sup_mask_p = (~sup_data_f1[prms[0]].isna())  # only 1 param
                sup_data_f2 = deepcopy(sup_data_f1.loc[sup_mask_p])
                num_list = [0 for y in range(len(apyr))]
                
                if params['clinker'] in num_frml:
                    sup_mask_st_2 = (file_data[fssh].isin(sup_sets_2))
                    sup_data_f1_2 = deepcopy(file_data.loc[sup_mask_st_2])

                    sup_mask_p_2 = (~sup_data_f1_2[prms[0]].isna())  # only 1 param
                    sup_data_f2_2 = deepcopy(sup_data_f1_2.loc[sup_mask_p_2])
                    num_list_2 = [0 for y in range(len(apyr))]
                    

                this_mask_p = (~file_data_f1[prms[0]].isna())  # only 1 param
                file_data_f2 = deepcopy(file_data_f1.loc[this_mask_p])
                den_list = [0 for y in range(len(apyr))]
                

                # Storing the yearly data:
                for y in range(len(apyr)):
                    sup_mask_p_y = (sup_data_f2[params['Year']].isin([apyr[y]]))
                    sup_data_f3 = sup_data_f2.loc[sup_mask_p_y, prms[0]]
                    num_list[y] += sum(sup_data_f3)
                    
                    if params['clinker'] in num_frml:
                        sup_mask_p_y_2 = (sup_data_f2_2[params['Year']].isin([apyr[y]]))
                        sup_data_f3_2 = sup_data_f2_2.loc[sup_mask_p_y_2, prms[0]]
                        num_list_2[y] += sum(sup_data_f3_2)
                        
                    

                    this_mask_p_y = (file_data_f2[params['Year']].isin([apyr[y]]))
                    file_data_f3 = file_data_f2.loc[this_mask_p_y, prms[0]]
                    den_list[y] += sum(file_data_f3)

                    if params['forest'] in num_frml:
                        res_lists_sum[y] = num_list[y] / params['area']
                        # print('############ HERE FOREST###########')
                        # print(y,num_list[y]/params['area'])
                    elif params['clinker'] in num_frml:
                        #res_lists_sum[y] = num_list[y]/(num_list_2[y]*den_list[y])
                        res_lists_sum[y] = num_list[y]/num_list_2[y]
                        #print('############ HERE CLINKER ###########')
                        #print(y, num_list[y], num_list_2[y], den_list[y], num_list[y]/(num_list_2[y]*den_list[y]))
                        #print(y, num_list[y], num_list_2[y], num_list[y]/num_list_2[y])
                    elif params['renewable_gen'] in num_frml:
                        # print('############ HERE RENEWABLE NO CONV ###########')
                        # print(y, num_list[y], den_list[y], num_list[y]/den_list[y])
                        res_lists_sum[y] = num_list[y] / den_list[y]
                    elif params['renewable_total'] in num_frml:
                        # print('############ HERE RENEWABLE CONV + NO CONV ###########')
                        # print(y, num_list[y], den_list[y], num_list[y]/den_list[y])
                        res_lists_sum[y] = num_list[y] / den_list[y]
                    elif params['per_cap_gen_sol'] in num_frml:
                        #print('############ HERE SOLID WASTE ###########')
                        #print(y, apyr[y], num_list[y], dicPop[apyr[y]], num_list[y] *1000000000/ (dicPop[apyr[y]]*365))
                        res_lists_sum[y] = num_list[y] *1000000000/ (dicPop[apyr[y]]*365)
                    elif params['per_cap_gen_wat'] in num_frml:
                        #print('############ HERE WASTEWATER ###########')
                        #print(y, apyr[y], num_list[y], dicPop[apyr[y]], num_list[y] *1000000000000/ (dicPop[apyr[y]]*365))
                        res_lists_sum[y] = num_list[y] *1000000000000/ (dicPop[apyr[y]]*365)
                    elif params['circ_econ_sol'] in num_frml:
                        # print('############ HERE CIRCULAR ECONOMY SOLIDS ###########')
                        # print(y, num_list[y], den_list[y], num_list[y]/den_list[y])
                        res_lists_sum[y] = num_list[y]/den_list[y]
                    elif params['treat_wat'] in num_frml:
                        #print('############ HERE TREATED WATER ###########')
                        #print(y, num_list[y], den_list[y], num_list[y]/den_list[y])
                        res_lists_sum[y] = num_list[y]/den_list[y]
                    else:
                        res_lists_sum[y] = num_list[y] / den_list[y]
                        # print('############ HERE OTHER ###########')
                        # print(y,num_list[y],den_list[y])
                # if params['clinker'] in num_frml:
                #     sys.exit()

            # The condition below helps methods tagged as *special*:
            if params['spe'] in num_frml:
                if params['spe_biofuel'] == num_frml:
                    file_data_f1 = [file_data[i] for i in apyr_ind]
                    for y in range(len(apyr)):
                        res_lists_sum[y] = file_data_f1[y]

                elif params['spe_fiscal_cost'] == num_frml:
                    pass  # addressed above

                elif ((params['spe_gen'] == num_frml) or
                        (params['spe_t&d'] == num_frml) or
                        (params['spe_psc'] == num_frml)):  # divide the costs by the production, hence a total cost per unit of production ("normalization")
                    num_list = [0 for y in range(len(apyr))]
                    numerator_values_avgcosts = deepcopy(res_lists_sum)

                    # Gotta select the production tech:
                    if params['gen_cost'] in num_frml or params['psc'] in num_frml:
                        sup_sets = [k for k in col_sets if 'PP' in k]
                    else:  # for t&d and power sector costs
                        sup_sets = params['sup_sets']

                    sup_mask_st = (file_data[fssh].isin(sup_sets))
                    sup_data_f1 = deepcopy(file_data.loc[sup_mask_st])

                    sup_mask_p = (~sup_data_f1['ProductionByTechnology'].isna())  # only 1 param
                    sup_data_f2 = deepcopy(sup_data_f1.loc[sup_mask_p])
                    den_list = [0 for y in range(len(apyr))]

                    # Storing the yearly data:
                    for y in range(len(apyr)):
                        num_list[y] += numerator_values_avgcosts[y]

                        sup_mask_p_y = (sup_data_f2[params['Year']].isin([apyr[y]]))
                        sup_data_f3 = sup_data_f2.loc[sup_mask_p_y, 'ProductionByTechnology']
                        den_list[y] += sum(sup_data_f3)

                        res_lists_sum[y] = num_list[y] / den_list[y]

                elif ((params['spe_us_solar_prod'] == num_frml) or
                        (params['spe_dis_solar_prod'] == num_frml) or
                        (params['spe_w_prod'] == num_frml)):
                    this_mask_p = (~file_data_f1[prms[0]].isna())
                    file_data_f2 = deepcopy(file_data_f1.loc[this_mask_p])
                    num_list = [0 for y in range(len(apyr))]

                    sup_sets = params['sup_sets_solar']

                    sup_mask_st = (file_data[fssh].isin(sup_sets))
                    sup_data_f1 = deepcopy(file_data.loc[sup_mask_st])

                    sup_mask_p = (~sup_data_f1[prms[0]].isna())  # only 1 param
                    sup_data_f2 = deepcopy(sup_data_f1.loc[sup_mask_p])
                    den_list = [0 for y in range(len(apyr))]

                    # Storing the yearly data:
                    for y in range(len(apyr)):
                        this_mask_p_y = (file_data_f2[params['Year']].isin([apyr[y]]))
                        file_data_f3 = file_data_f2.loc[this_mask_p_y, prms[0]]
                        num_list[y] += sum(file_data_f3)

                        sup_mask_p_y = (sup_data_f2[params['Year']].isin([apyr[y]]))
                        sup_data_f3 = sup_data_f2.loc[sup_mask_p_y, prms[0]]
                        den_list[y] += sum(sup_data_f3)

                        res_lists_sum[y] = num_list[y] / den_list[y]

                elif params['spe_elas'] == num_frml:
                    this_mask_p = (~file_data_f1[prms[0]].isna())
                    file_data_f2 = deepcopy(file_data_f1.loc[this_mask_p])

                    elasticity_apyr = [y for y in range(yr_ini-1, yr_fin+1)]
                    elasticity_apyr_ind = [i for i, val in enumerate(whole_period)
                                           if val in set(elasticity_apyr)]

                    # Subselect the period's GDP:
                    e_gdp_apyr = [this_gdp_allyr[i] for i in
                                    elasticity_apyr_ind]  # period GDP

                    num_list = [0 for y in range(len(elasticity_apyr))]
                    res_lists_sum = [0 for y in range(len(apyr))]

                    # Storing the yearly data:
                    for y in range(len(elasticity_apyr)):
                        this_mask_p_y = (file_data_f2[params['Year']].isin([elasticity_apyr[y]]))
                        file_data_f3 = file_data_f2.loc[this_mask_p_y, prms[0]]
                        num_list[y] += sum(file_data_f3)

                    for y in range(1,len(apyr)+1):  # "apyr" is correct
                        num_change = (num_list[y]-num_list[y-1])/num_list[y-1]


                        try:
                            den_change = \
                                (e_gdp_apyr[y]-e_gdp_apyr[y-1])/e_gdp_apyr[y-1]
                        except Exception:
                            print( len(e_gdp_apyr), y, y-1, len(apyr) )
                            sys.exit()


                        res_lists_sum[y-1] = num_change/den_change

                elif (params['spe_mode_shift'] == num_frml) or (
                        params['spe_PT_dist'] == num_frml) or (
                        params['spe_fre_shift'] == num_frml):
                    this_mask_p = (~file_data_f1[prms[0]].isna())
                    file_data_f2 = deepcopy(file_data_f1.loc[this_mask_p])
                    num_list = [0 for y in range(len(apyr))]

                    if params['spe_mode_shift'] == num_frml:
                        sup_sets = params['sup_sets_2']
                    elif params['spe_fre_shift'] == num_frml:
                        sup_sets = params['sup_sets_3']
                    elif params['spe_PT_dist'] == num_frml:
                        sup_sets = params['sup_sets_4']
                    sup_mask_st = (file_data[fssh].isin(sup_sets))
                    sup_data_f1 = deepcopy(file_data.loc[sup_mask_st])

                    sup_mask_p = (~sup_data_f1[prms[0]].isna())  # only 1 param
                    sup_data_f2 = deepcopy(sup_data_f1.loc[sup_mask_p])
                    den_list = [0 for y in range(len(apyr))]

                    # Storing the yearly data:
                    for y in range(len(apyr)):
                        this_mask_p_y = (file_data_f2[params['Year']].isin([apyr[y]]))
                        file_data_f3 = file_data_f2.loc[this_mask_p_y, prms[0]]
                        num_list[y] += sum(file_data_f3)

                        sup_mask_p_y = (sup_data_f2[params['Year']].isin([apyr[y]]))
                        sup_data_f3 = sup_data_f2.loc[sup_mask_p_y, prms[0]]
                        den_list[y] += sum(sup_data_f3)

                        res_lists_sum[y] = num_list[y] / den_list[y]

            # The condition below handles multiplications:
            if params['multiply'] in num_frml:
                # By design, there is only 1 parameter for this formula:
                inv_prm = prms[0].split(' * ')[0]
                sup_prm = prms[0].split(' * ')[1]

                for y in range(len(apyr)):
                    for a_set in col_sets:
                        match_mask = (df_sm['Involved_Set'] == a_set)
                        matching_set_df = df_sm.loc[match_mask,
                                                    'Supporting_Sets']
                        matching_set = matching_set_df.iloc[0]

                        # WARNING (ad hoc)! SELECTING THE DATA SOURCES:
                        if (len(source_list) == 3 and
                                params['ose_oupts'] in source_list and
                                params['tem_out'] in source_list and
                                params['ose_inputs'] in source_list):
                            # For involved param/set:
                            if inv_prm in file_data_f1.columns.tolist():
                                file_data_inv = file_data
                            elif inv_prm in file_data_2.columns.tolist():
                                file_data_inv = file_data_2
                            elif inv_prm in file_data_3.columns.tolist():
                                file_data_inv = file_data_3
                            # For supplementary param/set:
                            if sup_prm in file_data_f1.columns.tolist():
                                file_data_sup = file_data
                            elif sup_prm in file_data_2.columns.tolist():
                                file_data_sup = file_data_2
                            elif sup_prm in file_data_3.columns.tolist():
                                file_data_sup = file_data_3

                        # Extracting the "involved_set" value:
                        mask_inv = (file_data_inv[fssh].isin([a_set])
                                    ) & (~file_data_inv[inv_prm].isna()
                                         ) & (file_data_inv[params['Year']].isin([apyr[
                                              y]]))
                        file_data_f2_inv = deepcopy(file_data_inv.loc[mask_inv,
                                                                      inv_prm])
                        value_inv = sum(file_data_f2_inv)

                        # Extracting the "supporting_set" value;
                        # also, supplementary data to multiply:
                        mask_sup = (file_data_sup[fssh].isin([matching_set])
                                    ) & (~file_data_sup[sup_prm].isna()
                                         ) & (file_data_sup[params['Year']].isin([apyr
                                                                         [y]]))
                        file_data_f2_sup = deepcopy(file_data_sup.loc[mask_sup,
                                                                      sup_prm])
                        value_sup = sum(file_data_f2_sup)

                        # Storing the yearly data:
                        res_lists_sum[y] += value_inv * value_sup

            # Store the numerator for subsequent use, particularly for the BAU:
            store_res_lists_sum = deepcopy(res_lists_sum)

            ref_the_bau = False
            # /////////// Control the type of value to store:
            #             direct OR with_respect_to_BAU ///////////
            if (vmng['variable_Management'] == params['wrt_bau_ex'] and
                    scen != params['BAU']):
                ref_the_bau = True

            # The condition below divides the metric with a value from a
            # specified year:
            if params['rel'] in num_frml and exception_below is False:
                rel_yr = int(num_frml.split('_')[-1].replace(params['rel'], ''))
                rel_mask_y = (file_data_f1[params['Year']].isin([rel_yr]))
                rel_den = 0
                for prm in range(len(prms)):
                    this_mask_p = (~file_data_f1[prms[prm]].isna())
                    file_data_f2 = deepcopy(file_data_f1.loc[this_mask_p])

                    file_data_f3 = file_data_f2.loc[rel_mask_y, prms[prm]]

                    rel_den += sum(file_data_f3)

                # Store the elements of relative:
                # print(12345,store_res_lists_sum,rel_den,prms,rel_yr)
                # return rel_mask_y
                try:
                    res_lists_sum = \
                        [store_res_lists_sum[y]/rel_den
                         for y in range(len(apyr))]
                    
                except Exception:
                    # If the denominator is 0, define the variable as 0:
                    res_lists_sum = [0 for i in range(len(apyr))]
                    # this means an "impossibility" for the defined metric

            # /////////// Working with *denominator formulas* ///////////
            if params['den_gdp'] in den_frml:
                value_den = deepcopy(this_gdp_apyr)

            if 'none' in den_frml:
                value_den = [1 for i in range(len(apyr))]

            if params['tracost_at'] in den_frml or params['totcost_at'] in den_frml:
                # Find denominator year:
                den_data_yr = int(den_frml.split('_')[-1].replace('at', ''))

                # Select parameters for denominator:
                use_num_sub_prms = set_argmnt['numerator_sub_params']
                use_num_sum_prms = set_argmnt['numerator_sum_params']
                if type(use_num_sub_prms) == list:
                    iter_prms = use_num_sub_prms
                elif use_num_sub_prms == 'all' or use_num_sum_prms == 'all':
                    iter_prms = prms
                else:
                    print('There is a desing or a strucutre error. Carefully '
                          + 'check and review. Re-run after fix.')
                    sys.exit()

                # General quality assurance: make sure to have a non-empty
                # initial dataframe:
                if len(file_data_f1.index.tolist()) == 0:
                    print('WARNING! There may be an incorrect set in the ' +
                          'PRIM structure file. Review and re-run')
                    print('Table_ID', tbl_id, fssh, col_sets)
                    print('\n')
                    sys.exit()

                # Find appropiate denominator
                value_den_point = 0
                for aprm in iter_prms:  # iterating with a string
                    this_mask_py = (~file_data_f1[aprm].isna()) & \
                        (file_data_f1[params['Year']].isin([den_data_yr]))
                    file_data_f2_den = file_data_f1.loc[this_mask_py]

                    # Now extract the corresponding values:
                    if params['tot'] in den_frml:
                        own_lst_raw = list(set(file_data_f1['Owner'].tolist()))
                        owner_list = [i for i in own_lst_raw if 'Q' in i]
                        owner_factors = {'Q1': 10, 'Q2': 10, 'Q3': 12,
                                         'Q4': 14, 'Q5': 19}
                        for i in range(len(owner_list)):
                            mask_owner = \
                                (file_data_f2_den['Owner'] == owner_list[i])
                            use_this_value = sum(file_data_f2_den.loc
                                                 [mask_owner, aprm])
                            total_factor = owner_factors[owner_list[i].
                                                         split('_')[0]]
                            value_den_point += use_this_value / total_factor

                    elif params['tra'] in den_frml:
                        use_this_value = sum(file_data_f1.loc
                                             [this_mask_py, aprm])
                        value_den_point += use_this_value

                value_den = [value_den_point for i in range(len(apyr))]

            # /////////// Control the type of value to store:
            #             period average OR last (this is ad-hoc) ///////////
            if params['gdp'] not in num_frml:  # value was already assigned; not needed
                if ref_the_bau is False:
                    values_in_period = [res_lists_sum[y]/value_den[y] for
                                        y in range(len(apyr))]

                else:  # The BAU is [0] as it has only 1 element
                    bau_rls = prim_tbl_bau[per_name][col_name]['snl'][0]
                    # rls: res_lists_sum
                    values_in_period = [(res_lists_sum[y]-bau_rls[y]
                                         )/value_den[y]
                                        for y in range(len(apyr))]
                    store_res_lists_sum = deepcopy(values_in_period)

            # select the last year-of-period value
            if params['direct'] in num_frml or last_indicate == params['end']:  # grab last
                try:
                    this_value = values_in_period[-1]
                except Exception:
                    print('check this please')
                    print(num_frml, last_indicate, tbl_id)
                    sys.exit()

            elif last_indicate == params['start'] and params['gdp'] not in num_frml:  # grab first
                this_value = values_in_period[0]
            elif params['cumulative'] in num_frml:  # select the sum of period
                this_value = sum(values_in_period)
                '''
                # FUTURE FEATURES:
                                YOU MAY ADD OTHER FORMULAS WITH THIS CONDITION;
                                YOU MAY ADD OTHER CONDITIONS
                '''
            elif params['gdp'] in num_frml:
                pass  # The value was assigned earlier
            elif last_indicate == params['avg']:  # select the period average
                this_value = sum(values_in_period) / len(values_in_period)
            else:  # select the period average
                this_value = sum(values_in_period) / len(values_in_period)

            # The code below is incorrect because of denominator interference
            # The BAU is [0]; only 1 element
            # this_value -= prim_tbl_bau[col_name]['vl'][0]

            # /////////// Store the value ///////////
            # print(222,this_value,num_frml)
            value_list[per_name].append(this_value)
            store_num_lists[per_name].append(store_res_lists_sum)

            # Let's update the dictionary with the processing information:
            #   using "col_name" to name outcome/driver
            prim_tbl[per_name].update({col_name: {'vl': value_list[per_name],
                                                  'snl':
                                                  store_num_lists[per_name]
                                                  }})
            prim_tbl[per_name].update({'Fut_ID': fut_id_list})
            prim_tbl[per_name].update({'Run_Strat_ID': run_strat_id_list})
            prim_tbl[per_name].update({'Scenario': scenario_list})
            prim_tbl[per_name].update({'Strat_ID': tem_strat_id_list})

    return prim_tbl


''' ///////////////////////////////////////////////////////////////////
Function 3 (f3): obtain an expression that adds or subtracts sets or params in
the metric numerator.

# FUTURE FEATURE: THIS FUNCTION CAN HAVE FURTHER DEVELOPMENT IF MORE METRIC
POSSIBILITIES ARE REQUIRED, E.G. DIFFERENCE BETWEEN SETS
'''


def f3_num_locals(local_num, local_den, y, use_this_value, prm, file_data_f1,
                  set_argmnt):

    # Unpack the set description; these should aide executing instructions:
    num_sum_sets = set_argmnt['numerator_sum_sets']
    num_sub_sets = set_argmnt['numerator_sub_sets']
    den_sum_sets = set_argmnt['denominator_sum_sets']
    den_sub_sets = set_argmnt['denominator_sub_sets']
    num_sum_prms = set_argmnt['numerator_sum_params']
    num_sub_prms = set_argmnt['numerator_sub_params']
    den_sum_prms = set_argmnt['denominator_sum_params']
    den_sub_prms = set_argmnt['denominator_sub_params']

    if (num_sum_sets == 'all' and num_sub_sets == 'none' and num_sum_prms ==
            'all' and num_sub_prms == 'none'):
        local_num[y] += use_this_value

    if (num_sum_sets == 'none' and num_sub_sets == 'all' and num_sum_prms ==
            'none' and num_sub_prms == 'all'):
        local_num[y] += -1*use_this_value

    if (den_sum_sets == 'all' and den_sub_sets == 'none' and den_sum_prms ==
            'all' and den_sub_prms == 'none'):
        local_den[y] += use_this_value

    if (den_sum_sets == 'none' and den_sub_sets == 'all' and den_sum_prms ==
            'none' and den_sub_prms == 'all'):
        local_den[y] += -1*use_this_value

    if (num_sum_sets == 'all' and num_sub_sets == 'all' and type(num_sum_prms)
            == list and type(num_sub_prms) == list):
        if prm in num_sum_prms:
            local_num[y] += use_this_value
        elif prm in num_sub_prms:
            local_num[y] += -1*use_this_value

    if (den_sum_sets == 'all' and den_sub_sets == 'all' and type(den_sum_prms)
            == list and type(den_sub_prms) == list):
        if prm in den_sum_prms:
            local_den[y] += use_this_value
        elif prm in den_sub_prms:
            local_den[y] += -1*use_this_value

    # This add-on is for special fiscal results:
    if (num_sum_sets == 'all' and num_sub_sets == 'none' and type(num_sum_prms)
            == list):
        if prm in num_sum_prms:
            local_num[y] += use_this_value

    if (den_sum_sets == 'all' and den_sub_sets == 'none' and type(den_sum_prms)
            == list):
        if prm in den_sum_prms:
            local_den[y] += use_this_value

    return local_num, local_den


''' ///////////////////////////////////////////////////////////////////
                            END OF FUNCTIONS
'''

if __name__ == '__main__':
    """
    *Abbreviations:*
    _p: _parallel (useful for multiprocessing) // _parameter
    _o: _order / _outcome
    _sep: _separated
    _sm: set_matching
    _o_or_d: outcome or driver
    acc: access
    col: columns
    den: denominator
    df: dataframe
    dir: directory / address
    exp(s): experiment(s)
    fc: file_creator
    fcc: file_creator_controller
    fn: filename
    frml: formula
    fssh: file_set_selector_header
    fin: final
    ini: initial
    mcod: meaning_codification
    num: number
    num: numerator
    pfc: prim_files_creator
    pfc: prim_files_dictionary
    prm: params
    set_argmnt: set_arrangement
    sup_sets: supporting_sets
    outf: output file
    tbl(s): table(s)
    tcn: this_column_name
    vmng: variable_Management
    yr: year
    """

    dicPop=dict()
    libro_p=pd.ExcelFile( 'Population.xlsx' )
    hoja_p=libro_p.parse( 'Sheet1' , skiprows = 0 )
    encabezados_p=list(hoja_p)
    col_y=list(hoja_p[encabezados_p[0]])
    col_p=list(hoja_p[encabezados_p[1]])
    dicPop=dict(zip(col_y,col_p))


    # Recording initial time of execution
    start_1 = time.time()

    # Read yaml file with parameterization
    with open('PRIM_t3f2.yaml', 'r') as file:
        # Load content file
        params = yaml.safe_load(file)

    ''' ----------------------------------------------------------------------
        CLARIFYING: "prim_files_creator.py" is useful for "t3b_sdiscovery".
        Since we need to extract data form the "t3a_experiments" folder,
    we need to place this .py in the root folder.
        OVERARCHING OBJECTIVE: create small .csv files with "only-column"
    format that process the variables needed for the compartmentalized PRIM
    analysis per-future (and strategy, in the case of fiscal analysis).
        Be sure to create .csv files for each of the "blocks" and "IDs"
    specified in the "prim_files_creator.pickle", as well as for each
    individual period. This diminishes file size.
        Tip: it would be beneficial to create yearly visualization-ready
    data for the outcomes/drivers flagged with a "Post-TEM" data source
    in the "prim_files_creator.pickle").
        Make sure to add a "compiler" section that puts the tables
    PRIM-ready in the correct folder.
    ---------------------------------------------------------------------- '''

    # Let's start by defining the directories to work with.
    # has all the data per run: OSeMOSYS inputs, OSeMOSYS outputs, TEM_outputs
    dir_exps = params['dir_exps']  # dir_exps = './t3a_temp_experiments'

    # has the management dictionary; is the destination of the compiled tables
    dir_sdisc = params['dir_sdisc']

    #   max_per_batch: the number of simultaneous runs
    max_per_batch = params['max_per_batch']  # ADJUSTABLE CODE INPUT

    ''' ----------------------------------------------------------------------
        Step 0: open analysis specifications
        Objective: open the excely that provides initial parameters
    -----------------------------------------------------------------------'''

    # Extracting the list of experiments:
    # experiment_list = [i for i in os.listdir(dir_exps) if '.' not in i]
    experiment_list = [dir_exps]

    # Extracting the list of analyses:
    analysis_list = os.listdir(dir_sdisc)
    analysis_list = [a for a in analysis_list if '.' not in a
                     and params['ana'] in a]

    # Extracting the elements created at the experiment stage:
    all_exp_data = {}
    for e in range(len(experiment_list)):  # *e* is for experiment
        exp_id = str(experiment_list[e].replace('Experiment_', ''))
        all_exp_data.update({exp_id: {}})

        exp_data_acc = dir_sdisc + params['experi_data'] + experiment_list[e]
        exp_data_list = os.listdir(exp_data_acc)
        for i in range(len(exp_data_list)):
            fn_exp_data = exp_data_acc + '/' + exp_data_list[i]
            this_exp_data = pickle.load(open(fn_exp_data, 'rb'))
            all_exp_data[exp_id].update({exp_data_list[i].split('.')[0]:
                                         this_exp_data})

    # Creating the compiled pickles with the results:
    pfd_comp = {}

    # Extracting what experiments and analyses to evaluate from the fcc:
    fn_prim_fcc = open(params['Prim_files_crea_cntrl'], 'rb')
    df_prim_fcc_match = pd.read_excel(fn_prim_fcc, sheet_name=params['Mat_exp_ana'])
    included_exps, included_anas = [], []
    included_exp2ana = {}
    for i in range(len(df_prim_fcc_match['exps'].tolist())):
        if (str(df_prim_fcc_match['include_exp'].tolist()[i]) == 'YES' and
                df_prim_fcc_match['exps'].tolist()[i] not in included_exps):
            included_exps.append(df_prim_fcc_match['exps'].tolist()[i])
            included_exp2ana.update({df_prim_fcc_match['exps'].tolist()[i]:
                                     []})

        if (str(df_prim_fcc_match['include_ana'].tolist()[i]) == 'YES' and
                df_prim_fcc_match['analyses'].tolist()[i] not in
                included_anas):
            included_anas.append(df_prim_fcc_match['analyses'].tolist()[i])
            pfd_comp.update({df_prim_fcc_match['analyses'].tolist()[i]: {}})

    for i in range(len(df_prim_fcc_match['exps'].tolist())):
        this_exp_int = df_prim_fcc_match['exps'].tolist()[i]
        this_ana_int = df_prim_fcc_match['analyses'].tolist()[i]
        if (this_exp_int in included_exps and this_ana_int in included_anas):
            included_exp2ana[this_exp_int].append(this_ana_int)
            pfd_comp[this_ana_int].update({this_exp_int: {}})
            # For convenience, *pfd_comp* has switched order

    # Extracting the periods to iterate across:
    df_prim_fcc_per = pd.read_excel(fn_prim_fcc, sheet_name=params['Periods'])
    period_control = {'period_list': df_prim_fcc_per['period_list'].tolist(),
                      'yr_ini': df_prim_fcc_per['year_initial'].tolist(),
                      'yr_fin': df_prim_fcc_per['year_final'].tolist()}
    fn_prim_fcc.close()  # close file once you do not need

    ''' ----------------------------------------------------------------------
        Step 1: read the pickle with the instructions of this task:
    i) what to read, ii) what to copy and paste,
    iii) how to group the data, iv) and what call the result.
        Objective: open the dictionary that controls this file's workflow.
        Source: "prim_files_creator.pickle" comes from dir 't3b_sdiscovery"
    -----------------------------------------------------------------------'''

    # Create the list of controlling files of admitted [scen disc] analyses:
    dict_pfcp, dict_set_matching = {}, {}

    # Opening this system's contolling dictionary per analysis:
    for ana in analysis_list:
        if int(ana.split('_')[-1]) in included_anas:
            ana_id = int(ana.split('_')[-1])

            pfc_path = dir_sdisc + '/' + ana
            fn_prim_files_creator = pfc_path + '/' + params['Prim_files_crea']
            pfc = pickle.load(open(fn_prim_files_creator, 'rb'))

            prim_manager = pfc['prim_manager']
            prim_manager_order = pfc['prim_manager_o']
            prim_files_creator_parallel = pfc['prim_fc_p']
            df_set_matching = pfc['set_matching']

            dict_pfcp.update({ana_id: prim_files_creator_parallel})
            dict_set_matching.update({ana_id: df_set_matching})

    ''' ----------------------------------------------------------------------
        Step 2: set up the process that opens up the folders
    (for reference, look at "Vulnerability_Analysis_Creator_Parallel.py")
        Objective: define the structure that opens and edits all the files
    of interest.
        Source: work inside the 't3a_experiments" folder.
    -----------------------------------------------------------------------'''
    print('PRIM files creation is configured.')
    # sys.exit()

    # Iterating across experiments
    for e in range(len(experiment_list)):  # *e* is for experiment
        if str(experiment_list[e].replace('Experiment_', '')) in included_exps:
            print('\n')
            exp_id = str(experiment_list[e].replace('Experiment_', ''))
            print('Processing files of Experiment_' + str(exp_id))

            # Opening directories:
            # Folder where execute the script
            base_dir = os.path.dirname(os.path.abspath(__file__))
                
            # dir_this_exp = dir_exps + '/' + experiment_list[e]
            dir_this_exp = os.path.join(base_dir, '..', experiment_list[e])
            dir_this_exp = os.path.abspath(dir_this_exp)
            # maybe update directory names later
            dir_fut0 = os.path.join(dir_this_exp, params['Executables'])
            dir_futs = os.path.join(dir_this_exp, params['Experi_Plat'], params['Futures'])

            # Specify what analyses need to be executed for this experiment:
            e_analysis_list = included_exp2ana[exp_id]

            # Opening the "fut 0" runs:
            list_fut0_runs_raw = os.listdir(dir_fut0)
            list_fut0_runs = [i for i in list_fut0_runs_raw
                              if ('py' not in i) and ('.csv' not in i)]

            # There are as many "fut 0" runs as scenarios;
            # creating the scenario list:
            list_scenarios = [s.split('_')[0] for s in list_fut0_runs]

            # Store the directories with files to compile:
            list_dirs_compile_dir = []

            # We can select each scenarios' future list:
            if len(e_analysis_list) != 0:
                for scen in list_scenarios:
                    dir_scen_fut = dir_futs + '/' + scen
                    list_scen_fut = os.listdir(dir_scen_fut)

                    # Updating the compiled results for each experiment,
                    # possible analysis ID, and per scenario:
                    for pos_ana_ind in e_analysis_list:
                        pfd_comp[pos_ana_ind][exp_id].update({scen: {}})

                    # Iterating across futures with a parallel implementation:
                    #   x: length of list of futures per scenario
                    #   batches: ratio of *# of runs* and *max_per_batch*
                    #   batches_ceiling: ceiling of iterables per batch of runs
                    num = len(list_scen_fut)
                    batches = (num + 1) / max_per_batch
                    batches_ceiling = math.ceil(batches)
                    for batch in range(0, batches_ceiling):
                        # Defining the processes to execute with *mp* later:
                        processes = []

                        # Calculating the first index to iterate:
                        n_ini = batch * max_per_batch

                        # Calculating the last index to iterate:
                        if n_ini + max_per_batch < num:
                            max_iter = n_ini + max_per_batch
                        else:
                            max_iter = num + 1

                        # Iterating to collect the *mp* processes:
                        for run in range(n_ini, max_iter):
                            # Store the future 0 in the first process
                            if run == 0:
                                specific_dir = os.path.join(dir_fut0, scen + '_0')
                                if scen != params['BAU'] or len(list_scenarios) == 1:  # store dir for compilation
                                    list_dirs_compile_dir.append(specific_dir)
                                specific_dir_elements = os.listdir(specific_dir
                                                                )
                                # print('ENTRO ACA')
                                # prueba=f1_create_prim_files(specific_dir_elements,
                                #       specific_dir, scen,
                                #       dict_pfcp,
                                #       e_analysis_list,
                                #       dict_set_matching,
                                #       period_control,
                                #       all_exp_data,
                                #       exp_id, params,dicPop)
                                # sys.exit(29)
                                
                                p = mp.Process(target=f1_create_prim_files,
                                               args=(specific_dir_elements,
                                                     specific_dir, scen,
                                                     dict_pfcp,
                                                     e_analysis_list,
                                                     dict_set_matching,
                                                     period_control,
                                                     all_exp_data,
                                                     exp_id, params,dicPop))

                                processes.append(p)
                                p.start()

                            # Store all futures' processes
                            else:
                                specific_dir = os.path.join(dir_futs, scen, list_scen_fut[run-1])
                                if scen != params['BAU'] or len(list_scenarios) == 1:  # store dir for compilation
                                    list_dirs_compile_dir.append(specific_dir)
                                specific_dir_elements = os.listdir(specific_dir
                                                                   )
                                # print('ENTRO ACA')
                                # sys.exit()
                                p = mp.Process(target=f1_create_prim_files,
                                               args=(specific_dir_elements,
                                                     specific_dir, scen,
                                                     dict_pfcp,
                                                     e_analysis_list,
                                                     dict_set_matching,
                                                     period_control,
                                                     all_exp_data,
                                                     exp_id, params, dicPop))
                                processes.append(p)
                                p.start()

                        for process in processes:
                            process.join()

                print('*: We have finished the work of the parallel '
                      + 'functions for Experiment_' + str(exp_id))
                print('Now compiling the files of Experiment_' +
                      str(exp_id))

                for adir in list_dirs_compile_dir:
                    all_files = os.listdir(adir)
                    pfd_file_list = [f for f in all_files if 'pfd' in f]
                    # This list contains 1 or more "pfd" files
                    for f in pfd_file_list:
                        ana_id = int(f.split('.')[0].split('_')[-1])

                        if ana_id in included_anas:
                            fut_id = int(f.split('.')[0].split('_')[-2])
                            the_scen = f.split('.')[0].split('_')[-3]

                            this_pfd_file = open(adir + '/' + f, 'rb')
                            this_pfd_dict = pickle.load(this_pfd_file)
                            this_pfd_file.close()

                            pfd_comp[ana_id
                                     ][exp_id
                                     ][the_scen
                                       ].update({fut_id: this_pfd_dict})

            else:
                print('Experiment_' + str(exp_id) + ' does not have assigned'
                      + '*analysis*; its runs will not be processed.')

    # Export the compiled PRIM analysis pickle files:
    for ana in analysis_list:
        ana_ID = int(ana.split('_')[-1])
        if ana_ID in included_anas:
            apply_dir = dir_sdisc + '/' + str(ana)
            apply_suffix = '_' + str(ana_ID)
            with open(apply_dir + '/comp_pfd' + apply_suffix + '.pickle',
                      'wb') as outf:
                pickle.dump(pfd_comp[ana_ID],
                            outf, protocol=pickle.HIGHEST_PROTOCOL)
            outf.close()

    with open(params['All_comp_pdf'], 'wb') as outf:
        pickle.dump(pfd_comp, outf, protocol=pickle.HIGHEST_PROTOCOL)
    outf.close()

    # Recording final time of execution:
    end_f = time.time()
    te_f = -start_1 + end_f  # te: time_elapsed
    print(str(te_f) + ' seconds /', str(te_f/60) + ' minutes')
    print('*: PRIM files creation and compilation is completed.')