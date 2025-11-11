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

''' ///////////////////////////////////////////////////////////////////
Function 1 (f1): convert formulas and indicators to column information
'''


def frml_ind_2_colinfo(elmnt_id, o_OR_d, name, srce, frml, inv_sets, sup_sets,
                       prms, tfa, col_mngmt, sets_det, prms_det, scenarios,
                       var_mngmt, o_id_as_d, d_u_id):

    # Unpack elements (the ones that were entered as lists to this function):
    frml_num, frml_den, frml_last = frml[0], frml[1], frml[2]

    # Define the set arrangement:
    if sets_det[0] != 'all' and sets_det[0] != 'none':
        print(sets_det)
        num_sum_sets = sets_det[0].split(' ; ')
    else:
        num_sum_sets = sets_det[0]

    if sets_det[1] != 'all' and sets_det[1] != 'none':
        num_sub_sets = sets_det[1].split(' ; ')
    else:
        num_sub_sets = sets_det[1]

    if sets_det[2] != 'all' and sets_det[2] != 'none':
        den_sum_sets = sets_det[2].split(' ; ')
    else:
        den_sum_sets = sets_det[2]

    if sets_det[3] != 'all' and sets_det[3] != 'none':
        den_sub_sets = sets_det[3].split(' ; ')
    else:
        den_sub_sets = sets_det[3]

    # Define the param arrangement:
    if prms_det[0] != 'all' and prms_det[0] != 'none':
        num_sum_prms = prms_det[0].split(' ; ')
    else:
        num_sum_prms = prms_det[0]

    if prms_det[1] != 'all' and prms_det[1] != 'none':
        num_sub_prms = prms_det[1].split(' ; ')
    else:
        num_sub_prms = prms_det[1]

    if prms_det[2] != 'all' and prms_det[2] != 'none':
        den_sum_prms = prms_det[2].split(' ; ')
    else:
        den_sum_prms = prms_det[2]

    if prms_det[3] != 'all' and prms_det[3] != 'none':
        den_sub_prms = prms_det[3].split(' ; ')
    else:
        den_sub_prms = prms_det[3]

    # continue correcting this one first thing in the morning

    # Principle:
    # each row from *prim_structure* turns into several cols of *prim_file*

    # Unpacking the semicolon-separated elements into lists:
    try:
        all_sets = inv_sets.replace(' ', '').split(';')
    except Exception:
        print(elmnt_id, name)
        print('debug')
        sys.exit()
    all_sup_sets = sup_sets.replace(' ', '').split(';')
    #print(all_sup_sets)
    all_prms = prms.split(' ; ')

    all_scenarios = scenarios.replace(' ', '').split(';')
    all_var_mngmt = var_mngmt.replace(' ', '').split(';')

    # Define the output variables to produce:

    # we initialize the column numbers in zero,
    # but we need to specifiy the column sizes:
    col_nums_by_set, col_nums_by_prm = 0, 1

    # Besides knowing the number of columns that each driver must add,
    # we must add a title to each column
    col_title_suff_prm = ['']
    col_title_suff_set = []  # append this list with required column suffixes
    col_title_pref = name

    # Make sure to select the sets needed in each set-related column
    dict_sets_per_set_col = {}  # This is only for the set-related columns

    col_mngmt_ele = col_mngmt.split(' ; ')

    # indicate what param OR param list is needed by each column:
    params_for_column = [all_prms]
    # for generic purposes, except for *column_per_param*,
    # this is a lenght=1 list to be called below

    # column_Management: in this section we create the name of the sets
    if 'Str_Both_4 and 5 : Energy' in col_mngmt_ele:
        col_nums_by_set += 1
        col_title_suff_set.append('_energy')
        this_col_set_name = col_title_pref + col_title_suff_set[-1]
        # subselecting the sets:
        this_col_sets = all_sets
        dict_sets_per_set_col.update({this_col_set_name: this_col_sets})

    if 'Str_Only_4 : Transport' in col_mngmt_ele:
        col_nums_by_set += 1
        col_title_suff_set.append('_transport')
        this_col_set_name = col_title_pref + col_title_suff_set[-1]
        # subselecting the sets:
        this_col_sets = [i for i in all_sets if '4' in i]
        dict_sets_per_set_col.update({this_col_set_name: this_col_sets})
        # Explanation: the sets are already named with a 4 if they are related
        # to transport

    # This is the only column management that expands the parameters per column
    if 'column_per_param' in col_mngmt_ele:
        col_nums_by_prm = len(all_prms)
        col_title_suff_prm = []  # replace the param suffix list menu
        for k in range(len(all_prms)):
            col_title_suff_prm.append('_' + all_prms[k].replace(' ', '_'))

        params_for_column = all_prms
        # this list is as long as *col_nums_by_prm*

    if 'column_per_set' in col_mngmt_ele:
        col_nums_by_set += len(all_sets)
        for k in range(len(all_sets)):
            col_title_suff_set.append('_' + all_sets[k].replace(' ', '_'))
            this_col_set_name = col_title_pref + col_title_suff_set[-1]
            dict_sets_per_set_col.update({this_col_set_name: [all_sets[k]]})

    if 'group_by_fuel' in col_mngmt_ele:
        # counting the number of fuels in these sets:
        unique_fuel_sets = []
        for k in range(len(all_sets)):
            if all_sets[k].split('_')[0][-3:] not in unique_fuel_sets:
                unique_fuel_sets.append(all_sets[k].split('_')[0][-3:])

        col_nums_by_set += len(unique_fuel_sets)
        col_title_suff_set = ['_' + unique_fuel_sets[k] for k in
                              range(len(unique_fuel_sets))]

        for k in range(len(unique_fuel_sets)):
            this_col_set_name = col_title_pref + col_title_suff_set[k]
            this_col_sets = [i for i in all_sets if unique_fuel_sets[k] in i]
            dict_sets_per_set_col.update({this_col_set_name: this_col_sets})

    if 'group_by_type' in col_mngmt_ele:
        # counting the number of types in these sets:
        unique_type_sets = []
        for k in range(len(all_sets)):
            if all_sets[k][2:2+3] not in unique_type_sets:
                unique_type_sets.append(all_sets[k][2:2+3])

        col_nums_by_set += len(unique_type_sets)
        col_title_suff_set = ['_' + unique_type_sets[k] for k in
                              range(len(unique_type_sets))]

        for k in range(len(unique_type_sets)):
            this_col_set_name = col_title_pref + col_title_suff_set[k]
            this_col_sets = [i for i in all_sets if unique_type_sets[k] in i]
            dict_sets_per_set_col.update({this_col_set_name: this_col_sets})

    if 'group_by_type_and_LowHighEmissions' in col_mngmt_ele:
        # separating the sets into low and high emission tecnologies
        low_emission_sets = []
        high_emission_sets = []
        for k in range(len(all_sets)):
            if ('PH' in all_sets[k].split('_')[0][-3:] or
                    'ELE' in all_sets[k].split('_')[0][-3:] or
                    'HYD' in all_sets[k].split('_')[0][-3:]):
                # this includes hybrids, electric, or hydrogen
                low_emission_sets.append(all_sets[k])
            else:
                # this includes LPG, DSL or GAS
                high_emission_sets.append(all_sets[k])

        col_nums_by_set += 2  # there are only 2 categories to assign here
        col_title_suff_set = ['_' + 'LowEmissions', '_' + 'HighEmissions']

        # This is for low emissions
        this_col_set_name = col_title_pref + col_title_suff_set[0]
        dict_sets_per_set_col.update({this_col_set_name: low_emission_sets})

        # This is for high emissions
        this_col_set_name = col_title_pref + col_title_suff_set[1]
        dict_sets_per_set_col.update({this_col_set_name: high_emission_sets})

    if 'group_by_use' in col_mngmt_ele:
        # counting the number of uses in these sets:
        unique_use_sets = []
        for k in range(len(all_sets)):
            if all_sets[k][-3:] not in unique_use_sets:
                unique_use_sets.append(all_sets[k][-3:])

        col_nums_by_set += len(unique_use_sets)
        col_title_suff_set = ['_' + unique_use_sets[k] for k in
                              range(len(unique_use_sets))]

        for k in range(len(unique_use_sets)):
            this_col_set_name = col_title_pref + col_title_suff_set[k]
            this_col_sets = [i for i in all_sets if unique_use_sets[k] in i]
            dict_sets_per_set_col.update({this_col_set_name: this_col_sets})

    if 'group_fossil_elec_H2' in col_mngmt_ele:
        # separating the sets into fossil, electric, and hydrogen
        # (hybrids are not included in these sets)
        h2_emission_sets = []
        elec_emission_sets = []
        fossil_emission_sets = []
        for k in range(len(all_sets)):
            # this includes hydrogen
            if 'HYD' in all_sets[k].split('_')[0][-3:]:
                h2_emission_sets.append(all_sets[k])
            # this includes electricity
            elif 'ELE' in all_sets[k].split('_')[0][-3:]:
                elec_emission_sets.append(all_sets[k])
            # this includes fossil fuels
            else:
                fossil_emission_sets.append(all_sets[k])

        '''
        print(all_sets[k].split('_'))
        print('debug')
        sys.exit()
        '''

        col_nums_by_set += 3  # there are only 3 categories to assign here
        col_title_suff_set = ['_H2', '_elec', '_fossil']

        # this is for hydrogen
        this_col_set_name = col_title_pref + col_title_suff_set[0]
        dict_sets_per_set_col.update({this_col_set_name: h2_emission_sets})

        # this is for electricity
        this_col_set_name = col_title_pref + col_title_suff_set[1]
        dict_sets_per_set_col.update({this_col_set_name: elec_emission_sets})

        # this is for fossil fuels
        this_col_set_name = col_title_pref + col_title_suff_set[2]
        dict_sets_per_set_col.update({this_col_set_name: fossil_emission_sets})

    if 'none' in col_mngmt_ele:
        col_nums_by_set += 1
        col_title_suff_set.append('')
        this_col_set_name = col_title_pref
        # subselecting the sets:
        this_col_sets = all_sets
        dict_sets_per_set_col.update({this_col_set_name: this_col_sets})

    if 'special_Biofuel' in col_mngmt_ele:  # the formula should be direct
        col_nums_by_set += 2
        col_title_suff_set = ['_' + 'biodiesel', '_' + 'ethanol']
        col_sets_special_Biofuel = ['NDP then T4DSL_HEA then CO2e',
                                    'NDP then T4GSL_PRI then CO2e']
        # we use "then" because the data source is a dictionary and
        # the sets are nested

        for k in range(len(col_title_suff_set)):
            this_col_set_name = col_title_pref + col_title_suff_set[k]
            dict_sets_per_set_col.update({this_col_set_name:
                                          [col_sets_special_Biofuel[k]]})

    if 'special_mode_shift' in col_mngmt_ele:
        col_nums_by_set += 2
        col_title_suff_set = ['_' + 'public', '_' + 'nonmot']
        col_sets_special_mode_shift = ['E6TDPASPUB', 'E6TRNOMOT']

        for k in range(len(col_title_suff_set)):
            this_col_set_name = col_title_pref + col_title_suff_set[k]
            dict_sets_per_set_col.update({this_col_set_name:
                                          [col_sets_special_mode_shift[k]]})

        this_col_set_name = col_title_pref + '_denominator'
        dict_sets_per_set_col.update({this_col_set_name:
                                      col_sets_special_mode_shift})

    if 'special_freight_shift' in col_mngmt_ele:
        col_nums_by_set += 1
        col_title_suff_set = ['_' + 'rail']
        col_sets_special_freight_shift = ['Techs_Trains_Freight']

        for k in range(len(col_title_suff_set)):
            this_col_set_name = col_title_pref + col_title_suff_set[k]
            dict_sets_per_set_col.update({this_col_set_name:
                                          [col_sets_special_freight_shift[k]]})

        this_col_set_name = col_title_pref + '_denominator'
        dict_sets_per_set_col.update({this_col_set_name:
                                      col_sets_special_freight_shift})

    if 'special_PT_dist' in col_mngmt_ele:
        col_nums_by_set += 3
        col_title_suff_set = ['_' + 'bus', '_' + 'minibus', '_' + 'taxi']
        col_sets_special_PT_dist = ['Techs_Buses', 'Techs_Microbuses',
                                    'Techs_Taxis']

        for k in range(len(col_title_suff_set)):
            this_col_set_name = col_title_pref + col_title_suff_set[k]
            dict_sets_per_set_col.update({this_col_set_name:
                                          [col_sets_special_PT_dist[k]]})

        this_col_set_name = col_title_pref + '_denominator'
        dict_sets_per_set_col.update({this_col_set_name:
                                      col_sets_special_PT_dist})

    # create a dictionary with formulas per parameter
    frml_den_elmnts = frml_den.split(' ; ')
    frml_num_elmnts = frml_num.split(' ; ')

    # frml_denominator:
    # in this section we append the formulas for each parameter
    frml_den_list = []
    if 'Den_GDP' in frml_den_elmnts:
        for k in range(frml_den_elmnts.count('Den_GDP')):
            frml_den_list.append('Den_GDP')

    if 'none' in frml_den_elmnts:
        for k in range(frml_den_elmnts.count('none')):
            frml_den_list.append('none')

    if 'tracost_at2019' in frml_den_elmnts:
        for k in range(frml_den_elmnts.count('tracost_at2019')):
            frml_den_list.append('tracost_at2019')

    if 'totcost_at2019' in frml_den_elmnts:
        for k in range(frml_den_elmnts.count('totcost_at2019')):
            frml_den_list.append('totcost_at2019')

    # frml_numerator
    frml_num_list = []
    if 'GDP_growth' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('GDP_growth')):
            frml_num_list.append('GDP_growth')

    if 'average_across' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('average_across')):
            frml_num_list.append('average_across')

    # if 'average_across_rel2018' in frml_num_elmnts:
    #     for k in range(frml_num_elmnts.count('average_across_rel2018')):
    #         frml_num_list.append('average_across_rel2018')

    if 'average_across_rel' in frml_num_elmnts[0]:
        for k in range(frml_num_elmnts.count(frml_num_elmnts[0])):
            frml_num_list.append(frml_num_elmnts[0])

    if 'direct' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('direct')):
            frml_num_list.append('direct')

    if 'cumulative' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('cumulative')):
            frml_num_list.append('cumulative')

    if 'direct_rel' in frml_num_elmnts[0]:
        for k in range(frml_num_elmnts.count(frml_num_elmnts[0])):
            frml_num_list.append(frml_num_elmnts[0])

    # if 'direct_rel2018' in frml_num_elmnts:
    #     for k in range(frml_num_elmnts.count('direct_rel2018')):
    #         frml_num_list.append('direct_rel2018')

    if 'multiply_sum_across' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('multiply_sum_across')):
            frml_num_list.append('multiply_sum_across')

    if 'share_H2_of_total' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_H2_of_total')):
            frml_num_list.append('share_H2_of_total')

    if 'share_ZEV_of_total' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_ZEV_of_total')):
            frml_num_list.append('share_ZEV_of_total')

    if 'share_LPG_of_total' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_LPG_of_total')):
            frml_num_list.append('share_LPG_of_total')

    if 'share_electric_of_total' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_electric_of_total')):
            frml_num_list.append('share_electric_of_total')

    if 'special_elasticity' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_elasticity')):
            frml_num_list.append('special_elasticity')

    if 'special_Biofuel' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_Biofuel')):
            frml_num_list.append('special_Biofuel')

    if 'special_PT_dist' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_PT_dist')):
            frml_num_list.append('special_PT_dist')

    if 'special_mode_shift' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_mode_shift')):
            frml_num_list.append('special_mode_shift')

    if 'special_freight_shift' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_freight_shift')):
            frml_num_list.append('special_freight_shift')

    if 'special_FiscalCost' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_FiscalCost')):
            frml_num_list.append('special_FiscalCost')

    if 'special_FiscalCost_combine_set_type' in frml_num_elmnts:
        for k in range(frml_num_elmnts.
                       count('special_FiscalCost_combine_set_type')):
            frml_num_list.append('special_FiscalCost_combine_set_type')

    if 'sum_across' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('sum_across')):
            frml_num_list.append('sum_across')
            
    if 'share_forest_of_total' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_forest_of_total')):
            frml_num_list.append('share_forest_of_total')
            
    if 'share_clinker_in_cement' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_clinker_in_cement')):
            frml_num_list.append('share_clinker_in_cement')

    if 'share_renewable_gen' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_renewable_gen')):
            frml_num_list.append('share_renewable_gen')
            
    if 'share_renewable_total' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_renewable_total')):
            frml_num_list.append('share_renewable_total')
            
    if 'share_per_cap_gen_sol' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_per_cap_gen_sol')):
            frml_num_list.append('share_per_cap_gen_sol')
            
    if 'share_per_cap_gen_wat' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_per_cap_gen_wat')):
            frml_num_list.append('share_per_cap_gen_wat')
            
    if 'share_circ_econ_sol' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_circ_econ_sol')):
            frml_num_list.append('share_circ_econ_sol')
            
    if 'share_treat_wat' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('share_treat_wat')):
            frml_num_list.append('share_treat_wat')

    if 'special_ussolarprod' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_ussolarprod')):
            frml_num_list.append('special_ussolarprod')

    if 'special_disolarprod' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_disolarprod')):
            frml_num_list.append('special_disolarprod')

    if 'special_windprod' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_windprod')):
            frml_num_list.append('special_windprod')

    if 'special_gencost' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_gencost')):
            frml_num_list.append('special_gencost')

    if 'special_t&dcost' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_t&dcost')):
            frml_num_list.append('special_t&dcost')

    if 'special_powersectorcost' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_powersectorcost')):
            frml_num_list.append('special_powersectorcost')

    if 'sum_across_combine_set_type' in frml_num_elmnts:
        for k in range(frml_num_elmnts.
                       count('sum_across_combine_set_type')):
            frml_num_list.append('sum_across_combine_set_type')

    if 'sum_across_rel2018' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('sum_across_rel2018')):
            frml_num_list.append('sum_across_rel2018')

    if 'special_EaseImp' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_EaseImp')):
            frml_num_list.append('special_EaseImp')

    if 'special_ExtMng' in frml_num_elmnts:
        for k in range(frml_num_elmnts.count('special_ExtMng')):
            frml_num_list.append('special_ExtMng')

    # Let's check the logic
    correct_logic = False
    correct_logic_1 = False
    correct_logic_2 = False
    correct_logic_3 = False
    if (len(col_title_suff_prm)*len(col_title_suff_set) ==
            col_nums_by_set * col_nums_by_prm):
        correct_logic_1 = True
    else:
        print('    Error source: inconsistent assignation of names/sets and \
              quantification of columns')

    if (len(frml_den_elmnts) == len(frml_num_elmnts)):
        correct_logic_2 = True
    else:
        print('    Error source: incorrect assignation of numerator \
              and denominator instructions')

    # using the size of *col_title_suffix_prm* as proxy of correct assignation:
    '''
    if (len(frml_num_elmnts) == len(all_prms) ==
            len(frml_den_elmnts)) and ('column_per_param' in col_mngmt_ele):
    '''
    if (len(frml_num_elmnts) == len(all_prms) ==
            len(frml_den_elmnts)) and ('column_per_param' in col_mngmt_ele):
        correct_logic_3 = True
    elif 'column_per_param' not in col_mngmt_ele:
        correct_logic_3 = True
    else:
        print('    Error source: different number of parameters and formulas \
              when this condition is needed')

    if correct_logic_1 is True and correct_logic_2 is True and \
            correct_logic_3 is True:
        correct_logic = True

    if correct_logic is False:
        alert_string = 'System is not consistent for ' + str(o_OR_d) + \
            ': ' + str(name)
        print(alert_string, elmnt_id)
        print('---------------------------\n')
        sys.exit()

    '''
    # Now that the conditions have been managed,
    # let's return the variables of interest:
    #   i) each name (outcome or driver) has a column expansion,
    #   ii) # of columns per name,
    #   iii) operation, paramater, and sets (sum and subtract) of numerator
             PER column
    #   iv) operation, paramater, and sets (sum and subtract) of denominator
            PER column
    '''

    # This reflects the total number of columns to iterate:
    #   col_nums = col_nums_by_set * col_nums_by_prm
    # Since we have already checked the logic consistency,
    #   we must proceeed with producing the definitve PER-column data:
    # Let's use the convention: name_set-name_param-name //
    #   often, param-name will be just a '' string
    # Also, let's creat the dictionaries that hold the sets,
    #   numerator formulas, denominator formulas, PER column
    list_column_names = []
    dict_col_mea_cod = {}

    dict_per_column_sets = {}
    dict_per_col_sup_sets = {}
    dict_per_column_params = {}
    dict_per_col_num_frml = {}
    dict_per_col_den_frml = {}
    dict_per_col_set_arrgmt = {}
    dict_per_col_var_mngmt_scen = {}

    column_namer_variable_Management = {'Direct': '_direct',
                                        'wrt_BAU_excess': '_wrtBAU'}

    for vm in range(len(all_var_mngmt)):
        for p in range(col_nums_by_prm):
            for s in range(col_nums_by_set):
                name_SetName_ParamName = col_title_pref + \
                    col_title_suff_set[s] + col_title_suff_prm[p]

                name_set_param_vm = name_SetName_ParamName + \
                    column_namer_variable_Management[all_var_mngmt[vm]]

                # Storing the sets for this column:
                name_SetName = col_title_pref + col_title_suff_set[s]
                this_set_group = dict_sets_per_set_col[name_SetName]
                dict_per_column_sets.update({name_set_param_vm:
                                             this_set_group})
                dict_per_col_sup_sets.update({name_set_param_vm:
                                              all_sup_sets})
                # this column generically can use the appended supporting sets

                # storing the parameters for this column:
                if type(params_for_column[p]) == list:
                    dict_per_column_params.update({name_set_param_vm:
                                                  params_for_column[p]})
                elif type(params_for_column[p]) == str:
                    dict_per_column_params.update({name_set_param_vm:
                                                  [params_for_column[p]]})
                else:
                    print('There is an assignation anomaly. Please review.')
                    sys.exit()

                # storing the formulas for this column
                try:
                    this_numerator_frml = frml_num_list[p]
                except Exception:
                    print(frml_num_list, p)
                    print('There is an inexistent numerator formula: ',
                          frml_num_elmnts, ' Please fix.')
                    sys.exit()

                this_denominator_frml = frml_den_list[p]
                dict_per_col_num_frml.update({name_set_param_vm:
                                              this_numerator_frml})
                dict_per_col_den_frml.update({name_set_param_vm:
                                              this_denominator_frml})

                this_set_arrangement = {'numerator_sum_sets': num_sum_sets,
                                        'numerator_sub_sets': num_sub_sets,
                                        'denominator_sum_sets': den_sum_sets,
                                        'denominator_sub_sets': den_sub_sets,
                                        'numerator_sum_params': num_sum_prms,
                                        'numerator_sub_params': num_sub_prms,
                                        'denominator_sum_params': den_sum_prms,
                                        'denominator_sub_params': den_sub_prms}
                dict_per_col_set_arrgmt.update({name_set_param_vm:
                                                this_set_arrangement})

                dict_per_col_var_mngmt_scen.update({name_set_param_vm:
                                                    {'variable_Management':
                                                     all_var_mngmt[vm],
                                                     'scenarios':
                                                     all_scenarios}})

                list_column_names.append(name_set_param_vm)

                dict_col_mea_cod.update({name_set_param_vm:
                                         {'vm': all_var_mngmt[vm],
                                          'p': col_title_suff_prm[p],
                                          's': col_title_suff_set[s]}})
                # this is useful to know how comparable each column is;
                #   ... ideally, the number of necessary columns for PRIM
                # effectiveness is inferior to the number of total columns.

    processing_dict = {'all_column_names': list_column_names,
                       'meaning_codification': dict_col_mea_cod,
                       'column_sets': dict_per_column_sets,
                       'supporting_sets': dict_per_col_sup_sets,
                       'params': dict_per_column_params,
                       'numerator_frml': dict_per_col_num_frml,
                       'denominator_frml': dict_per_col_den_frml,
                       'set_arrangement': dict_per_col_set_arrgmt,
                       'variable_Management': dict_per_col_var_mngmt_scen,
                       'o_id_as_d': o_id_as_d,
                       'd_u_id': d_u_id,
                       'indicate_last_value':frml_last}
    # the last key applies for an outcome or for a driver

    return srce, tfa, processing_dict


