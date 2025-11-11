# -*- coding: utf-8 -*-
"""
Created on Wed May  5 15:44:25 2021

@author: Luis Victor-Gallardo, Andrey Salazar-Vargas
"""

import pandas as pd
import os
import sys
from copy import deepcopy
import prim
import time
import pickle
import numpy as np
import matplotlib.pyplot as plt
# import ema_workbench  # standalone PRIM imported above is equivalent
# from ema_workbench.analysis import prim as prim_ema  # we don't actually need
from datetime import datetime

"""
SOURCES:
1. For dataframe creation from lists:
https://www.geeksforgeeks.org/create-a-pandas-dataframe-from-lists/ (code #6)
2. For dataframe normalization before PRIM:
https://towardsdatascience.com/data-normalization-with-pandas-and-scikit-learn-7c1cc6ed6475
"""


def intersection_2(lst1, lst2):
    return list(set(lst1) & set(lst2))


def intersection_3(lst1, lst2, lst3):
    return list(set(lst1) & set(lst2) & set(lst3))


def intersection_4(lst1, lst2, lst3, lst4):
    return list(set(lst1) & set(lst2) & set(lst3) & set(lst4))


def intersection_6(lst1, lst2, lst3, lst4, lst5, lst6):
    return list(set(lst1) & set(lst2) & set(lst3) & set(lst4) & set(lst5) &
                set(lst6))


def max_abs_scaling(df):  # this is the easiest scaling method
    norm_df = deepcopy(df)
    scale_factor = {}  # store this to later re-scale the results back to the
    # original value

    for col in norm_df.columns:
        scale_factor.update({col: float(norm_df[col].abs().max())})
        norm_df[col] = norm_df[col]/norm_df[col].abs().max()

    return norm_df, scale_factor


def min_max_scaling(df):  # this is convinient to deal with "Dep" thresh. type
    norm_df = deepcopy(df)
    # store these to later re-scale the results back to the original value
    scale_factor = {}
    scale_sum = {}
    scale_zero = {}

    for col in norm_df.columns:
        scale_factor.update({col:
                             deepcopy(float(norm_df[col].max() -
                                      norm_df[col].min()))
                             })
        scale_sum.update({col: deepcopy(norm_df[col].min())})

        try:
            if (norm_df[col].max() != 0 and norm_df[col].max() ==
                    norm_df[col].min()):
                scale_zero.update({col: 0})  # this won'r actually matter
            else:
                scale_zero.update({col: -1*deepcopy(norm_df[col].min())
                                   / deepcopy(float(norm_df[col].max() -
                                                    norm_df[col].min()))})
        except Exception:
            print('Debug 1')
            print(deepcopy(float(norm_df[col].max() - norm_df[col].min())))
            print(col)
            print(norm_df[col].max(), norm_df[col].min())
            sys.exit()

        norm_df[col] = (norm_df[col] - norm_df[col].min()) / \
            (norm_df[col].max() - norm_df[col].min())

    return norm_df, scale_factor, scale_sum, scale_zero


'''
Function 0 (f0): function that returns multiple options of a table, e.g.,
average across all sets or disaggregated by set.'''


def f0_clean_options(root_list):
    # Define *pure_options*:
    pure_options = [i for i in root_list if '_' not in i]

    exclude_in_disag = []
    for i in root_list:
        if (i.split('_')[0] not in exclude_in_disag and i.split('_')[0] in
                pure_options and i not in pure_options):
            exclude_in_disag.append(i.split('_')[0])
        elif (i.split('_')[0] not in exclude_in_disag and
              i not in pure_options):
            pure_options.append(i)

    # Define *disag_options* // disaggragated: with subtypes
    disag_options = [i for i in root_list if
                     (i in pure_options and i not in exclude_in_disag) or
                     i.count('_') > 0]

    return pure_options, disag_options


''' ///////////////////////////////////////////////////////////////////
Funtion 1 (f1): apply the PRIM process in the main for dependent drivers.
The goal is to report the best thresholds, measured as avg(density, coverage).
'''


def f1_prim_box_execute(o_thresh_list, outc_array, outc_list, inp_df,
                        scale_zero_float, py):
    # Create empty dictionaries:
    info_dict_1 = {}
    info_dict_2 = {}

    error_type_a = False
    error_type_b = False

    o_thresh_list_apply = [i for i in o_thresh_list if i != 'Dep']

    # Iterate across "o_thresh_list":
    for t in o_thresh_list_apply:
        # Avoid invalid data conditions:
        if scale_zero_float < min(outc_list) and t.lower() == 'zero':
            print('This condition (A) should almost never happen. ' +
                  'Inspect when it happens')
            error_type_a = True
        elif len(inp_df.columns.tolist()) == 0:
            print('This condition (B) should almost never happen. ' +
                  'Inspect when it happens')
            error_type_b = True
        else:  # act as usual
            # pick base numeric threshold in percentiles
            # // below a user-defined dictionary!!!
            num_thr_dict = {'high': 75, 'mid': 50, 'low': 25, 'zero': 0,
                            'high40': 40, 'high60': 60, 'high25': 25,
                            'low40': 40, 'low60': 60, 'low75': 75}
            type_thr_dict = {'high': ">", 'mid': ">", 'low': "<", 'zero': "<",
                             'high40': ">", 'high60': ">", 'high25': ">",
                             'low40': "<", 'low60': "<", 'low75': "<"}
            '''
            The logic for these threshold types are:
                High: find predictors of values greater than 75th percentile
                Mid: find predictors of values greater than 50th percentile
                Low: find predictors of values lower than 25th percentile
                Zero: find predictors of values lower than 0
            '''
            this_t = t.lower()
            # Below we add an exception for the handling of external thresholds
            if '_' not in this_t:  # this does not require external thlds.
                type_thr = type_thr_dict[this_t]
                num_thr = num_thr_dict[this_t]
                if num_thr == 0:
                    val_thr = scale_zero_float
                else:
                    val_thr = np.percentile(outc_array, num_thr)

            else:  # the goal here is to obtain the "type_thr" and "num_thr" strings
                # by hard-coded design, everything is set for 4 periods
                # this should be carefully modified in future versions for different periods
                this_e_string = this_t.split('+')[py]
                if this_e_string == 'skip':
                    type_thr = 'skip'  # this means there should be not action
                else:
                    this_e_info = this_e_string.replace('e', '').split('_')
                    type_thr = type_thr_dict[this_e_info[0]]
                    num_thr = 'none'
                    val_thr = float(this_e_info[-1])

            if '_' not in this_t or type_thr != 'skip':
                # Apply PRIM for standard threshold:
                try:
                    p = prim.Prim(inp_df, outc_list,
                                threshold=val_thr,
                                threshold_type=type_thr)
                    box = p.find_box()
                except Exception:
                    print('Debug 2')
                    print(val_thr, type_thr, type(inp_df), type(outc_list))
                    print(inp_df)
                    print(outc_list)
                    print(num_thr)
                    print(scale_zero_float)
                    print(np.percentile(outc_array, num_thr))
                    print(this_t)
                    print('\n')
                    sys.exit()
                # print(this_t,outc_list)
                # SELECTION CRITERIA: max(avg(coverage, density)) if dim == 2
                # if dim > 2, select the highest dim with coverages of at least
                # 0.7 ; then, out of that selected dim, apply index of
                # max(avg(coverage, density))
                x = box.peeling_trajectory
                xresdim = list(set(x['res dim'].tolist()))

                if len(xresdim) <= 2:  # at least 2 dimensions
                    mask = (x['res dim'].isin([int(len(xresdim))-1]))
                    local_x = x.loc[mask]
                    local_xidx = local_x.index.tolist()

                    local_xcov = local_x['coverage'].tolist()
                    local_xden = local_x['density'].tolist()
                    local_xmass = local_x['mass'].tolist()
                    local_xavg = [ (local_xcov[i] + local_xden[i] )/2 for i in range(len(local_xcov))]

                    maxxavgidx_local = local_xavg.index(max(local_xavg))
                    maxxavgidx_glob_idx = local_xidx[maxxavgidx_local]

                else:
                    for dim in xresdim:
                        mask = (x['res dim'].isin([dim]))
                        local_x = x.loc[mask]
                        local_xidx = local_x.index.tolist()

                        local_xcov = local_x['coverage'].tolist()
                        local_xden = local_x['density'].tolist()

                        if max(local_xcov) > 0.7:
                            use_dim = dim
                            local_xmass = local_x['mass'].tolist()
                            local_xavg = [ (local_xcov[i] + local_xden[i] )/2 for i in range(len(local_xcov))]

                            # This works as long as the *local_xcov* is in
                            # descending order
                            for lx in range(len(local_xcov)):
                                if local_xcov[lx] > 0.7:
                                    maxxavgidx_local_store = deepcopy(lx)
                                    maxxavgidx_local = maxxavgidx_local_store
                                else:
                                    maxxavgidx_local = maxxavgidx_local_store

                            # maxxavgidx_local = local_xavg.index(max(local_xavg))
                            maxxavgidx_glob_idx = local_xidx[maxxavgidx_local]

                box.select(maxxavgidx_glob_idx)
                

                base_cov = box.coverage
                base_den = box.density
                base_mer = (box.coverage+box.density)/2
                base_range = num_thr
                base_val_thr = val_thr
                base_limit_tbl = box.limits
                base_pred_d = base_limit_tbl.index.tolist()  # pred: predominant //
                
                
                # d: driver
                base_pred_d_min = [base_limit_tbl.loc[i, 'min'] for i in
                                base_pred_d]
                base_pred_d_max = [base_limit_tbl.loc[i, 'max'] for i in
                                base_pred_d]

                this_info_dict_1 = {'base_cov': base_cov, 'base_den': base_den,
                                    'base_mer': base_mer, 'base_range': base_range,
                                    'base_value_thld': base_val_thr,
                                    'base_limit_tbl': base_limit_tbl,
                                    'base_pred_d': base_pred_d,
                                    'base_pred_d_min': base_pred_d_min,
                                    'base_pred_d_max': base_pred_d_max}

                if '_' not in this_t:
                    info_dict_1.update({t: this_info_dict_1})
                else:
                    info_dict_1.update({'e' + this_e_info[0]: this_info_dict_1})
                    
    

    return info_dict_1, info_dict_2, error_type_a, error_type_b


''' ///////////////////////////////////////////////////////////////////
Funtion 1.2 (f1_2): create the string that reports the results.
Also append the final csv with all prim results.'''


def f1_2_rep_string_and_csv(info_dict_1, info_dict_2, rep_csv, b, o, o_name,
                            lvl, this_fam, this_col, per_name,
                            scale_factor_o, scale_sum_o, scale_zero_o,
                            scale_factor_i, scale_sum_i, scale_zero_i,
                            rel_driv, rel_driv_min, rel_driv_max,
                            rel_driv_tbase, rel_driv_t,
                            rel_driv_o_col, rel_driv_o_fam,
                            rel_driv_maxobase, qtype):
    # First, creare a list of strings that report the findings of the PRIM
    # algorithm
    astr_list = []

    # Second, unpack the info dicts:
    o_thresh_list = list(info_dict_1.keys())
    for t in o_thresh_list:
        base_cov = info_dict_1[t]['base_cov']
        base_den = info_dict_1[t]['base_den']
        base_mer = info_dict_1[t]['base_mer']
        base_range = info_dict_1[t]['base_range']
        base_val_thld = info_dict_1[t]['base_value_thld']
        base_pred_d = info_dict_1[t]['base_pred_d']  # pred: predictor
        base_pred_d_min = info_dict_1[t]['base_pred_d_min']  # normalized value
        base_pred_d_max = info_dict_1[t]['base_pred_d_max']

        # Here, take advantage of loop to write string:
        astr_list.append('         >> Column: ' + str(this_col) + ' // ' +
                         'Level: ' + str(lvl))
        astr_list.append('         >> Thld. type: ' + str(t) +
                         ' (base) // Thld. range: ' + str(base_range) +
                         ' // Thld. value: ' +
                         "{:.2e}".format(base_val_thld))
        astr_list.append('             >>> Coverage: ' + str(base_cov) + ' // '
                         + 'Density: ' + str(base_den) + ' // Avg(Cov, Den) : '
                         + str(base_mer))
        for n in range(len(base_pred_d)):
            min_val_real = base_pred_d_min[n] * scale_factor_i[base_pred_d[n]]\
                + scale_sum_i[base_pred_d[n]]
            max_val_real = base_pred_d_max[n] * scale_factor_i[base_pred_d[n]]\
                + scale_sum_i[base_pred_d[n]]
            astr_list.append('             >>> Driver: ' +
                             str(base_pred_d[n]) + ' // Min (norm): '
                             + "{:.2f}".format(base_pred_d_min[n])
                             + ' // Min (real): '
                             + "{:.2e}".format(min_val_real)
                             + ' // Max (norm): '
                             + "{:.2f}".format(base_pred_d_max[n])
                             + ' // Max (real): '
                             + "{:.2e}".format(max_val_real))

        rep_size_base = len(base_pred_d)  # rep: report

        # Store resulting drivers:
        rel_driv += deepcopy(base_pred_d)
        rel_driv_min += deepcopy(base_pred_d_min)
        rel_driv_max += deepcopy(base_pred_d_max)
        rel_driv_tbase += deepcopy([t for r in range(rep_size_base)])
        rel_driv_t += deepcopy([t for r in range(rep_size_base)])
        rel_driv_o_col += deepcopy([this_col for r in range(rep_size_base)])
        rel_driv_o_fam += deepcopy([this_fam for r in range(rep_size_base)])
        rel_driv_maxobase += deepcopy(['base' for r in range(rep_size_base)])

        # Create appropiate lists to append to general .csv table:
        rep_cov = deepcopy([base_cov for r in range(rep_size_base)])
        rep_den = deepcopy([base_den for r in range(rep_size_base)])
        rep_mer = deepcopy([base_mer for r in range(rep_size_base)])
        # mer: merit
        rep_range = deepcopy([base_range for r in range(rep_size_base)])
        rep_val_thld = deepcopy([base_val_thld for r in range(rep_size_base)])
        rep_pred_d = deepcopy(base_pred_d)
        rep_pred_d_min = deepcopy(base_pred_d_min)
        rep_pred_d_max = deepcopy(base_pred_d_max)
        rep_prim_opt = deepcopy(['base' for r in range(rep_size_base)])

        rep_size_max = 0
        '''
        if info_dict_2[t] != 'none':
            max_cov = info_dict_2[t]['max_cov']
            max_den = info_dict_2[t]['max_den']
            max_mer = info_dict_2[t]['max_mer']
            max_range = info_dict_2[t]['max_range']
            max_val_thld = info_dict_2[t]['max_value_thld']
            max_pred_d = info_dict_2[t]['max_pred_d']
            max_pred_d_min = info_dict_2[t]['max_pred_d_min']
            max_pred_d_max = info_dict_2[t]['max_pred_d_max']

            # Here, take advantage of loop to write string:
            astr_list.append('         >> Thld. type: ' + str(t) +
                             ' (max) // Thld. range: ' + str(base_range) +
                             ' // Thld. value: ' +
                             "{:.2e}".format(base_val_thld))
            astr_list.append('             >>> Coverage: ' + str(base_cov)
                             + ' // Density: ' + str(base_den) +
                             ' // Avg(Cov, Den) : ' + str(base_mer))
            for n in range(len(max_pred_d)):
                min_val_real = max_pred_d_min[n] * \
                    scale_factor_i[max_pred_d[n]] + scale_sum_i[max_pred_d[n]]
                max_val_real = max_pred_d_max[n] * \
                    scale_factor_i[max_pred_d[n]] + scale_sum_i[max_pred_d[n]]
                astr_list.append('             >>> Driver: '
                                 + str(max_pred_d[n])
                                 + ' // Min (norm): ' +
                                 "{:.2f}".format(max_pred_d_min[n])
                                 + ' // Min (real): ' +
                                 "{:.2e}".format(min_val_real)
                                 + ' // Max (norm): ' +
                                 "{:.2f}".format(max_pred_d_max[n])
                                 + ' // Max (real): ' +
                                 "{:.2e}".format(max_val_real))

            rep_size_max = len(max_pred_d)

            # Store resulting drivers:
            rel_driv += deepcopy(max_pred_d)
            rel_driv_min += deepcopy(max_pred_d_min)
            rel_driv_max += deepcopy(max_pred_d_max)
            rel_driv_t += deepcopy([t for r in range(rep_size_max)])
            rel_driv_o_col += deepcopy([this_col for r in range(rep_size_max)])
            rel_driv_o_fam += deepcopy([this_fam for r in range(rep_size_max)])
            rel_driv_maxobase += deepcopy(['max' for r in range(rep_size_max)])

            # Create appropiate lists to append to general .csv table:
            rep_cov += deepcopy([max_cov for r in range(rep_size_max)])
            rep_den += deepcopy([max_den for r in range(rep_size_max)])
            rep_mer += deepcopy([max_mer for r in range(rep_size_max)])
            rep_range += deepcopy([max_range for r in range(rep_size_max)])
            rep_val_thld += deepcopy([max_val_thld for r in range(rep_size_max)
                                      ])
            rep_pred_d += deepcopy(max_pred_d)
            rep_pred_d_min += deepcopy(max_pred_d_min)
            rep_pred_d_max += deepcopy(max_pred_d_max)
            rep_prim_opt += deepcopy(['max' for r in range(rep_size_max)])
        '''

        # Third, append the information in the general results table:
        for r in range(rep_size_base + rep_size_max):
            rep_csv['block'].append(b)
            rep_csv['o_id'].append(o)
            rep_csv['outcome'].append(o_name)
            rep_csv['level'].append(lvl)
            rep_csv['family'].append(this_fam)
            rep_csv['o1_fam'].append(this_fam)
            rep_csv['o1_col'].append(this_col)
            rep_csv['o2_fam'].append('')
            rep_csv['o2_col'].append('')
            rep_csv['column'].append(this_col)
            rep_csv['period'].append(per_name)
            rep_csv['base_thr'].append(t)
            rep_csv['thr_type'].append(t)
            rep_csv['thr_range'].append(rep_range[r])
            rep_csv['thr_value'].append(rep_val_thld[r] *
                                        scale_factor_o[this_col] +
                                        scale_sum_o[this_col])
            rep_csv['thr_value_norm'].append(rep_val_thld[r])
            rep_csv['prim_option'].append(rep_prim_opt[r])
            rep_csv['coverage'].append(rep_cov[r])
            rep_csv['density'].append(rep_den[r])
            rep_csv['avg_cov_dev'].append(rep_mer[r])
            rep_csv['driver_col'].append(rep_pred_d[r])
            rep_csv['min'].append(rep_pred_d_min[r] *
                                  scale_factor_i[rep_pred_d[r]] +
                                  scale_sum_i[rep_pred_d[r]])
            rep_csv['max'].append(rep_pred_d_max[r] *
                                  scale_factor_i[rep_pred_d[r]] +
                                  scale_sum_i[rep_pred_d[r]])
            rep_csv['min_norm'].append(rep_pred_d_min[r])
            rep_csv['max_norm'].append(rep_pred_d_max[r])
            rep_csv['query_type'].append(qtype)

    return astr_list, rep_csv, rel_driv, rel_driv_min, rel_driv_max, \
        rel_driv_tbase, rel_driv_t, rel_driv_o_col, rel_driv_o_fam, \
        rel_driv_maxobase


''' ///////////////////////////////////////////////////////////////////
Funtion 2 (f2): repeat the PRIM process in the main for dependent drivers.
This saves space and is useful because repetition is needed. '''