''' ///////////////////////////////////////////////////////////////////
                            END OF FUNCTIONS
'''


if __name__ == '__main__':
    """
    *Abbreviations:*
    ana: analysis
    cat: category
    col: column
    den: denominator
    det: detail
    dict: dictionary
    dl: driver_loop
    fc: file_creator
    fn: file_name
    frml: formula
    inv: involved
    lp: list_possible
    lst: list
    num: numerator
    mngmt: Management
    prc: process / processing
    prm(s): parameter(s)
    srce: source
    strc: structure
    sub: subtract
    sup: supporting
    tfa: tech_fuel_actor
    var: variable
    _p: parallel (useful for multiprocessing)
    _o: order // outcome
    """

    # Recording initial time of execution
    start_1 = time.time()

    ''' ----------------------------------------------------------------------
    Step 1: read the "compartmentalization" Excel file and structure the
    variables to consult; do this for each analysis

    Objective: extract the outcomes / drivers of each BLOCK and ID
    -----------------------------------------------------------------------'''

    all_files_in_this_dir = os.listdir()
    ana_dir = [f for f in all_files_in_this_dir if 'Analysis' in f]
    #ana_dir = [f for f in all_files_in_this_dir if 'Analysis' in f and
    #           '8' not in f]
    # sys.exit()  # this is a temporary hack

    # ana_dir_apply = [i for i in ana_dir if '1' in i]
    # ana_dir = ana_dir_apply

    # Create a pickle that stores all the analyses:
    prim_fc_all = {}

    for ana in ana_dir:  # iterate across all the defined analyses;
        # only the table content varies
        print('Executing for ' + ana)

        fn_prim_structure = './' + ana + '/prim_structure.xlsx'

        df_strc = pd.read_excel(open(fn_prim_structure, 'rb'),
                                sheet_name='Sequences')
        df_set_matching = pd.read_excel(open(fn_prim_structure, 'rb'),
                                        sheet_name='Set_Matching_4_Param_Mult')

        # development task: extract the unique comment columns with
        # additional information to process the variables:
        developing_phase = True
        if developing_phase is True:
            # Unique numerator formulas:
            list_frml_num = []

            lp_outcome_frml_num = list(set
                                       (df_strc['Driver_Formula_Numerator'
                                                ].tolist()))
            for n1 in range(len(lp_outcome_frml_num)):
                if type(lp_outcome_frml_num[n1]) == str:
                    internal_list = lp_outcome_frml_num[n1].split(' ; ')
                    for n2 in range(len(internal_list)):
                        if internal_list[n2] not in list_frml_num:
                            list_frml_num.append(internal_list[n2])

            lp_driver_frml_num = list(set
                                      (df_strc['Outcome_Formula_Numerator'
                                               ].tolist()))
            for n1 in range(len(lp_driver_frml_num)):
                if type(lp_driver_frml_num[n1]) == str:
                    internal_list = lp_driver_frml_num[n1].split(' ; ')
                    for n2 in range(len(internal_list)):
                        if internal_list[n2] not in list_frml_num:
                            list_frml_num.append(internal_list[n2])

            # Unique denominator formulas:
            list_frml_den = []

            lp_outcome_frml_den = list(set
                                       (df_strc['Driver_Formula_Denominator'
                                                ].tolist()))
            for n1 in range(len(lp_outcome_frml_den)):
                if type(lp_outcome_frml_den[n1]) == str:
                    internal_list = lp_outcome_frml_den[n1].split(' ; ')
                    for n2 in range(len(internal_list)):
                        if internal_list[n2] not in list_frml_den:
                            list_frml_den.append(internal_list[n2])

            lp_driver_frml_den = list(set
                                      (df_strc['Outcome_Formula_Denominator'
                                               ].tolist()))
            for n1 in range(len(lp_driver_frml_den)):
                if type(lp_driver_frml_den[n1]) == str:
                    internal_list = lp_driver_frml_den[n1].split(' ; ')
                    for n2 in range(len(internal_list)):
                        if internal_list[n2] not in list_frml_den:
                            list_frml_den.append(internal_list[n2])

            # Unique column management types:
            list_column_mang = []

            lp_outcome_column_mang = list(set
                                          (df_strc['Driver_Column_Management'
                                                   ].tolist()))
            for n1 in range(len(lp_outcome_column_mang)):
                if type(lp_outcome_column_mang[n1]) == str:
                    internal_list = lp_outcome_column_mang[n1].split(' ; ')
                    for n2 in range(len(internal_list)):
                        if internal_list[n2] not in list_column_mang:
                            list_column_mang.append(internal_list[n2])

            lp_driver_column_mang = list(set
                                         (df_strc['Outcome_Column_Management'
                                                  ].tolist()))
            for n1 in range(len(lp_driver_column_mang)):
                if type(lp_driver_column_mang[n1]) == str:
                    internal_list = lp_driver_column_mang[n1].split(' ; ')
                    for n2 in range(len(internal_list)):
                        if internal_list[n2] not in list_column_mang:
                            list_column_mang.append(internal_list[n2])

            list_frml_num.sort()
            list_frml_den.sort()
            list_column_mang.sort()

        '''
        # 1.1. Create the implementation loop:
        '''
        list_index = df_strc.index.tolist()

        list_level = list(set(df_strc['Level'].tolist()))
        list_level.sort()

        list_block = list(set(df_strc['Block_ID'].tolist()))
        list_block.sort()

        list_ID = list(set(df_strc['Table_ID'].tolist()))
        list_ID.sort()

        # Create and populate a dictionary with the instructions to extract
        # the data from the modelling sources:
        prim_fc_p = {'Outcome': {}, 'Driver': {}, 'Driver_U': {}}
        prim_fc_p_unique_ID = []

        # We must make the process faster by storing the unique drivers:
        list_udriver_ID_raw1 = df_strc['Driver_U_ID'].tolist()
        list_udriver_ID_raw2 = [i for i in list_udriver_ID_raw1 if type(i)
                                == int]
        list_udriver_ID = list(set(list_udriver_ID_raw2))
        list_udriver_ID.sort()

        #       We must dynamically store the unique drive IDs only ONCE:
        list_udriver_unique_control = []

        # Creat and populate a dictionary with the PRIM execution order:
        prim_manager = {'Outcome': {}, 'Driver': {}}  # order-dependent
        prim_manager_o = {}

        # Feature - 1st, table controller:
        # Ensure equivalent column names for "prim_fc_p" and "prim_manager"
        for b in range(len(list_block)):  # iterate across block
            df_prim_b = df_strc.loc[df_strc['Block_ID'] ==
                                    list_block[b]]

            # table_ID is equivalent to outcome_ID for this analysis
            table_ID_local = set(df_prim_b['Table_ID'].tolist())
            list_ID_local = list(table_ID_local)
            list_ID_local.sort()

            # create this block dictionary for control
            prim_manager_o.update({list_block[b]: {}})
            prim_manager['Outcome'].update({list_block[b]: {}})
            prim_manager['Driver'].update({list_block[b]: {}})

            for i in range(len(list_ID_local)):  # iterate across ID
                df_prim_b_i = df_prim_b.loc[df_prim_b
                                            ['Table_ID'
                                             ] == list_ID_local[i]]
                df_prim_b_i = df_prim_b_i.reset_index(drop=True)
                # remember: outcome_ID and table_ID are the same

                # read the outcomes and grab the first row of the block
                o_actor = df_prim_b_i['Outcome_Actor'].iloc[0]
                o_id = df_prim_b_i['Outcome_ID'].iloc[0]
                o = df_prim_b_i['Outcome'].iloc[0]
                o_source = df_prim_b_i['Outcome_Source'].iloc[0]
                o_thresh = df_prim_b_i['Outcome_Threshold'].iloc[0]

                o_frml_last = df_prim_b_i['Outcome_Formula_Last'].iloc[0]
                o_frml_num = df_prim_b_i['Outcome_Formula_Numerator'].iloc[0]
                o_frml_den = df_prim_b_i['Outcome_Formula_Denominator'].iloc[0]
                o_frml = [o_frml_num, o_frml_den, o_frml_last]

                o_inv_sets = df_prim_b_i['Outcome_Involved_Sets'].iloc[0]
                o_sup_sets = df_prim_b_i['Outcome_Supporting_Sets'].iloc[0]
                ################
                ##### NEW ######
                # element_dict_2_co2 = {
                #  'CO2e': 'CO2e',
                # 'CO2e_TRN': 'CO2e',
                # 'CO2e_PIUP': 'CO2e',
                # #'CO2e_sources': 'CO2e',
                # 'CO2e_HFC': 'CO2e',
                # 'CO2e_DE': 'CO2e',
                # 'CO2e_PP': 'CO2e',
                # 'CO2e_AFOLU': 'CO2e',
                # 'CO2e_WASTE': 'CO2e'
                # }
                
                ################
                ################
                o_prms = df_prim_b_i['Outcome_Exact_Parameters_Involved'
                                     ].iloc[0]
                o_tfa = df_prim_b_i['Outcome_Tech_or_Fuel_or_Actor'
                                    ].iloc[0]

                o_col_mngmt = df_prim_b_i['Outcome_Column_Management'].iloc[0]

                o_num_sum_sets = df_prim_b_i['Outcome_Numerator_Sum_Sets'
                                             ].iloc[0]
                o_num_sub_sets = df_prim_b_i['Outcome_Numerator_Sub_Sets'
                                             ].iloc[0]
                o_den_sum_sets = df_prim_b_i['Outcome_Denominator_Sum_Sets'
                                             ].iloc[0]
                o_den_sub_sets = df_prim_b_i['Outcome_Denominator_Sub_Sets'
                                             ].iloc[0]
                o_sets_det = [o_num_sum_sets, o_num_sub_sets,
                              o_den_sum_sets, o_den_sub_sets]

                o_num_sum_prms = df_prim_b_i['Outcome_Numerator_Sum_Params'
                                             ].iloc[0]
                o_num_sub_prms = df_prim_b_i['Outcome_Numerator_Sub_Params'
                                             ].iloc[0]
                o_den_sum_prms = df_prim_b_i['Outcome_Denominator_Sum_Params'
                                             ].iloc[0]
                o_den_sub_prms = df_prim_b_i['Outcome_Denominator_Sub_Params'
                                             ].iloc[0]
                o_prms_det = [o_num_sum_prms, o_num_sub_prms,
                              o_den_sum_prms, o_den_sub_prms]

                o_scenarios = df_prim_b_i['Outcome_Involved_Scenarios'
                                          ].iloc[0]
                o_var_mngmt = df_prim_b_i['Outcome_Variable_Management'
                                          ].iloc[0]

                # Store the block / IDs order for prim_manager,
                # as well as the name of the outcome for this block / ID:
                # Design rule: a Driver or Outcome can have 1 or MORE Columns
                local_ID = list_ID_local[i]
                this_block = list_block[b]

                dict_4_update = {'Num_drivers': 0, 'Num_driver_cols': 0,
                                 'Num_outcomes': 0, 'Num_outcome_cols': 0}
                prim_manager_o[list_block[b]].update({local_ID: dict_4_update})

                dict_4_update = {'Name': [], 'Cols': [], 'Threshold': []}
                prim_manager['Outcome'][list_block[b]
                                        ].update({local_ID: dict_4_update})

                dict_4_update = {'Name': [], 'Cols': []}
                prim_manager['Driver'][list_block[b]
                                       ].update({local_ID: dict_4_update})

                # Let's produce cleaner instructions for the other programs                
                elmnt_id = [local_ID, 0]
                srce, tfa, o_prc_dict = frml_ind_2_colinfo(elmnt_id, 'Outcome',
                                                           o, o_source, o_frml,
                                                           o_inv_sets,
                                                           o_sup_sets,
                                                           o_prms, o_tfa,
                                                           o_col_mngmt,
                                                           o_sets_det,
                                                           o_prms_det,
                                                           o_scenarios,
                                                           o_var_mngmt,
                                                           'none',
                                                           'none')

                # Store the general requirements to *pass prim_files_creator*
                # with DIRECT INSTRUCTIONS PER COLUMN
                prim_fc_p['Outcome'].update({local_ID: {'Actor': o_actor,
                                                        'Name': o,
                                                        'Source': srce,
                                                        'Set_Type': tfa,
                                                        'Processing':
                                                        o_prc_dict,
                                                        'Threshold':
                                                        o_thresh,
                                                        'ID': o_id
                                                        }})

                # store the outcome names and column names for reference:
                prim_manager['Outcome'][this_block][local_ID
                                                    ]['Name'].append(o)
                prim_manager['Outcome'][this_block][local_ID
                                                    ]['Threshold'
                                                      ].append(o_thresh)
                prim_manager['Outcome'
                             ][this_block
                               ][local_ID
                                 ]['Cols'
                                   ].append(o_prc_dict['all_column_names'])

                # create a loop to call the drivers
                dl_lst = df_prim_b_i.index.tolist()

                num_cols_total = 0
                for n in range(len(dl_lst)):
                    d_actor = df_prim_b_i['Driver_Actor'].iloc[n]
                    d_type = df_prim_b_i['Driver_Type'].iloc[n]
                    d = df_prim_b_i['Driver'].iloc[n]
                    d_source = df_prim_b_i['Driver_Source'].iloc[n]
                    d_id = df_prim_b_i['Driver_ID'].iloc[n]

                    # Now, let's store the IDs for matching
                    o_id_as_d = int(df_prim_b_i['Outcome_ID_as_Driver'
                                                ].fillna(0).iloc[n])
                    if o_id_as_d > 0:
                        pass_o_id_as_d = o_id_as_d
                    else:
                        pass_o_id_as_d = 'none'

                    d_u_id = int(df_prim_b_i['Driver_U_ID'].fillna(0).iloc[n])
                    if d_u_id > 0:
                        pass_d_u_id = d_u_id
                    else:
                        pass_d_u_id = 'none'

                    d_frml_last = df_prim_b_i['Driver_Formula_Last'].iloc[n]
                    d_frml_num = df_prim_b_i['Driver_Formula_Numerator'
                                             ].iloc[n]
                    d_frml_den = df_prim_b_i['Driver_Formula_Denominator'
                                             ].iloc[n]
                    d_frml = [d_frml_num, d_frml_den, d_frml_last]

                    d_inv_sets = df_prim_b_i['Driver_Involved_Sets'
                                             ].iloc[n]
                    d_sup_sets = df_prim_b_i['Driver_Supporting_Sets'
                                             ].iloc[n]
                    d_prms = df_prim_b_i['Driver_Exact_Parameters_Involved'
                                         ].iloc[n]
                    d_tfa = df_prim_b_i['Driver_Tech_or_Fuel_or_Actor'
                                        ].iloc[n]

                    d_col_mngmt = df_prim_b_i['Driver_Column_Management'
                                              ].iloc[n]

                    d_num_sum_sets = df_prim_b_i['Driver_Numerator_Sum_Sets'
                                                 ].iloc[n]
                    d_num_sub_sets = df_prim_b_i['Driver_Numerator_Sub_Sets'
                                                 ].iloc[n]
                    d_den_sum_sets = df_prim_b_i['Driver_Denominator_Sum_Sets'
                                                 ].iloc[n]
                    d_den_sub_sets = df_prim_b_i['Driver_Denominator_Sub_Sets'
                                                 ].iloc[n]
                    d_sets_det = [d_num_sum_sets, d_num_sub_sets,
                                  d_den_sum_sets, d_den_sub_sets]

                    d_num_sum_prms = df_prim_b_i['Driver_Numerator_Sum_Params'
                                                 ].iloc[n]
                    d_num_sub_prms = df_prim_b_i['Driver_Numerator_Sub_Params'
                                                 ].iloc[n]
                    d_den_sum_prms = \
                        df_prim_b_i['Driver_Denominator_Sum_Params'].iloc[n]
                    d_den_sub_prms = \
                        df_prim_b_i['Driver_Denominator_Sub_Params'].iloc[n]
                    d_prms_det = [d_num_sum_prms, d_num_sub_prms,
                                  d_den_sum_prms, d_den_sub_prms]

                    d_scenarios = df_prim_b_i['Driver_Involved_Scenarios'
                                              ].iloc[n]
                    d_var_mngmt = df_prim_b_i['Driver_Variable_Management'
                                              ].iloc[n]

                    # Let's produce cleaner instructions for other programs:
                    elmnt_id = [local_ID, n]
                    # if d_prms == "UseByTechnology" or d_prms == "ProdcutionByTechnology":
                    #     print(d_prms)
                    #     sys.exit(98)
                    
                    srce, tfa, d_prc_dict = frml_ind_2_colinfo(elmnt_id,
                                                               'Driver',
                                                               d, d_source,
                                                               d_frml,
                                                               d_inv_sets,
                                                               d_sup_sets,
                                                               d_prms, d_tfa,
                                                               d_col_mngmt,
                                                               d_sets_det,
                                                               d_prms_det,
                                                               d_scenarios,
                                                               d_var_mngmt,
                                                               pass_o_id_as_d,
                                                               pass_d_u_id)

                    # if d_frml[0] == "share_ZEV_of_total" or d_frml[0] == "share_ZEV_of_total":
                    #     print(d_frml[0],d_prms)
                    #     sys.exit(99)

                    dict_4_update = {'Actor': d_actor, 'Name': d,
                                     'Source': srce, 'Set_Type': tfa,
                                     'Processing': d_prc_dict,
                                     'o_as_d_ID': o_id_as_d,
                                     'u_d_ID': d_u_id,
                                     'ID': d_id}
                    if local_ID not in prim_fc_p_unique_ID:
                        prim_fc_p['Driver'].update({local_ID:
                                                    {n: dict_4_update}})
                        prim_fc_p_unique_ID.append(local_ID)
                    else:
                        prim_fc_p['Driver'][local_ID
                                            ].update({n: dict_4_update})

                    # Feature - 2nd, unique driver data list:
                    if d_u_id > 0:
                        if d_u_id not in list_udriver_unique_control:
                            # Control storing the data only once:
                            list_udriver_unique_control.append(d_u_id)
                            prim_fc_p['Driver_U'].update({d_u_id:
                                                          dict_4_update})

                    # store the outcome names and column names for reference:
                    prim_manager['Driver'
                                 ][this_block][local_ID]['Name'].append(d)
                    prim_manager['Driver'
                                 ][this_block
                                   ][local_ID
                                     ]['Cols'
                                       ].append(d_prc_dict['all_column_names'])

                    num_cols_total += len(d_prc_dict['all_column_names'])

                # store how many drivers were needed:
                prim_manager_o[this_block
                               ][local_ID]['Num_drivers'] = len(dl_lst)
                prim_manager_o[this_block
                               ][local_ID]['Num_driver_cols'] = num_cols_total
                prim_manager_o[this_block][local_ID]['Num_outcomes'] = 1
                prim_manager_o[this_block
                               ][local_ID
                                 ]['Num_outcome_cols'
                                   ] = len(o_prc_dict['all_column_names'])

        '''
        # 1.2. Export the processing instructions:
        '''
        prim_fc = {'prim_manager': prim_manager,
                   'prim_manager_o': prim_manager_o,
                   'prim_fc_p': prim_fc_p,
                   'set_matching': df_set_matching}

        prim_fc_all.update({ana: prim_fc})

        fn_fc = './' + ana + '/prim_files_creator.pickle'
        with open(fn_fc, 'wb') as outf:
            pickle.dump(prim_fc, outf, protocol=pickle.HIGHEST_PROTOCOL)
        outf.close()

    # Recording final time of execution
    end_1 = time.time()
    te_1 = -start_1 + end_1  # te: time_elapsed
    print(str(te_1) + ' seconds /', str(te_1/60) + ' minutes')
    print('*: For all effects, we have finished the work of this script.')