def f2_ipp(lvl, lvl_max, b, o, o_name, per_name, rep_csv, ad_df_grab,
           ad_col_fam_list, ad_col_fam_dict, ad, norm_min, norm_max, the_t,
           the_o1_col, the_o1_fam, the_o2_col, the_o2_fam,
           the_maxobase, rel_driv, rel_driv_min,
           rel_driv_max, rel_driv_tbase, rel_driv_t,
           rel_driv_o1_col, rel_driv_o1_fam, rel_driv_o2_col, rel_driv_o2_fam,
           rel_driv_maxobase, qtype):
    # Define the function's outcome:
    astr_list = []

    error_type_c = False
    if len(ad_col_fam_list) == 0:
        error_type_c = True
    error_type_d = False

    # Proceed by repeating the PRIM algorithm as in the main function:
    for fam in range(len(ad_col_fam_list)):
        this_fam = ad_col_fam_list[fam]
        o_pssbl_cols = ad_col_fam_dict['o'][fam]
        d_pssbl_cols = ad_col_fam_dict['d'][fam]

        this_df_raw = ad_df_grab[this_fam]

        # Filter the normalized dataframe:
        keys_IDs = ['Fut_ID', 'Run_Strat_ID', 'Scenario', 'Strat_ID']
        unique_strats = list(set(this_df_raw['Strat_ID']))
        if (len(unique_strats) == 2 and 'none' in
                unique_strats):
            this_df_raw_2 = this_df_raw.loc[(this_df_raw
                                             ['Strat_ID']
                                             != 'none')]
        else:
            this_df_raw_2 = this_df_raw

        use_cols = [i for i in this_df_raw_2.columns.tolist()
                    if i not in keys_IDs]
        this_df_raw_3 = this_df_raw_2[use_cols]
        this_df_raw_3 = this_df_raw_3.reset_index()

        this_df = this_df_raw_3.loc[:, (this_df_raw_3.sum(axis=0) != 0)]

        d_pssbl_cols_app = [i for i in d_pssbl_cols if i in
                            this_df.columns.tolist()]

        norm_df, scale_factor, scale_sum, scale_zero = min_max_scaling(this_df)

        inp_df_raw = norm_df[d_pssbl_cols_app]
        inp_df = inp_df_raw.dropna(axis=1, how='all')

        # Excluded columns could be reported in future versions:
        # exc_inp_df = inp_df_raw.loc[(inp_df_raw.sum(axis=0) == 0)]
        # exc_cols = exc_inp_df.columns().tolist()

        # we need to proceed only for the consulting column
        if ad in o_pssbl_cols and float(this_df_raw[ad].sum()) != 0:
            outc_list = norm_df[ad].tolist()

            # Selecting the direction of the new thresholds:
            diff_min = norm_min
            diff_max = 1 - norm_max

            # this means the sector must be lower than max
            if diff_min < diff_max:
                val_thr = norm_max
                num_thr = 100*norm_max
                type_thr = "<"
                t = 'Low'
            # this means the sector must be greater than min
            elif diff_max <= diff_min:
                val_thr = norm_min
                num_thr = 100*norm_min
                type_thr = ">"
                t = 'High'

            # Apply PRIM for standard threshold:
            try:               
                p = prim.Prim(inp_df, outc_list, threshold=val_thr,
                              threshold_type=type_thr)

                box = p.find_box()

                # SELECTION CRITERIA: max(avg(coverage, density)) if dim == 2
                # if dim > 2, select the highest dim with coverages of at least
                # 0.7 ; then, out of that selected dim, apply index of
                # max(avg(coverage, density))
                x = box.peeling_trajectory
                xresdim = list(set(x['res dim'].tolist()))

                if len(xresdim) <= 2:  # at least 2 dimensions
                    mask = (x['res dim'].isin([int(len(xresdim))-1]))
                    local_x = x.loc[mask]
                    local_xidx = local_x.index.tolist()

                    local_xcov = local_x['coverage'].tolist()
                    local_xden = local_x['density'].tolist()
                    local_xmass = local_x['mass'].tolist()
                    local_xavg = [ (local_xcov[i] + local_xden[i] )/2 for i in range(len(local_xcov))]

                    maxxavgidx_local = local_xavg.index(max(local_xavg))
                    maxxavgidx_glob_idx = local_xidx[maxxavgidx_local]

                else:
                    for dim in xresdim:
                        mask = (x['res dim'].isin([dim]))
                        local_x = x.loc[mask]
                        local_xidx = local_x.index.tolist()

                        local_xcov = local_x['coverage'].tolist()
                        local_xden = local_x['density'].tolist()

                        if max(local_xcov) > 0.7:
                            use_dim = dim
                            local_xmass = local_x['mass'].tolist()
                            local_xavg = [ (local_xcov[i] + local_xden[i] )/2 for i in range(len(local_xcov))]

                            # This works as long as the *local_xcov* is in
                            # descending order
                            for lx in range(len(local_xcov)):
                                if local_xcov[lx] > 0.7:
                                    maxxavgidx_local_store = deepcopy(lx)
                                    maxxavgidx_local = maxxavgidx_local_store
                                else:
                                    maxxavgidx_local = maxxavgidx_local_store

                            # maxxavgidx_local = local_xavg.index(max(local_xavg))
                            maxxavgidx_glob_idx = local_xidx[maxxavgidx_local]

                box.select(maxxavgidx_glob_idx)

                base_cov = box.coverage
                base_den = box.density
                base_mer = (box.coverage+box.density)/2
                base_range = num_thr
                base_val_thld = val_thr
                base_limit_tbl = box.limits
                base_pred_d = base_limit_tbl.index.tolist()
                # pred: predominant //
                # d: driver
                base_pred_d_min = [base_limit_tbl.loc[i, 'min'] for i in
                                   base_pred_d]
                base_pred_d_max = [base_limit_tbl.loc[i, 'max'] for i in
                                   base_pred_d]

                # Here, take advantage of loop to write string:
                astr_list.append('         >> Column: ' + str(ad) +
                                 ' // Level: ' + str(lvl) + ' // Dependency: '
                                 + str(the_o1_col))
                astr_list.append('         >> Thld. type: ' + str(t) +
                                 ' (dep) // Thld. range: ' + str(base_range) +
                                 ' // Thld. value: ' +
                                 "{:.2e}".format(base_val_thld))
                astr_list.append('             >>> Coverage: ' + str(base_cov)
                                 + ' // Density: ' + str(base_den) +
                                 ' // Avg(Cov, Den) : ' + str(base_mer))
                for n in range(len(base_pred_d)):
                    min_val_real = base_pred_d_min[n] * \
                        scale_factor[base_pred_d[n]] + \
                        scale_sum[base_pred_d[n]]
                    max_val_real = base_pred_d_max[n] * \
                        scale_factor[base_pred_d[n]] + \
                        scale_sum[base_pred_d[n]]
                    astr_list.append('             >>> Driver: ' +
                                     str(base_pred_d[n])
                                     + ' // Min (norm): ' +
                                     "{:.2e}".format(base_pred_d_min[n])
                                     + ' // Min (real): ' +
                                     "{:.2e}".format(min_val_real)
                                     + ' // Max (norm): ' +
                                     "{:.2e}".format(base_pred_d_max[n])
                                     + ' // Max (real): ' +
                                     "{:.2e}".format(max_val_real))

                rep_size_base = len(base_pred_d)  # rep: report

                # Store resulting drivers:
                if lvl < lvl_max:  # WARNING!!! This is a user-defined entry
                    rel_driv += base_pred_d
                    rel_driv_min += base_pred_d_min
                    rel_driv_max += base_pred_d_max
                    rel_driv_tbase += [the_t for r in range(rep_size_base)]
                    rel_driv_t += [t for r in range(rep_size_base)]
                    rel_driv_o1_col += \
                        [the_o1_col for r in range(rep_size_base)]
                    rel_driv_o1_fam += \
                        [the_o1_fam for r in range(rep_size_base)]
                    rel_driv_o2_col += [ad for r in range(rep_size_base)]
                    rel_driv_o2_fam += [this_fam for r in range(rep_size_base)]
                    rel_driv_maxobase += [the_maxobase for r in
                                          range(rep_size_base)]
                else:  # just complete the function returns
                    rel_driv, rel_driv_min, rel_driv_max, rel_driv_t, \
                        rel_driv_o1_col, rel_driv_o1_fam, \
                        rel_driv_o2_col, rel_driv_o2_fam, \
                        rel_driv_maxobase = \
                        [], [], [], [], [], [], [], [], []

                # Create appropiate lists to append to general .csv table:
                rep_cov = [base_cov for r in range(rep_size_base)]
                rep_den = [base_den for r in range(rep_size_base)]
                rep_mer = [base_mer for r in range(rep_size_base)]
                # mer: merit
                rep_range = [base_range for r in range(rep_size_base)]
                rep_val_thld = [base_val_thld for r in range(rep_size_base)]
                rep_pred_d = deepcopy(base_pred_d)
                rep_pred_d_min = deepcopy(base_pred_d_min)
                rep_pred_d_max = deepcopy(base_pred_d_max)
                rep_prim_opt = [the_maxobase for r in range(rep_size_base)]

                # Append the information in the general results table:
                for r in range(rep_size_base):
                    rep_csv['block'].append(b)
                    rep_csv['o_id'].append(o)
                    rep_csv['outcome'].append(o_name)
                    rep_csv['level'].append(lvl)
                    if lvl == 2:
                        rep_csv['o1_fam'].append(the_o1_fam)
                        rep_csv['o1_col'].append(the_o1_col)
                        rep_csv['o2_fam'].append('')
                        rep_csv['o2_col'].append('')
                    if lvl == 3:
                        rep_csv['o1_fam'].append(the_o1_fam)
                        rep_csv['o1_col'].append(the_o1_col)
                        rep_csv['o2_fam'].append(the_o2_fam)
                        rep_csv['o2_col'].append(the_o2_col)
                    rep_csv['family'].append(this_fam)
                    rep_csv['column'].append(ad)
                    rep_csv['period'].append(per_name)
                    rep_csv['base_thr'].append(the_t)
                    rep_csv['thr_type'].append(t)
                    rep_csv['thr_range'].append(rep_range[r])
                    rep_csv['thr_value'].append(rep_val_thld[r] *
                                                scale_factor[ad] +
                                                scale_sum[ad])
                    rep_csv['thr_value_norm'].append(rep_val_thld[r])
                    rep_csv['prim_option'].append(rep_prim_opt[r])
                    # only relates to the related outcome
                    rep_csv['coverage'].append(rep_cov[r])
                    rep_csv['density'].append(rep_den[r])
                    rep_csv['avg_cov_dev'].append(rep_mer[r])
                    rep_csv['driver_col'].append(rep_pred_d[r])
                    rep_csv['min'].append(rep_pred_d_min[r] *
                                          scale_factor[rep_pred_d[r]] +
                                          scale_sum[rep_pred_d[r]])
                    rep_csv['max'].append(rep_pred_d_max[r] *
                                          scale_factor[rep_pred_d[r]] +
                                          scale_sum[rep_pred_d[r]])
                    rep_csv['min_norm'].append(rep_pred_d_min[r])
                    rep_csv['max_norm'].append(rep_pred_d_max[r])
                    rep_csv['query_type'].append(qtype)

            except Exception:
                astr_list.append('         >> Column: ' + str(ad) +
                                 ' // Level: ' + str(lvl) + ' // Dependency: '
                                 + str(the_o1_col))
                astr_list.append('         >> Has equal Min. (' + str(norm_min)
                                 + ') and Max. (' + str(norm_max) + '). Hence,'
                                 + ' PRIM is not applied.')

        else:
            error_type_d = True

    return astr_list, rep_csv, rel_driv, rel_driv_min, rel_driv_max, \
        rel_driv_tbase, rel_driv_t, rel_driv_o1_col, rel_driv_o1_fam, \
        rel_driv_o2_col, rel_driv_o2_fam, \
        rel_driv_maxobase, error_type_c, error_type_d


if __name__ == '__main__':
    """
    *Abbreviations:*
    dict: dictionary
    fn: filename
    lld: local_data_dict
    pfd: prim_files_dictionary
    pfc: prim_files_creator
    norm: normalized
    """

    # WARNING!!! The list below contains the period strings to make running
    # this program faster.
    '''
    period_list = [ '25-29',
                    '30-36',
                    '37-43',
                    '44-50']
    '''
    # period_list = [ '23-30',
    #                 '31-50',
    #                 '51-70',
    #                 '23-50',
    #                 '23-70',
    #                 '31-40',
    #                 '41-50',
    #                 '51-60',
    #                 '61-70']
    
    # period_list = [ '23-30',
    #                 '31-50',
    #                 '23-50',
    #                 '31-40',
    #                 '41-50',
    #                 '24-27',
    #                 '28-35',
    #                 '36-50',
    #                 '24-50']
    period_list = [ '21-30',
                    '31-40',
                    '41-50'
                    ]



    '''
    General aim: to be able to perform any prim analysis without inputs other
    than the Analysis data (this means, no external controls).
    '''

    ''' ----------------------------------------------------------------------
    Step 1: Open the analysis pickles according to each analysis
    Objective: control access to the controlling dictionaries and the data
    -----------------------------------------------------------------------'''

    # Recording initial time of execution
    start_1 = time.time()

    # datetime object containing current date and time
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    # For a complete record of the prim manager execution, write a report with
    # all the prints in this system:
    pmrep_name = 'sd_manager.txt'
    pmrep = open(pmrep_name, 'w+')
    pmrep.write(dt_string + '\n')

    # These are all the analyses defined in the system:
    analysis_list = [a for a in os.listdir() if '.' not in a and 'Analysis' in
                     a]

    # The default analyses to iterate are all in *analysis_list*;
    # manually enter a custom and valid list to extract the data
    # list_ana_iter = analysis_list  # !!!Alternatively define any [int]!!!
    # list_ana_iter_int = [1, 2, 3]
    list_ana_iter_int = [1]
    # list_ana_iter_int = [2]  # USER ENTRY
    list_ana_iter = ['Analysis_' + str(i) for i in list_ana_iter_int]

    # Let's iterate across analysis:
    for ana in list_ana_iter:
        add_str = '1. Performing analysis for ' + ana + '. Opening all data.'
        print(add_str)
        pmrep.write(add_str + '\n')

        ana_pickle_list = [p for p in os.listdir('./' + ana) if 'pickle' in p]

        ana_ID = int(ana.split('_')[-1])

        fn_comp_pfd = [i for i in ana_pickle_list if 'pfd' in i][0]
        # fn_comp_pfd = [i for i in ana_pickle_list if 'pfd' in i and '_2' in i][0]  # WARNING!!! Provisional hack to use another PC
        fn_prim_fc = [i for i in ana_pickle_list if 'files_creator' in i][0]

        acc_comp_pfd = './' + ana + '/' + fn_comp_pfd
        acc_prim_fc = './' + ana + '/' + fn_prim_fc

        file_comp_pfd = open(acc_comp_pfd, 'rb')
        comp_pfd = pickle.load(file_comp_pfd)
        file_comp_pfd.close()

        file_prim_fc = open(acc_prim_fc, 'rb')
        prim_fc = pickle.load(file_prim_fc)
        file_comp_pfd.close()

        # Extract block-outcome-driver nest:
        prim_manager = prim_fc['prim_manager']

        # Extract number of cols in each block-outcome-driver nest:
        prim_manager_o = prim_fc['prim_manager_o']

        # Extract the outcome and driver specifications across outcome IDs:
        specs_ao_outcome = prim_fc['prim_fc_p']['Outcome']
        specs_ao_driver = prim_fc['prim_fc_p']['Driver']

        # Extract the data specifications across unique driver ID:
        specs_udriver = prim_fc['prim_fc_p']['Driver_U']

        add_str = '     > Data is open.'
        print(add_str)
        pmrep.write(add_str)

        # The default experiments to iterate are all comp_pfd.keys();
        # manually enter a custom and valid list to extract the data
        '''
        list_exp_iter = list(comp_pfd.
                             keys())  # !!!Alternatively define any [int]!!!
        '''
        list_exp_iter = ['1_Experiment']  # USER ENTRY
        add_str = '\n2. We will now iterate across experiments: '
        print(add_str, list_exp_iter)
        pmrep.write(add_str)
        for listitem in list_exp_iter:
            pmrep.write(' %s,' % listitem)
        pmrep.write('\n')

        for exp_ID in list_exp_iter:
            add_str = '\n=> We are working with Experiment: ' + str(exp_ID)
            print(add_str)
            pmrep.write(add_str + '\n')

            add_str = '3. Creating the analysis/experiment report. ' + \
                'We populate the report below.'
            print(add_str)
            pmrep.write(add_str + '\n')

            this_report_name = 'sd_ana_' + str(ana_ID
                                               ) + '_exp_' + str(exp_ID
                                                                 ) + '.txt'
            this_report = open(this_report_name, 'w+')
            this_report.write('This is a PRIM analysis. The Analysis ID is: '
                              + str(ana_ID) + ' // The Experiment ID is: '
                              + str(exp_ID) + '\n\n')
            # NOTE: future versions of this implementation could include other
            # algorithms such as CART

            # Select the data linked to the experiment
            add_str = '4. Selecting the data to create tables'
            print(add_str)
            pmrep.write(add_str + '\n')
            use_pfd = comp_pfd[exp_ID]['Scenario1']
            future_list = list(use_pfd.keys())
            future_list.sort()

            # > We will first extract the data and then perform the analysis
            # > A figure-creation analysis would be very similar to the loop
            # below
            # > So now, let's create the data to first store and perform
            # analysis after
            subtbl = {}  # stores the subtable data by block and outcome
            o_dep_name = []  # useful to call subtable
            o_dep_o_col = []  # bis
            o_dep_block_id = []  # bis
            o_dep_o_id = []  # bis
            subtbl_col_cntrl = {}  # helps manage column names

            # Now, we divide the report into "blocks" to give structure
            list_blocks = list(prim_manager_o.keys())
            add_str = '5. Iterating across analysis blocks: '
            print(add_str)
            pmrep.write(add_str + '\n')
            for b in list_blocks:
                add_str = '\n===> Analyzing block: ' + str(b)
                print(add_str)
                pmrep.write(add_str + '\n')

                # appending the block key to data controller:
                subtbl.update({b: {}})
                subtbl_col_cntrl.update({b: {}})

                # Iterate across outcomes:

                list_outcomes = list(prim_manager_o[b].keys())
                for o in list_outcomes:
                    o_name = prim_manager['Outcome'
                                          ][b][o]['Name'
                                                  ][0]  # list of length 1
                    o_thresh_raw = prim_manager['Outcome'
                                                ][b
                                                  ][o
                                                    ]['Threshold'
                                                      ][0
                                                        ]  # list of length 1

                    # appending the block key to data controller:
                    subtbl[b].update({o: {}})
                    subtbl_col_cntrl[b].update({o: {}})

                    o_cols_list = prim_manager['Outcome'][b][o]['Cols'][0]
                    add_str = '\n     => Analyzing outcome (table): ' + \
                        str(o) + ' // ' + o_name
                    print(add_str)
                    pmrep.write(add_str + '\n')

                    # Define dictionary with data appending all the futures:
                    # - use a per-period basis:
                    o_data_dict_per = {}
                    for fut in future_list:
                        o_data_per_period = use_pfd[fut]['o'][o]
                        # this dictionary depends on the periods

                        # Iterating across periods:
                        per_list = list(o_data_per_period.keys())
                        # de-activate running the entire list // we need the
                        # entire list here
                        # per_list = period_list
                        for py in range(len(per_list)):
                            per_name = per_list[py]
                            lld = {fut: o_data_per_period[per_name]}
                            if fut == 0:  # using an internal source of periods
                                o_data_dict_per.update({per_name: lld})
                            else:
                                o_data_dict_per[per_name].update(lld)

                    # Define dictionary with data appending all the futures:
                    # - use a per-period basis AND a per-driver basis:
                    d_data_dict_per = {}
                    d_cols_list_dict = {}

                    # Iterate across drivers:
                    list_drivers = prim_manager['Driver'][b][o]['Name']
                    add_str = '     The associated drivers are: '
                    print(add_str)
                    pmrep.write(add_str)
                    for listitem in list_drivers:
                        pmrep.write(' %s,' % listitem)
                    pmrep.write('\n')

                    for d in range(len(list_drivers)):
                        d_name = list_drivers[d]
                        d_cols_list = prim_manager['Driver'][b][o]['Cols'][d]
                        d_cols_list_dict.update({d_name: d_cols_list})

                        # We have the task of finding what *unique_driver*
                        # to extract
                        spec_driver_raw = specs_ao_driver[o][d]
                        u_d_ID = spec_driver_raw['u_d_ID']
                        o_as_d_ID = spec_driver_raw['o_as_d_ID']

                        for fut in future_list:
                            if u_d_ID != 0:  # extract unique driver
                                d_data_per_period = use_pfd[fut]['d'][u_d_ID]
                            elif o_as_d_ID != 0:  # extract outcome as driver
                                d_data_per_period = use_pfd[fut
                                                            ]['o'][o_as_d_ID]
                            # this dictionary depends on the periods

                            # Iterating across periods:
                            per_list = list(d_data_per_period.keys())
                            # de-activate running the entire list // we need
                            # the entire list here
                            # per_list = period_list
                            for py in range(len(per_list)):
                                per_name = per_list[py]
                                lld = {fut: d_data_per_period[per_name]}
                                if fut == 0:
                                    # Do this to manage multiple drivers:
                                    if d == 0:  # avoid overlapping
                                        d_data_dict_per.update({per_name: {}})
                                    d_data_dict_per[per_name].update({d_name:
                                                                      lld})
                                else:
                                    d_data_dict_per[per_name][d_name
                                                              ].update(lld)

                    add_str = \
                        '     6. Creating analysis tables for each period'
                    print(add_str)
                    pmrep.write(add_str + '\n')
                    # NOTE: !!!Add cross-period features!!!
                    per_list = list(o_data_dict_per.keys())
                    # de-activate running the entire list // we need the
                    # entire list here
                    # per_list = period_list
                    for py in range(len(per_list)):
                        per_name = per_list[py]

                        add_str = '     => Crating tables for period: ' + \
                            str(per_name)
                        print(add_str)
                        pmrep.write(add_str + '\n')

                        add_str = '         > Grouping headers'
                        print(add_str)
                        pmrep.write(add_str + '\n')
                        # First, we need some column assortment //
                        # consult future_0 for this
                        o_data = o_data_dict_per[per_name]  # remember: o_name

                        o_cols_list_direct = [i for i in o_cols_list
                                              if 'direct' in i]
                        o_cols_list_wrtBAU = [i for i in o_cols_list
                                              if 'wrtBAU' in i]
                        o_cols_list_root = [i.replace('_direct', '') for i in
                                            o_cols_list_direct]
                        # If the strings does not have a '_direct', the root
                        # will be empty. Let's add 'wrtBAU' cases:
                        if len(o_cols_list_root) == 0:
                            o_cols_list_root = [i.replace('_wrtBAU', '') for i
                                                in o_cols_list_wrtBAU]
                        o_cols_opt_pure, o_cols_opt_disag = \
                            f0_clean_options(o_cols_list_root)

                        d_data = d_data_dict_per[per_name]

                        d_cols_list_direct = []
                        d_cols_list_wrtBAU = []
                        d_cols_list_root = []
                        for a_driver in list(d_data.keys()):
                            d_cols_list = d_cols_list_dict[a_driver]

                            # Extracting direct columns of drivers:
                            d_cols_ld_local = [i for i in d_cols_list
                                               if 'direct' in i]

                            d_cols_list_direct += [acol for acol in
                                                   d_cols_ld_local if acol not
                                                   in d_cols_list_direct]

                            # Extracting wrtBAU columns of drivers:
                            d_cols_lwb_local = [i for i in d_cols_list
                                                if 'wrtBAU' in i]

                            d_cols_list_wrtBAU += [acol for acol in
                                                   d_cols_lwb_local if acol not
                                                   in d_cols_list_direct]

                            # Extracting root columns of drivers:
                            d_cols_lr_local = [i.replace('_direct', '')
                                               for i in d_cols_ld_local]
                            if len(d_cols_lr_local) == 0:
                                d_cols_lr_local = [i.replace('_wrtBAU', '')
                                                   for i in d_cols_lwb_local]

                            d_cols_list_root += [acol for acol in
                                                 d_cols_lr_local if acol not in
                                                 d_cols_list_root]

                        d_cols_opt_pure, d_cols_opt_disag = \
                            f0_clean_options(d_cols_list_root)

                        # use these conditions later to reduce number of tables
                        # (o_cols_opt_pure == o_cols_opt_disag)
                        # (d_cols_opt_pure == d_cols_opt_disag)
                        '''
                        TECHNICAL NOTE:
                            > We must now create a number of possible
                            combinations for our tables.
                            > The logic is to define 4 outcomes and 4 drivers:
                                pure_direct // pure_wrtBAU //
                                disag_direct // disag_wrtBAU
                            > That gives a total of 16 tables (as a max)
                            > Most likely, this is true:
                                pure_direct == disag_direct; hence, 8 tables
                            > We must ID the tables depending on the avialable
                            combinations
                        '''
                        o_cols_pure_direct = [i for i in o_cols_list_direct
                                              if i.replace('_direct', '')
                                              in o_cols_opt_pure]
                        o_cols_disag_direct = [i for i in o_cols_list_direct
                                               if i.replace('_direct', '')
                                               in o_cols_opt_disag]
                        o_cols_pure_wrtBAU = [i for i in o_cols_list_wrtBAU
                                              if i.replace('_wrtBAU', '')
                                              in o_cols_opt_pure]
                        o_cols_disag_wrtBAU = [i for i in o_cols_list_wrtBAU
                                               if i.replace('_wrtBAU', '')
                                               in o_cols_opt_disag]

                        d_cols_pure_direct = [i for i in d_cols_list_direct
                                              if i.replace('_direct', '')
                                              in d_cols_opt_pure]
                        d_cols_disag_direct = [i for i in d_cols_list_direct
                                               if i.replace('_direct', '')
                                               in d_cols_opt_disag]
                        d_cols_pure_wrtBAU = [i for i in d_cols_list_wrtBAU
                                              if i.replace('_wrtBAU', '')
                                              in d_cols_opt_pure]
                        d_cols_disag_wrtBAU = [i for i in d_cols_list_wrtBAU
                                               if i.replace('_wrtBAU', '')
                                               in d_cols_opt_disag]

                        # Above we defined all the column names, now let's
                        # combine them
                        o_d_col_fam_list = []
                        o_d_col_fam_list_names = []
                        o_d_col_fam_dict = {'o': [], 'd': []}
                        o_d_col_fam_dict_names = {'o': [], 'd': []}

                        # Possible family of outcomes:
                        if (o_cols_opt_pure == o_cols_opt_disag):
                            if (len(o_cols_list_direct) != 0
                                    and len(o_cols_list_wrtBAU) != 0):
                                oc_iterate = [o_cols_pure_direct,
                                              o_cols_pure_wrtBAU]
                                oc_names = ['pure_direct', 'pure_wrtBAU']
                            elif len(o_cols_list_direct) == 0:
                                oc_iterate = [o_cols_pure_wrtBAU]
                                oc_names = ['pure_wrtBAU']
                            elif len(o_cols_list_wrtBAU) == 0:
                                oc_iterate = [o_cols_pure_direct]
                                oc_names = ['pure_direct']
                        else:  # "pure" and "disag" are different
                            if (len(o_cols_list_direct) != 0
                                    and len(o_cols_list_wrtBAU) != 0):
                                oc_iterate = [o_cols_pure_direct,
                                              o_cols_disag_direct,
                                              o_cols_pure_wrtBAU,
                                              o_cols_disag_wrtBAU]
                                oc_names = ['pure_direct', 'disag_direct',
                                            'pure_wrtBAU', 'disag_wrtBAU']
                            elif len(o_cols_list_direct) == 0:
                                oc_iterate = [o_cols_pure_wrtBAU,
                                              o_cols_disag_wrtBAU]
                                oc_names = ['pure_wrtBAU', 'disag_wrtBAU']
                            elif len(o_cols_list_wrtBAU) == 0:
                                oc_iterate = [o_cols_pure_direct,
                                              o_cols_disag_direct]
                                oc_names = ['pure_direct', 'disag_direct']

                        # Add-on for drvers here:
                        #       If there are direct roots not in wrtBAU roots,
                        # we should combine them so that the table subtypes
                        # are as comparable as possible.
                        # - 1) Pure direct grabs from pure wrtBAU:
                        d_cols_pwb_ref = deepcopy(d_cols_pure_wrtBAU)
                        d_cols_pd_ref = deepcopy(d_cols_pure_direct)
                        d_cols_dwb_ref = deepcopy(d_cols_disag_wrtBAU)
                        d_cols_dd_ref = deepcopy(d_cols_disag_direct)

                        d_cols_pd_roots = [acol.replace('_direct', '') for
                                           acol in d_cols_pure_direct]
                        for acol in d_cols_pwb_ref:
                            if acol.replace('_wrtBAU', '') not in \
                                    d_cols_pd_roots:
                                d_cols_pure_direct.append(acol)

                        # - 2) Pure wrtBAU grabs from pure direct:
                        d_cols_pwb_roots = [acol.replace('_wrtBAU', '') for
                                            acol in d_cols_pure_wrtBAU]
                        for acol in d_cols_pd_ref:
                            if acol.replace('_direct', '') not in \
                                    d_cols_pwb_roots:
                                d_cols_pure_wrtBAU.append(acol)

                        # - 3) Disag direct grabs from disag wrtBAU:
                        d_cols_dd_roots = [acol.replace('_direct', '') for
                                           acol in d_cols_disag_direct]
                        for acol in d_cols_dwb_ref:
                            if acol.replace('_wrtBAU', '') not in \
                                    d_cols_dd_roots:
                                d_cols_disag_direct.append(acol)

                        # - 4) Disag wrtBAU grabs from disag direct:
                        d_cols_dwb_roots = [acol.replace('_wrtBAU', '') for
                                            acol in d_cols_disag_wrtBAU]
                        for acol in d_cols_dd_ref:
                            if acol.replace('_direct', '') not in \
                                    d_cols_dwb_roots:
                                d_cols_disag_wrtBAU.append(acol)

                        # Possible family of drivers
                        if (d_cols_opt_pure == d_cols_opt_disag):
                            if (len(d_cols_list_direct) != 0
                                    and len(d_cols_list_wrtBAU) != 0):
                                dc_iterate = [d_cols_pure_direct,
                                              d_cols_pure_wrtBAU]
                                dc_names = ['pure_direct', 'pure_wrtBAU']
                            elif len(d_cols_list_direct) == 0:
                                dc_iterate = [d_cols_pure_wrtBAU]
                                dc_names = ['pure_wrtBAU']
                            elif len(d_cols_list_wrtBAU) == 0:
                                dc_iterate = [d_cols_pure_direct]
                                dc_names = ['pure_direct']
                        else:  # "pure" and "disag" are different
                            if (len(d_cols_list_direct) != 0
                                    and len(d_cols_list_wrtBAU) != 0):
                                dc_iterate = [d_cols_pure_direct,
                                              d_cols_disag_direct,
                                              d_cols_pure_wrtBAU,
                                              d_cols_disag_wrtBAU]
                                dc_names = ['pure_direct', 'disag_direct',
                                            'pure_wrtBAU', 'disag_wrtBAU']
                            elif len(d_cols_list_direct) == 0:
                                dc_iterate = [d_cols_pure_wrtBAU,
                                              d_cols_disag_wrtBAU]
                                dc_names = ['pure_wrtBAU', 'disag_wrtBAU']
                            elif len(d_cols_list_wrtBAU) == 0:
                                dc_iterate = [d_cols_pure_direct,
                                              d_cols_disag_direct]
                                dc_names = ['pure_direct', 'disag_direct']

                        # Possible family of drivers
                        if (d_cols_opt_pure == d_cols_opt_disag):
                            if (len(d_cols_list_direct) != 0
                                    and len(d_cols_list_wrtBAU) != 0):
                                dc_iterate = [d_cols_pure_direct,
                                              d_cols_pure_wrtBAU]
                                dc_names = ['pure_direct', 'pure_wrtBAU']
                            elif len(d_cols_list_direct) == 0:
                                dc_iterate = [d_cols_pure_wrtBAU]
                                dc_names = ['pure_wrtBAU']
                            elif len(d_cols_list_wrtBAU) == 0:
                                dc_iterate = [d_cols_pure_direct]
                                dc_names = ['pure_direct']
                        else:  # "pure" and "disag" are different
                            if (len(d_cols_list_direct) != 0
                                    and len(d_cols_list_wrtBAU) != 0):
                                dc_iterate = [d_cols_pure_direct,
                                              d_cols_disag_direct,
                                              d_cols_pure_wrtBAU,
                                              d_cols_disag_wrtBAU]
                                dc_names = ['pure_direct', 'disag_direct',
                                            'pure_wrtBAU', 'disag_wrtBAU']
                            elif len(d_cols_list_direct) == 0:
                                dc_iterate = [d_cols_pure_wrtBAU,
                                              d_cols_disag_wrtBAU]
                                dc_names = ['pure_wrtBAU', 'disag_wrtBAU']
                            elif len(d_cols_list_wrtBAU) == 0:
                                dc_iterate = [d_cols_pure_direct,
                                              d_cols_disag_direct]
                                dc_names = ['pure_direct', 'disag_direct']

                        # Creating the families:
                        for oc in range(len(oc_iterate)):
                            for dc in range(len(dc_iterate)):
                                o_d_col_fam_list.append(oc_iterate[oc]
                                                        + dc_iterate[dc])
                                o_d_col_fam_list_names.append(
                                    'o_' + oc_names[oc] +
                                    '_d_' + dc_names[dc])
                                o_d_col_fam_dict['o'].append(oc_iterate[oc])
                                o_d_col_fam_dict['d'].append(dc_iterate[dc])
                                o_d_col_fam_dict_names['o'].append(oc_names[oc
                                                                            ])
                                o_d_col_fam_dict_names['d'].append(dc_names[dc
                                                                            ])
                        add_str = '         > A total of ' + \
                            str(len(o_d_col_fam_list)) + \
                            ' sub-tables are required.'
                        print(add_str)
                        pmrep.write(add_str + '\n')

                        add_str = \
                            '         > Extracting large table (all columns)'
                        print(add_str)
                        pmrep.write(add_str + '\n')

                        keys_IDs = ['Fut_ID', 'Run_Strat_ID', 'Scenario',
                                    'Strat_ID']
                        dict_large_table = {'Fut_ID': [], 'Run_Strat_ID': [],
                                            'Scenario': [], 'Strat_ID': []}
                        for fut in future_list:
                            # Extracting all the available IDs:
                            fut_ID_list = o_data[fut]['Fut_ID']
                            run_strat_ID_list = o_data[fut]['Run_Strat_ID']
                            scenario_list = o_data[fut]['Scenario']
                            strat_list = o_data[fut]['Strat_ID']

                            # Storing the IDs is done below (after checking
                            # positive matching IDs for outcomes and drivers)

                            # Extracting data column names
                            o_data_local_cols = [i for i in list(o_data[fut]
                                                                 .keys())
                                                 if i not in keys_IDs]

                            # Creating the data list for outcomes:
                            if fut == 0:
                                for oc in o_data_local_cols:
                                    dict_large_table.update({oc: []})

                                    # here we need to control whether the
                                    # outcome has a "Dep" threshold command:
                                    if ('Dep' in o_thresh_raw.split(' ; ') and
                                            py == 0 and oc not in o_dep_o_col):
                                        o_dep_name.append(o_name)
                                        o_dep_o_col.append(oc)  # unique entry
                                        o_dep_block_id.append(b)
                                        o_dep_o_id.append(o)
                                    # this is useful because of dependecies;
                                    # some driver depend on other drivers and
                                    # we can recall the corresponding table
                                    # if we encounter one such driver

                            # Storing the data values of outcomes is done below
                            # (after checking positive matching IDs for
                            # outcomes and drivers):

                            a_driver_counter = 0
                            d_data_local_cols = []  # lc: local_cols
                            d_data_lc_dict = {}
                            inconsistency_exists_glob = False
                            for a_driver in list(d_data.keys()):
                                fut_ID_check = d_data[a_driver][fut]['Fut_ID']
                                run_strat_ID_check = d_data[a_driver
                                                            ][fut
                                                              ]['Run_Strat_ID']
                                scenario_check = d_data[a_driver][fut
                                                                  ]['Scenario']
                                strat_check = d_data[a_driver][fut
                                                               ]['Strat_ID']

                                # Ensure all elements in drivers are consistent
                                # with outcomes:
                                inconsistency_exists = False
                                if fut_ID_list != fut_ID_check:
                                    print('WARNING! Inconsistent future IDs ' +
                                          'for outcome: ' + str(o) + ' (' +
                                          o_name + ') and driver: ' + a_driver)
                                    inconsistency_exists = True
                                if run_strat_ID_list != run_strat_ID_check:
                                    print('WARNING! Inconsistent run/strat IDs'
                                          + ' for outcome: ' + str(o) + ' (' +
                                          o_name + ') and driver: ' + a_driver)
                                    inconsistency_exists = True
                                if scenario_list != scenario_check:
                                    print('WARNING! Inconsistent scenario IDs '
                                          + 'for outcome: ' + str(o) + ' (' +
                                          o_name + ') and driver: ' +
                                          a_driver)
                                    inconsistency_exists = True
                                if strat_list != strat_check:
                                    print('WARNING! Inconsistent strat IDs ' +
                                          'for outcome: ' + str(o) + ' (' +
                                          o_name + ') and driver: ' + a_driver)
                                    inconsistency_exists = True
                                if inconsistency_exists is True:
                                    print('')
                                    inconsistency_exists_glob = True
                                    if (len(fut_ID_list) != len(fut_ID_check)
                                            and len(run_strat_ID_list
                                                    ) != len(run_strat_ID_check
                                                             )
                                            and len(scenario_list
                                                    ) != len(scenario_check)
                                            and len(strat_list
                                                    ) != len(strat_check)):
                                        # store the largest list of IDs:
                                        if len(fut_ID_check
                                               ) > len(fut_ID_list):
                                            alt_fut_ID = deepcopy(fut_ID_check)
                                            alt_run_strat_ID = \
                                                deepcopy(run_strat_ID_check)
                                            alt_scenario = \
                                                deepcopy(scenario_check)
                                            alt_strat = \
                                                deepcopy(strat_check)
                                        else:
                                            alt_fut_ID = deepcopy(fut_ID_list)
                                            alt_run_strat_ID = \
                                                deepcopy(run_strat_ID_list)
                                            alt_scenario = \
                                                deepcopy(scenario_list)
                                            alt_strat = \
                                                deepcopy(strat_list)
                                    else:
                                        print('DESIGN ERROR!. MUST ELIMINATE '
                                              + 'INCONSISTENCIES AND RE-RUN.')
                                        print('Potentially, you have ' +
                                              'unassigned ' +
                                              '"Outcome_ID_as_Driver"' +
                                              ' or "Driver_U_ID" columns.')
                                        pmrep.close()
                                        this_report.close()
                                        sys.exit()
                                else:
                                    pass
                                # As the system continues, we must append the
                                # driver columns
                                add_cols = [i for i in
                                            list(d_data[a_driver][fut].keys())
                                            if i not in keys_IDs]
                                d_data_local_cols += add_cols
                                d_data_lc_dict.update({a_driver: add_cols})

                            if inconsistency_exists_glob is False:
                                # Storing the IDs is done HERE (after
                                # checking positive matching IDs for
                                # outcomes and drivers)
                                dict_large_table[keys_IDs[0]] += fut_ID_list
                                dict_large_table[keys_IDs[1]] += \
                                    run_strat_ID_list
                                dict_large_table[keys_IDs[2]] += scenario_list
                                dict_large_table[keys_IDs[3]] += strat_list
                                ref_size = len(fut_ID_list)
                            else:
                                dict_large_table[keys_IDs[0]] += alt_fut_ID
                                dict_large_table[keys_IDs[1]] += \
                                    alt_run_strat_ID
                                dict_large_table[keys_IDs[2]] += alt_scenario
                                dict_large_table[keys_IDs[3]] += alt_strat
                                ref_size = len(alt_fut_ID)

                            # Storing the data values of outcomes is done
                            # below (after checking positive matching IDs for
                            # outcomes and drivers):
                            for oc in o_data_local_cols:
                                if inconsistency_exists_glob is False:
                                    dict_large_table[oc] += \
                                        o_data[fut][oc]['vl']
                                elif (len(o_data[fut][oc]['vl']) == ref_size):
                                    # inconsistency_exists_glob is True,
                                    # but the lengths match // equivalent to
                                    # the above condition
                                    dict_large_table[oc] += \
                                        o_data[fut][oc]['vl']
                                else:
                                    # inconsistency_exists_glob is True,
                                    # AND, there is a length mismatch
                                    vale_2_add = o_data[fut][oc]['vl'][-1]
                                    # !!!WARNING!!! This could enable fixing
                                    # the exoneration for fiscal analysis as:
                                    # not_exone_val = o_data[fut][oc]['vl'][0]
                                    # exone_val = o_data[fut][oc]['vl'][-1]
                                    # change this if desired!
                                    list_2_add = [vale_2_add for i in
                                                  range(ref_size)]
                                    dict_large_table[oc] += list_2_add
                                

                            # Creating the data list for drivers:
                            if fut == 0:
                                for dc in d_data_local_cols:
                                    dict_large_table.update({dc: []})

                            # Storing the data values of drivers:
                            for a_driver in list(d_data.keys()):
                                
                                for dc in d_data_lc_dict[a_driver]:
                                    
                                    if inconsistency_exists_glob is False:
                                        dict_large_table[dc] += \
                                            d_data[a_driver][fut][dc]['vl']
                                    elif (len(d_data[a_driver][fut][dc]['vl'])
                                          == ref_size):
                                        # inconsistency_exists_glob is True,
                                        # but the lengths match // equivalent
                                        # to the above condition
                                        dict_large_table[dc] += \
                                            d_data[a_driver][fut][dc]['vl']
                                    else:
                                        # inconsistency_exists_glob is True,
                                        # AND, there is a length mismatch
                                        vale_2_add = \
                                            d_data[a_driver][fut][dc]['vl'][-1]
                                        # !!!WARNING!!! This could fix
                                        # see note under *outcomes*
                                        list_2_add = [vale_2_add for i in
                                                      range(ref_size)]
                                        dict_large_table[dc] += list_2_add
                                    

                        add_str = '         > Large table created.'
                        print(add_str)
                        pmrep.write(add_str + '\n')
                        df_large_table = pd.DataFrame(dict_large_table)

                        # if o == 1:
                        #     print('debug why columns dont have IDs')
                        #     sys.exit()

                        add_str = \
                            '         > Creating sub-tables for all families'
                        print(add_str)
                        pmrep.write(add_str + '\n')
                        # Create a dictionary that stores the sub-tables:
                        dict_df_subtables = {}
                        for t in range(len(o_d_col_fam_list)):
                            this_fam = o_d_col_fam_list[t]

                            # print('check this')
                            # sys.exit()

                            df_a_subtable = df_large_table[keys_IDs + this_fam]

                            name_subtable_o = o_d_col_fam_dict_names['o'][t]
                            name_subtable_d = o_d_col_fam_dict_names['d'][t]
                            name_subtable = 'o_' + name_subtable_o + \
                                            '_d_' + name_subtable_d

                            dict_df_subtables.update({name_subtable:
                                                      df_a_subtable})

                        # appending the block key to data controller:
                        subtbl[b][o].update({per_name:
                                             deepcopy(dict_df_subtables)})

                        if py == 0:  # we do not want to repeat this per period
                            subtbl_col_cntrl[b
                                             ][o
                                               ].update({'o_d_cfl':
                                                         o_d_col_fam_list,
                                                         'o_d_cfln':
                                                         o_d_col_fam_list_names,                                                         
                                                         'o_d_cfd':
                                                         o_d_col_fam_dict,
                                                         'o_d_cfdn':
                                                         o_d_col_fam_dict_names
                                                         })

            add_str = '\n PRIM tables are finished satisfactorily.'
            print(add_str)
            pmrep.write(add_str + '\n')
            # Recording mid time of execution:
            end_m = time.time()
            te_m = -start_1 + end_m  # te: time_elapsed
            print(str(te_m) + ' seconds /', str(te_m/60) + ' minutes\n')

            # Check here that our design is consistent:
            if len(o_dep_o_col) != len(list(set(o_dep_o_col))):
                print('DESIGN ERROR 2. MUST ELIMINATE INCONSISTENCIES AND ' +
                      'RE-RUN')
                sys.exit()

            # Store the subtable as a pickle; it may come in handy for multiple
            # reporting purposes:
            fn_subtbl = 'subtbl_ana_' + str(ana_ID) + '_exp_' + str(exp_ID)
            with open(fn_subtbl + '.pickle', 'wb') as out_subtbl:
                pickle.dump(subtbl, out_subtbl, protocol=pickle.HIGHEST_PROTOCOL)
            out_subtbl.close()

            '''
            pmrep.close()
            this_report.close()
            sys.exit()
            '''

            # Here we have finished across blocks and outcomes. Time for the
            # performance of the scenario discovery analysis using PRIM. Here
            # we must do a lot of results reporting. Also, this part is *NOT*
            # useful for the figures creation analysis.
            add_str = '\n7. Creating PRIM analyses per period and report.'
            print(add_str)
            pmrep.write(add_str + '\n')

            # Don't forget to create a .csv output with the systematization
            # of the Scenario Discovery results:
            rep_csv = {'block': [], 'o_id': [], 'outcome': [],
                       'level': [], 'o1_fam': [], 'o1_col': [],
                       'o2_fam': [], 'o2_col': [],
                       'family': [], 'column': [],
                       'period': [], 'base_thr': [],
                       'thr_type': [], 'thr_range': [], 'thr_value': [],
                       'thr_value_norm': [], 'prim_option': [],
                       'coverage': [], 'density': [], 'avg_cov_dev': [],
                       'driver_col': [], 'min': [], 'max': [],
                       'min_norm': [], 'max_norm': [],
                       'query_type': []}

            for b in list_blocks:  # 4 dubugging
                # for b in [33]:
                add_str = '\n===> Analyzing block: ' + str(b)
                print(add_str)
                pmrep.write(add_str + '\n')

                this_report.write('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')
                add_str = 'Analysis of block ' + str(b)
                this_report.write(add_str + '\n\n')

                # Iterate across outcomes:
                list_outcomes = list(prim_manager_o[b].keys())
                for o in list_outcomes:  # 4 dubugging
                    # for o in [33]:
                    o_name = prim_manager['Outcome'
                                          ][b][o]['Name'
                                                  ][0]  # list of length 1
                    o_thresh_raw = prim_manager['Outcome'
                                                ][b
                                                  ][o
                                                    ]['Threshold'
                                                      ][0
                                                        ]  # list of length 1
                    o_thresh_list = o_thresh_raw.split(' ; ')

                    add_str = '\n     ===> Analyzing outcome (table): ' + \
                        str(o) + ' // ' + o_name
                    print(add_str)
                    pmrep.write(add_str + '\n')
                    this_report.write(add_str + '\n')

                    # Here we need to extract the column name manager:
                    o_d_col_fam_list = subtbl_col_cntrl[b][o]['o_d_cfl']
                    o_d_col_fam_list_names = subtbl_col_cntrl[b][o]['o_d_cfln']
                    o_d_col_fam_dict = subtbl_col_cntrl[b][o]['o_d_cfd']
                    o_d_col_fam_dict_names = subtbl_col_cntrl[b][o]['o_d_cfdn']

                    per_list = period_list
                    for py in range(len(per_list)):
                        per_name = per_list[py]
                        for fam in range(len(o_d_col_fam_list)):
                            this_fam_key = o_d_col_fam_list_names[fam]
                            o_pssbl_cols = o_d_col_fam_dict['o'][fam]
                            d_pssbl_cols = o_d_col_fam_dict['d'][fam]

                            add_str = \
                                '\n     => Working with column family: ' + \
                                this_fam_key + ' and period ' + str(per_name) \
                                + ' for ' + str(o_name) + ' (' + str(o) + ')'
                            print(add_str)
                            pmrep.write(add_str + '\n')
                            this_report.write(add_str + '\n')

                            this_df_raw = subtbl[b][o][per_name][this_fam_key]
                            this_df_raw = this_df_raw.fillna(0)

                            # Filter the normalized dataframe:
                            unique_strats = list(set(this_df_raw['Strat_ID']))
                            if (len(unique_strats) == 2 and 'none' in
                                    unique_strats):
                                this_df_raw_2 = this_df_raw \
                                    .loc[(this_df_raw['Strat_ID'] != 'none')]
                            else:
                                this_df_raw_2 = this_df_raw

                            use_cols = [i for i in this_df_raw_2.columns.
                                        tolist() if i not in keys_IDs]
                            this_df_raw_3 = this_df_raw_2[use_cols]
                            this_df_raw_3 = this_df_raw_3.reset_index()

                            this_df = this_df_raw_3 \
                                .loc[:, (this_df_raw_3.sum(axis=0) != 0)]

                            d_pssbl_cols_app = [i for i in d_pssbl_cols if i in
                                                this_df.columns.tolist()]

                            add_str = \
                                '         > We exclude the following cols: '
                            exc_df = this_df.loc[:, (this_df.sum(axis=0) == 0)]
                            exc_cols = exc_df.columns.tolist()
                            print(add_str, exc_cols)
                            for listitem in exc_cols:
                                pmrep.write('         %s,' % listitem)
                                this_report.write(' %s,' % listitem)
                            pmrep.write('\n')
                            this_report.write('\n')

                            # WARNING!!! Be sure to eliminate IDs and to be
                            # consistent, e.g., use exonerated fiscal results
                            # if only 2 "Strategy IDs exist".

                            add_str = '         8. Normalizing the dataframe.'
                            print(add_str)
                            pmrep.write(add_str + '\n')
                            # use a function // test other scalings in future
                            # versions:

                            # print('debug possible error below')

                            norm_df, scale_factor, scale_sum, scale_zero = \
                                min_max_scaling(this_df)

                            inp_df_raw = norm_df[d_pssbl_cols_app]
                            inp_df = inp_df_raw.dropna(axis=1, how='all')

                            norm_df = norm_df.fillna(0)

                            # Work on applying PRIM below for these outcomes //
                            # Iterate across possible column names //
                            # In the meantime, store the infor dictionaries
                            # pero column.
                            dict_infos = {}

                            bug_acts = False
                            bug_acts_1 = False
                            bug_acts_2 = False

                            for c in o_pssbl_cols:
                                if float(this_df_raw[c].sum()) == 0:
                                    add_str = '         > No action for this' \
                                        + \
                                        ' family and period. Columns are zero.'
                                    print(add_str)
                                    pmrep.write(add_str + '\n')
                                    this_report.write(add_str + '\n')
                                    bug_acts_1 = True
                                elif float(norm_df[c].sum()) == 0:
                                    add_str = '         > No action for this' \
                                        + \
                                        ' family and period. ' \
                                        '*Normalized* columns are zero.'
                                    print(add_str)
                                    pmrep.write(add_str + '\n')
                                    this_report.write(add_str + '\n')
                                    bug_acts_1 = True
                                else:
                                    # Create the metric list and numpy arrary:
                                    outc_list = norm_df[c].tolist()
                                    outc_array = np.array(outc_list)

                                    if (o_thresh_list[0].lower() == 'dep'
                                            and len(o_thresh_list) == 1):
                                        add_str = '         > No action ' \
                                            + \
                                            'for this family and period.' \
                                            + \
                                            '  The threshold for this ' + \
                                            'column depends on other ' + \
                                            'metrics.'
                                        print(add_str)
                                        pmrep.write(add_str + '\n')
                                        this_report.write(add_str + '\n')
                                        bug_acts_2 = True
                                    else:
                                        # Iterate across threshold lists:
                                        add_str = '         > Action! ' + \
                                            'Applying thresholds :'
                                        print(add_str, o_thresh_list)
                                        pmrep.write(add_str)
                                        this_report.write(add_str)
                                        for listitem in o_thresh_list:
                                            pmrep.write(' %s,' % listitem)
                                            this_report.write(' %s,' %
                                                              listitem)
                                        pmrep.write('\n')
                                        this_report.write('\n')

                                        # Apply the PRIM and expect to get a
                                        # information dicts (with results):
                                        info_dict_1, info_dict_2, \
                                            error_type_a, error_type_b = \
                                            f1_prim_box_execute(o_thresh_list,
                                                                outc_array,
                                                                outc_list,
                                                                inp_df,
                                                                scale_zero[c],
                                                                py
                                                                )
                                        
                                        this_dict_infos = {1: info_dict_1,
                                                           2: info_dict_2}
                                        dict_infos.update({c: this_dict_infos})

                                        bug_acts = True
                            # if c == "Benefit_direct":
                            #     sys.exit(89)
                            add_str = \
                                '         > Report on the PRIM findings for ' \
                                + 'valid columns.'
                            print(add_str)
                            pmrep.write(add_str + '\n')
                            this_report.write(add_str + '\n')

                            # Relevant drivers for later query // rel: relevant
                            rel_driv = []
                            rel_driv_min = []
                            rel_driv_max = []
                            rel_driv_tbase = []
                            rel_driv_t = []
                            rel_driv_o_col = []
                            rel_driv_o_fam = []
                            rel_driv_maxobase = []

                            # Iterate across outcome columns:
                            for this_col in list(dict_infos.keys()):
                                info_dict_1 = dict_infos[this_col][1]
                                info_dict_2 = dict_infos[this_col][2]
                                astr_list, rep_csv, rel_driv, rel_driv_min, \
                                    rel_driv_max, rel_driv_tbase, \
                                    rel_driv_t, rel_driv_o_col, \
                                    rel_driv_o_fam, rel_driv_maxobase = \
                                    f1_2_rep_string_and_csv(info_dict_1,
                                                            info_dict_2,
                                                            rep_csv, b, o,
                                                            o_name, 1,  # lvl 1
                                                            this_fam_key,
                                                            this_col,
                                                            per_name,
                                                            scale_factor,
                                                            scale_sum,
                                                            scale_zero,
                                                            scale_factor,
                                                            scale_sum,
                                                            scale_zero,
                                                            rel_driv,
                                                            rel_driv_min,
                                                            rel_driv_max,
                                                            rel_driv_tbase,
                                                            rel_driv_t,
                                                            rel_driv_o_col,
                                                            rel_driv_o_fam,
                                                            rel_driv_maxobase,
                                                            'structured')
                                # Report results:
                                for astr in astr_list:
                                    print(astr)
                                    pmrep.write(astr + '\n')
                                    this_report.write(astr + '\n')
                                if len(astr_list) == 0:
                                    add_str = '         > No PRIM results ' \
                                        + 'for independent driver (level 1).' \
                                        + ' Checking info_dict_1: ' + \
                                        str(len(list(info_dict_1.keys()))) + \
                                        '. // Error A: ' + str(error_type_a) \
                                        + '. // Error B: ' + \
                                        str(error_type_b) + '.'
                                    print(add_str)
                                    pmrep.write(add_str + '\n')
                                    this_report.write(add_str + '\n')

                            # Work on applying PRIM below for any driver that
                            # is in the "Dep" list, i.e., depends on other
                            # drivers.
                            # NOTE: by design, we can do this up to 2 times,
                            # since we designed 3 levels in PRIM structure.
                            # !!WARNING!!! More blocks could be designed ad-hoc

                            # Relevant drivers for lvl 2 query // rel: relevant
                            rel_driv_l2 = []
                            rel_driv_min_l2 = []
                            rel_driv_max_l2 = []
                            rel_driv_tbase_l2 = []
                            rel_driv_t_l2 = []
                            rel_driv_o1_col_l2 = []
                            rel_driv_o1_fam_l2 = []
                            rel_driv_o2_col_l2 = []
                            rel_driv_o2_fam_l2 = []
                            rel_driv_mb_l2 = []

                            # Apply level 2 query:
                            for relofam in list(set(rel_driv_o_fam)):
                                for relocol in list(set(rel_driv_o_col)):
                                    for thld_base in list(set(rel_driv_tbase)):
                                        for u_rel_driv in list(set(rel_driv)):
                                            ithld = \
                                                [i for i, x in
                                                enumerate(rel_driv_tbase)
                                                if x == thld_base]
                                            ireld = \
                                                [i for i, x in enumerate(rel_driv)
                                                if x == u_rel_driv]
                                            irelocol = \
                                                [i for i, x in enumerate(rel_driv_o_col)
                                                if x == relocol]
                                            irelofam = \
                                                [i for i, x in enumerate(rel_driv_o_fam)
                                                if x == relofam]
                                            ad_list = \
                                                intersection_4(ithld, ireld, irelocol, irelofam)
                                            if len(ad_list) != 0:
                                                ad = ad_list[0]
                                                if len(ad_list) != 1:
                                                    print('design error\n')
                                                    sys.exit()
                                                if rel_driv[ad] in o_dep_o_col:
                                                    unique_dep_index = \
                                                        o_dep_o_col.index(rel_driv[ad])
                                                    ad_b = \
                                                        o_dep_block_id[unique_dep_index]
                                                    ad_o = \
                                                        o_dep_o_id[unique_dep_index]
                                                    ad_o_name = \
                                                        o_dep_name[unique_dep_index]
                                                    ad_df_grab = subtbl[ad_b
                                                                        ][ad_o
                                                                        ][per_name]
                                                    # cfl: col_fam_list
                                                    ad_cfl_names = \
                                                        subtbl_col_cntrl[ad_b
                                                                        ][ad_o
                                                                        ]['o_d_cfln'
                                                                        ]
                                                    ad_col_fam_dict = \
                                                        subtbl_col_cntrl[ad_b
                                                                        ][ad_o
                                                                        ]['o_d_cfd']
                                                    # Select the output columns that
                                                    # contain specifically "ad" index
                                                    ad_cfl_names_app = []
                                                    ad_col_fam_dict_app_o = []
                                                    ad_col_fam_dict_app_d = []
                                                    for fam in range(len(ad_cfl_names)):
                                                        if (rel_driv[ad] in
                                                                ad_col_fam_dict['o'][fam]):
                                                            ad_cfl_names_app \
                                                                .append(ad_cfl_names[fam])
                                                            ad_col_fam_dict_app_o \
                                                                .append(ad_col_fam_dict['o']
                                                                        [fam])
                                                            ad_col_fam_dict_app_d \
                                                                .append(ad_col_fam_dict['d']
                                                                        [fam])
                                                    ad_col_fam_dict_app = \
                                                        {'o': ad_col_fam_dict_app_o,
                                                        'd': ad_col_fam_dict_app_d}
                                                    # extracting dependent column info:
                                                    norm_min = rel_driv_min[ad]
                                                    norm_max = rel_driv_max[ad]
                                                    the_t = rel_driv_tbase[ad]
                                                    the_o1_col = rel_driv_o_col[ad]
                                                    the_o1_fam = rel_driv_o_fam[ad]
                                                    the_maxobase = \
                                                        rel_driv_maxobase[ad]
                                                    # lvl 2
                                                    astr_list, rep_csv, rel_driv_l2, \
                                                        rel_driv_min_l2, \
                                                        rel_driv_max_l2,\
                                                        rel_driv_tbase_l2,\
                                                        rel_driv_t_l2, \
                                                        rel_driv_o1_col_l2,\
                                                        rel_driv_o1_fam_l2, \
                                                        rel_driv_o2_col_l2, \
                                                        rel_driv_o2_fam_l2, \
                                                        rel_driv_maxobase_l2, \
                                                        error_type_c, error_type_d = \
                                                        f2_ipp(2, 3, b, o, o_name,
                                                            per_name, rep_csv,
                                                            ad_df_grab,
                                                            ad_cfl_names_app,
                                                            ad_col_fam_dict_app,
                                                            rel_driv[ad],
                                                            norm_min, norm_max,
                                                            the_t,
                                                            the_o1_col,
                                                            the_o1_fam, '', '',
                                                            the_maxobase,
                                                            rel_driv_l2,
                                                            rel_driv_min_l2,
                                                            rel_driv_max_l2,
                                                            rel_driv_tbase_l2,
                                                            rel_driv_t_l2,
                                                            rel_driv_o1_col_l2,
                                                            rel_driv_o1_fam_l2,
                                                            rel_driv_o2_col_l2,
                                                            rel_driv_o2_fam_l2,
                                                            rel_driv_mb_l2,
                                                            'structured')
                                                    # Report results:
                                                    for astr in astr_list:
                                                        add_str = \
                                                            '         > (PRIM results' \
                                                            + ' for level 2 dependecies).'
                                                        print(add_str)
                                                        pmrep.write(add_str)
                                                        this_report.write(add_str)
                                                        print(astr)
                                                        pmrep.write(astr + '\n')
                                                        this_report.write(astr + '\n')
                                                    if len(astr_list) == 0:
                                                        add_str = \
                                                            '         > No PRIM results '\
                                                            + 'under level 2 dependecies.'\
                                                            + ' // Error C: ' + \
                                                            str(error_type_c) + \
                                                            ' // Error D: ' + \
                                                            str(error_type_d)
                                                        print(add_str)
                                                        pmrep.write(add_str + '\n')
                                                        this_report.write(add_str
                                                                        + '\n')

                            # Apply level 3 query:
                            for relofam2 in list(set(rel_driv_o2_fam_l2)):
                                for relocol2 in list(set(rel_driv_o2_col_l2)):
                                    for relofam in list(set(rel_driv_o1_fam_l2)):
                                        for relocol in list(set(rel_driv_o1_col_l2)):
                                            for thld_base in list(set(rel_driv_tbase_l2)):
                                                for u_rel_driv in list(set(rel_driv_l2)):
                                                    ithld = \
                                                        [i for i, x in
                                                        enumerate(rel_driv_tbase_l2)
                                                        if x == thld_base]
                                                    ireld = \
                                                        [i for i, x in enumerate(rel_driv_l2)
                                                        if x == u_rel_driv]
                                                    irelocol = \
                                                        [i for i, x in
                                                        enumerate(rel_driv_o1_col_l2)
                                                        if x == relocol]
                                                    irelocol2 = \
                                                        [i for i, x in
                                                        enumerate(rel_driv_o2_col_l2)
                                                        if x == relocol2]
                                                    irelofam = \
                                                        [i for i, x in
                                                        enumerate(rel_driv_o1_fam_l2)
                                                        if x == relofam]
                                                    irelofam2 = \
                                                        [i for i, x in
                                                        enumerate(rel_driv_o2_fam_l2)
                                                        if x == relofam2]
                                                    ad_list = \
                                                        intersection_6(ithld, ireld, irelocol, irelocol2, irelofam, irelofam2)
                                                    if len(ad_list) != 0:
                                                        ad = ad_list[0]
                                                        if len(ad_list) != 1:
                                                            print('design error\n')
                                                            sys.exit()
                                                        if rel_driv_l2[ad] in o_dep_o_col:
                                                            unique_dep_index = \
                                                                o_dep_o_col.index(rel_driv_l2[ad])
                                                            ad_b = o_dep_block_id[unique_dep_index]
                                                            ad_o = o_dep_o_id[unique_dep_index]
                                                            ad_o_name = \
                                                                o_dep_name[unique_dep_index]
                                                            ad_df_grab = subtbl[ad_b
                                                                                ][ad_o][per_name]
                                                            # cfl: col_fam_list
                                                            ad_cfl_names = \
                                                                subtbl_col_cntrl[ad_b
                                                                                ][ad_o
                                                                                ]['o_d_cfln']
                                                            ad_col_fam_dict = \
                                                                subtbl_col_cntrl[ad_b
                                                                                ][ad_o]['o_d_cfd']
                                                            # Select the output columns relevant
                                                            # thar contain specifically "ad" index
                                                            ad_cfl_names_app = []
                                                            ad_col_fam_dict_app_o = []
                                                            ad_col_fam_dict_app_d = []
                                                            for fam in range(len(ad_cfl_names)):
                                                                if (rel_driv_l2[ad] in
                                                                        ad_col_fam_dict['o'][fam]):
                                                                    ad_cfl_names_app \
                                                                        .append(ad_cfl_names[fam])
                                                                    ad_col_fam_dict_app_o \
                                                                        .append(ad_col_fam_dict['o']
                                                                                [fam])
                                                                    ad_col_fam_dict_app_d \
                                                                        .append(ad_col_fam_dict['d']
                                                                                [fam])
                                                            ad_col_fam_dict_app = \
                                                                {'o': ad_col_fam_dict_app_o,
                                                                'd': ad_col_fam_dict_app_d}
                                                            # extracting dependent column info:
                                                            norm_min = rel_driv_min_l2[ad]
                                                            norm_max = rel_driv_max_l2[ad]
                                                            the_t = rel_driv_tbase_l2[ad]
                                                            the_o1_col = rel_driv_o1_col_l2[ad]
                                                            the_o1_fam = rel_driv_o1_fam_l2[ad]
                                                            the_o2_col = rel_driv_o2_col_l2[ad]
                                                            the_o2_fam = rel_driv_o2_fam_l2[ad]
                                                            the_maxobase = rel_driv_mb_l2[ad]
                                                            # lvl 3
                                                            astr_list, rep_csv, pass1, pass2, \
                                                                pass3, pass4, pass5, pass6, \
                                                                pass7, pass8, pass9, pass10, \
                                                                error_type_c, error_type_d = \
                                                                f2_ipp(3, 3, b, o, o_name,
                                                                    per_name, rep_csv,
                                                                    ad_df_grab,
                                                                    ad_cfl_names_app,
                                                                    ad_col_fam_dict_app,
                                                                    rel_driv_l2[ad],
                                                                    norm_min, norm_max,
                                                                    the_t,
                                                                    the_o1_col, the_o1_fam,
                                                                    the_o2_col, the_o2_fam,
                                                                    the_maxobase,
                                                                    [], [], [],
                                                                    [], [], [],
                                                                    [], [], [],
                                                                    [],
                                                                    'structured')
                                                            # Report results:
                                                            for astr in astr_list:
                                                                add_str = \
                                                                    '         > (PRIM results' \
                                                                    + ' for level 3 dependecies).'
                                                                print(add_str)
                                                                pmrep.write(add_str)
                                                                this_report.write(add_str)
            
                                                                print(astr)
                                                                pmrep.write(astr + '\n')
                                                                this_report.write(astr + '\n')
                                                            if len(astr_list) == 0:
                                                                add_str = \
                                                                    '         > No PRIM results'\
                                                                    ' under level 3 dependecies.'
                                                                print(add_str)
                                                                pmrep.write(add_str + '\n')
                                                                this_report.write(add_str
                                                                                + '\n')

                            ''' If many more levels are required for the
                            analysis, the corresponding process should be made
                            more concise. '''

                            # Report no result.
                            if len(list(dict_infos.keys())) == 0:
                                add_str = \
                                    '         > No PRIM to report for family.'\
                                    + ' No *dict_infos* content.'
                                print(add_str)
                                print(bug_acts, bug_acts_1, bug_acts_2)
                                pmrep.write(add_str + '\n')
                                this_report.write(add_str + '\n')
                                pmrep.write(str(bug_acts) + ',' +
                                            str(bug_acts_1) + ',' +
                                            str(bug_acts_2) + '\n')

            add_str = '\n9. The automatic PRIM results (from the structured' \
                + ' analysis) have been completed.'
            print(add_str)
            pmrep.write(add_str + '\n')
            this_report.write(add_str + '\n')

            # > Here we have finished across blocks and outcomes for all
            # pre-programmed driver identification. However, it would be useful
            # to also have specific questions hard-programmed below.
            # > This is necessary to apply PRIM to metrics without a temporal
            # correspondence, i.e., an outcome of the 21-50 average compared
            # to other periods.

            # dont start the section below yet, still debugging automatic PRIM!
            # sys.exit()

            # By this point we can print *rep_csv* as a dataframe (in .csv)
            # for table visualization
            rep_df_name = 'sd_ana_' + str(ana_ID) + '_exp_' + str(exp_ID) +\
                '.csv'
            rep_df = pd.DataFrame.from_dict(rep_csv)
            rep_df.to_csv(rep_df_name, index=None, header=True)

            # Close the system and report closure of this report:
            this_report.close()
            print('We just closed: ' + str(this_report_name) + '\n\n')
            # sys.exit()

    pmrep.close()
    # Recording final time of execution:
    end_f = time.time()
    te_f = -start_1 + end_f  # te: time_elapsed
    print(str(te_f) + ' seconds /', str(te_f/60) + ' minutes')
    print('*: This automatic analysis is finished.')
