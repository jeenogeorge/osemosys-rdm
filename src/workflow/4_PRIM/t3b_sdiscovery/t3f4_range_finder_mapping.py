# -*- coding: utf-8 -*-
"""
Created on Mon Feb 14 2022

@author: Luis Victor-Gallardo, Andrey Salazar-Vargas, Ignacio Alfaro-Corrales
"""

'''
Objective: work the "sd" file to find the adequate ranges of drivers
'''

import pandas as pd
import sys
from copy import deepcopy
import xlsxwriter

# The main code is below:

#######################################################################
# Step 1) call the results data
ana_id = 1  # THIS IS AN INPUT
exp_id = '1_Experiment'  # THIS IS AN INPUT

sd_filename = 'sd_ana_' + str(ana_id) + '_exp_' + str(exp_id)
sd_file = sd_filename + '.csv'

sd_df = pd.read_csv(sd_file)  

# the columns of an sd are:
sd_cols = ['block', 'o_id', 'outcome', 'level', 'o1_fam', 'o1_col',
'o2_fam', 'o2_col', 'family', 'column', 'period', 'base_thr',
'thr_type', 'thr_range', 'thr_value', 'thr_value_norm', 'prim_option',
'coverage', 'density', 'avg_cov_dev', 'driver_col', 'min', 'max',
'min_norm', 'max_norm', 'query_type']

# the unique elements per column are:
unique_content_dict = {}
for uc in sd_cols:
    uc_list = sd_df[uc].tolist()
    uc_list_unique = list(set(uc_list))
    unique_content_dict.update({uc:uc_list_unique})

# the list with unique drivers is:
sd_driver_unique_raw = unique_content_dict['driver_col']
sd_driver_unique = []
for n in range(len(sd_driver_unique_raw)):
    if 'Mode shift_' in sd_driver_unique_raw[n]:
        sd_driver_unique.append(sd_driver_unique_raw[n].replace('Mode shift_', 'Mode shift '))
    else:
        sd_driver_unique.append(sd_driver_unique_raw[n])
sd_driver_unique_name = [d.split('_')[0] for d in sd_driver_unique]
sd_driver_unique_feat = [d.split('_')[-1] for d in sd_driver_unique]

# the list of unique outcomes is:
sd_outcome_unique = unique_content_dict['outcome']

# the list of unique outcomes is:
unique_periods = unique_content_dict['period']

# also call the prim_structure to get the uncertainties, i.e., what matters:
prim_structure = \
    pd.read_excel(open('./Analysis_' + str(ana_id) + '/prim_structure.xlsx', 'rb'),
                  sheet_name='Sequences')

drivers_uncertainty_df = \
    prim_structure.loc[(prim_structure['Driver_Type'] == 'Uncertainty')]
drivers_intermediary_df = \
    prim_structure.loc[(prim_structure['Driver_Type'] == 'Intermediary')]
drivers_metric_df = \
    prim_structure.loc[(prim_structure['Driver_Type'] == 'Metric of interest')]

drivers_uncertainty = list(set(drivers_uncertainty_df['Driver'].tolist()))
if 'Mode shift' in drivers_uncertainty:
    mshft_idx = drivers_uncertainty.index('Mode shift')
    drivers_uncertainty[mshft_idx] = 'Mode shift public'
    drivers_uncertainty += ['Mode shift nonmot']

drivers_intermediary = list(set(drivers_intermediary_df['Driver'].tolist()))
drivers_metric = list(set(drivers_metric_df['Driver'].tolist()))

prim_structure['Driver']

#######################################################################
# Step 2) you want a super simple list, for every type of outcome,
# that tells the PRIM story

# Define the separation between desirable and risk outcomes:
desirable_outcomes = {\
    'Costs':'low',
    'Emissions':'low',
    'CAPEX':'low',
    'Bus Price':'low',
    'Electricity price':'low'}
risk_outcomes = {\
    'Costs':'high',
    'Emissions':'high',
    'CAPEX':'high',
    'Bus Price':'high',
    'Electricity price':'high'}

# create dictionaries apt for periods (2 for this analysis):
desi_u_data = {}
general_u_keys = ['drivers', 'drivers_max_norm', 'drivers_min_norm',
                  'case', 'condition', 'tiebreaker', 'driver_type',
                  'store_uncertainty_driver_data',
                  'store_intermediary_driver_data']

# create a nested dictionary to store all results:
list_u_data_metrics = sd_outcome_unique + ['All']  # 'All' is last

for metric in list_u_data_metrics:  # iterate across metrics
    desi_u_data.update({metric:{}})

    for key in general_u_keys:  # iterate across keys
        desi_u_data[metric].update({key:{}})

        for p in range(len(unique_periods)):  # iterate across periods
            per = unique_periods[p]
            desi_u_data[metric][key].update({per:[]})

risk_u_data = deepcopy(desi_u_data)

# iterating the across periods and outcomes to search outcomes:
outcome_type_list = ['desirable', 'risk']
for outcome_type in outcome_type_list:
    for p in range(len(unique_periods)):  # "unique_periods" is from above
        per = unique_periods[p]

        # defining elements for the "All" category, i.e., a combination
        subdf_list = []
        drivers_all_uncertainty = []
        drivers_all_intermediary = []

        drivers_all_uncertainty_dict = {}
        drivers_all_intermediary_dict = {}

        for o in sd_outcome_unique:
            if outcome_type == 'desirable':
                direction_outcome = desirable_outcomes[o]
            else:
                direction_outcome = risk_outcomes[o]
            diro = deepcopy(direction_outcome.capitalize())

            this_mask = (sd_df['outcome'] == o
                        ) & (sd_df['period'] == per
                            ) & (sd_df['base_thr'] == diro)
            subdf_list.append(deepcopy(sd_df.loc[this_mask]))

            # now we must find the prodominant range of each driver in the
            # local df
            local_df = deepcopy(subdf_list[-1])
            local_df.reset_index(drop=True, inplace=True)
            local_df_lvl1 = local_df.loc[(local_df['level'] == 1)]  # not actually needed
            local_df_lvl2 = local_df.loc[(local_df['level'] == 2)]  # not actually needed
            local_df_lvl3 = local_df.loc[(local_df['level'] == 3)]  # not actually needed

            # defining elements for local outcomes:
            drivers_all_uncertainty_local = []        
            drivers_all_intermediary_local = []
            drivers_all_uncertainty_local_dict = {}
            drivers_all_intermediary_local_dict = {}
            # let's create a unique list of drivers for each level for unique uncertainties and intermediary:
            list_index = local_df.index.tolist()
            for l_idx in list_index:
                # extract the driver's information:
                this_driver_col_raw = local_df.loc[l_idx, 'driver_col']
                if 'Mode shift_' in this_driver_col_raw:
                    this_driver_col_raw = this_driver_col_raw.replace('Mode shift_', 'Mode shift ')
                else:
                    pass
                this_driver_col = this_driver_col_raw.split('_')[0]
                row_data_min = local_df.loc[l_idx, 'min']
                row_data_max = local_df.loc[l_idx, 'max']
                row_data_minnorm = local_df.loc[l_idx, 'min_norm']
                row_data_maxnorm = local_df.loc[l_idx, 'max_norm']

                # Selecting the direction of the threshold:
                diff_min = row_data_minnorm
                diff_max = 1 - row_data_maxnorm
                # The region must be lower than max:
                if diff_min < diff_max:
                    this_e_dir = 'low'
                    thld_val = deepcopy(row_data_max)
                    thld_val_norm = deepcopy(row_data_maxnorm)
                # The region must be greater than min:
                elif diff_max <= diff_min:
                    this_e_dir = 'high'
                    thld_val = deepcopy(row_data_min)
                    thld_val_norm = deepcopy(row_data_minnorm)
                else:  # something is wrong
                    print('Something is wrong with direction')
                    sys.exit()

                # define a generic dictionary to store the data:
                first_time_dict = {'thr_val':[], 'thr_val_norm':[], 'dir':[]}

                # let's add the cumulative information for each driver at a local and general (i.e., "all") metric dimensions:
                if this_driver_col in drivers_uncertainty:
                    if this_driver_col not in drivers_all_uncertainty_local:
                        drivers_all_uncertainty_local.append(this_driver_col)
                        drivers_all_uncertainty_local_dict.update({this_driver_col:deepcopy(first_time_dict)})
                    else:
                        pass
                    #
                    if this_driver_col not in drivers_all_uncertainty:
                        drivers_all_uncertainty.append(this_driver_col)
                        drivers_all_uncertainty_dict.update({this_driver_col:deepcopy(first_time_dict)})
                    else:
                        pass
                    # stay working with the uncertainty variables:
                    drivers_all_uncertainty_local_dict[this_driver_col]['thr_val'].append(thld_val)
                    drivers_all_uncertainty_local_dict[this_driver_col]['thr_val_norm'].append(thld_val_norm)
                    drivers_all_uncertainty_local_dict[this_driver_col]['dir'].append(this_e_dir)
                    drivers_all_uncertainty_dict[this_driver_col]['thr_val'].append(thld_val)
                    drivers_all_uncertainty_dict[this_driver_col]['thr_val_norm'].append(thld_val_norm)
                    drivers_all_uncertainty_dict[this_driver_col]['dir'].append(this_e_dir)

                elif this_driver_col in drivers_intermediary + drivers_metric:
                    if this_driver_col not in drivers_all_intermediary_local:
                        drivers_all_intermediary_local.append(this_driver_col)
                        drivers_all_intermediary_local_dict.update({this_driver_col:deepcopy(first_time_dict)})
                    else:
                        pass
                    #
                    if this_driver_col not in drivers_all_intermediary:
                        drivers_all_intermediary.append(this_driver_col)
                        drivers_all_intermediary_dict.update({this_driver_col:deepcopy(first_time_dict)})
                    else:
                        pass
                    # stay working with the uncertainty variables:
                    drivers_all_intermediary_local_dict[this_driver_col]['thr_val'].append(thld_val)
                    drivers_all_intermediary_local_dict[this_driver_col]['thr_val_norm'].append(thld_val_norm)
                    drivers_all_intermediary_local_dict[this_driver_col]['dir'].append(this_e_dir)
                    drivers_all_intermediary_dict[this_driver_col]['thr_val'].append(thld_val)
                    drivers_all_intermediary_dict[this_driver_col]['thr_val_norm'].append(thld_val_norm)
                    drivers_all_intermediary_dict[this_driver_col]['dir'].append(this_e_dir)

                else:
                    print('There is a driver name issue')
                    sys.exit()

                #print(l_idx, this_driver_col)

            # By now everything is ready to find the most predominant range per driver:
            # There are five cases:
            # i) there is only one predominant direction; pick the mean of the thresholds
            # ii) one direction is more predominant than another within the [0.1-0.9] range;
            #     pick the mean threshold of the most repeated direction
            # iii) same as ii), but with ranges within [0-0.1] U [0.9-1]
            # iv) the range is not predominant (the number of directions is equal and within [0.1-0.9]: define a trade-off.
            #     IMPORTANT: if there is a trade-off, you must store the average OR apply a tiebraker
            # v) the range is not predominant and outside [0.1-0.9] (within [0-0.1] U [0.9-1]): define inclusive range.

            # 1) First, iterate across the drivers of the local outcome:
            this_d_count = 0
            for this_d in drivers_all_intermediary_local + drivers_all_uncertainty_local:
                if this_d in drivers_all_intermediary_local:
                    driver_type = 'intermediary'
                    thr_val = deepcopy(drivers_all_intermediary_local_dict[this_d]['thr_val'])
                    thr_val_norm = deepcopy(drivers_all_intermediary_local_dict[this_d]['thr_val_norm'])
                    the_dir = deepcopy(drivers_all_intermediary_local_dict[this_d]['dir'])
                else:
                    driver_type = 'uncertainty'
                    thr_val = deepcopy(drivers_all_uncertainty_local_dict[this_d]['thr_val'])
                    thr_val_norm = deepcopy(drivers_all_uncertainty_local_dict[this_d]['thr_val_norm'])
                    the_dir = deepcopy(drivers_all_uncertainty_local_dict[this_d]['dir'])

                # 2) Second, identify the 5 cases:
                # by knowing how many directions occur and in which proportion
                dir_unique = list(set(the_dir))
                direction_content = 'none'
                if len(dir_unique) == 1:
                    if 'high' in dir_unique:
                        direction_content = 'high_unanimous'
                    elif 'low' in dir_unique:
                        direction_content = 'low_unanimous'
                    else:
                        print('There is an issue here (1)')
                        sys.exit()
                elif len(dir_unique) == 2:
                    high_count_list = \
                        [1 for n in the_dir if 'high' in n]
                    high_count = sum(high_count_list)

                    low_count_list = \
                        [1 for n in the_dir if 'low' in n]
                    low_count = sum(low_count_list)

                    # find the predominance:
                    if len(high_count_list) > len(low_count_list):
                        direction_content = 'high_predominant'
                    elif len(high_count_list) < len(low_count_list):
                        direction_content = 'low_predominant'
                    else:
                        direction_content = 'tie'
                else:
                    print('There is an issue here (2)')
                    sys.exit()

                # calculate the thresholds
                high_thlds_list = \
                    [thr_val_norm[n] for n in range(len(the_dir)) if 'high' in the_dir[n]]
                if len(high_thlds_list) != 0:
                    high_thlds_avg = \
                        sum(high_thlds_list)/len(high_thlds_list)
                    high_thlds_avg_pre = 0
                    if high_thlds_avg < 0.01:
                        high_thlds_avg_pre = deepcopy(high_thlds_avg)
                        high_thlds_avg = 99
                else:
                    high_thlds_avg = 99

                low_thlds_list = \
                    [thr_val_norm[n] for n in range(len(the_dir)) if 'low' in the_dir[n]]
                if len(low_thlds_list) != 0:
                    low_thlds_avg = \
                        sum(low_thlds_list)/len(low_thlds_list)
                    low_thlds_avg_pre = 0
                    if low_thlds_avg > 0.99:
                        low_thlds_avg_pre = deepcopy(low_thlds_avg)
                        low_thlds_avg = 99
                else:
                    low_thlds_avg = 99

                #######################################################
                #######################################################
                '''
                if this_d_count == 0:
                    print('check and decide')
                    sys.exit()
                '''

                # find the range:
                if low_thlds_avg < 0.9 and high_thlds_avg > 0.1 and high_thlds_avg != 99 and low_thlds_avg != 99:
                    range_content = 'within'
                elif low_thlds_avg > 0.9 and high_thlds_avg < 0.1 and high_thlds_avg != 99 and low_thlds_avg != 99:
                    range_content = 'outside'
                elif high_thlds_avg == 99 or low_thlds_avg == 99:
                    range_content = 'one_sided'
                else:  # this needs to be reviewed
                    range_content = 'strange'

                # so, identifying the cases:
                case = 99
                if direction_content in ['high_unanimous', 'low_unanimous']:
                    case = 1  # this is going to be "one_sided"
                elif direction_content in ['high_predominant', 'low_predominant'] and range_content in ['within', 'strange']:
                    case = 2
                elif direction_content in ['high_predominant', 'low_predominant'] and range_content in ['outside']:
                    case = 3
                elif direction_content in ['high_predominant', 'low_predominant'] and range_content in ['one_sided']:
                    case = 3
                elif direction_content == 'tie' and range_content == 'within':
                    case = 4
                elif direction_content == 'tie' and range_content == 'outside':
                    case = 5
                elif direction_content == 'tie' and range_content == 'one_sided':
                    case = 1
                    if low_thlds_avg == 99:
                        direction_content = 'high_predominant'
                    if high_thlds_avg == 99:
                        direction_content = 'low_predominant'
                elif direction_content == 'tie' and range_content == 'strange':
                    case = 2
                    if high_thlds_avg > 1-low_thlds_avg:
                        direction_content = 'high_predominant'
                    else:
                        direction_content = 'low_predominant'
                else:
                    print('There is a combination that is not considered')
                    print(outcome_type, '|', per, '|', o, '|', this_d)
                    print(direction_content, '|', range_content)
                    sys.exit()


                '''
                if this_d_count == 11 and per == '31-50' and o == 'CAPEX':
                    print('check 11 agin')
                    sys.exit()
                '''


                if case in [1, 2, 3]:  # definitive
                    this_condition = 'definitive'
                    this_tiebreaker = 'none'
                    if 'high' in direction_content:
                        final_min_norm = high_thlds_avg
                        final_max_norm = 1
                    elif 'low' in direction_content:
                        final_min_norm = 0
                        final_max_norm = low_thlds_avg
                    else:
                        print('There is an issue here (3)')
                        sys.exit()
                    if (final_min_norm > 1 or final_max_norm > 1):
                        if final_min_norm == 99:
                            final_min_norm = high_thlds_avg_pre
                        elif final_max_norm == 99:
                            final_max_norm = low_thlds_avg_pre
                        else:
                            print('There is an issue here (4)')
                            sys.exit()
                elif case == 4:
                    this_condition = 'trade-off'
                    this_tiebreaker = 'high/low average'
                    final_min_norm = (low_thlds_avg + high_thlds_avg)/2
                    final_max_norm = final_min_norm
                elif case == 5:
                    this_condition = 'inclusive'
                    this_tiebreaker = 'none'
                    final_min_norm = high_thlds_avg
                    final_max_norm = low_thlds_avg

                this_d_count += 1
                # 3) Third, we must store the information related to the driver:
                if outcome_type == 'desirable':
                    desi_u_data[o]['driver_type'][per].append(driver_type)
                    desi_u_data[o]['drivers'][per].append(this_d)
                    desi_u_data[o]['drivers_min_norm'][per].append(final_min_norm)
                    desi_u_data[o]['drivers_max_norm'][per].append(final_max_norm)
                    desi_u_data[o]['case'][per].append(case)
                    desi_u_data[o]['condition'][per].append(this_condition)
                    desi_u_data[o]['tiebreaker'][per].append(this_tiebreaker)
                    if this_d_count == (len(drivers_all_intermediary_local) + len(drivers_all_uncertainty_local)):
                        desi_u_data[o]['store_uncertainty_driver_data'][per] = deepcopy(drivers_all_uncertainty_local_dict)
                        desi_u_data[o]['store_intermediary_driver_data'][per] = deepcopy(drivers_all_intermediary_local_dict)
                else:
                    risk_u_data[o]['driver_type'][per].append(driver_type)
                    risk_u_data[o]['drivers'][per].append(this_d)
                    risk_u_data[o]['drivers_min_norm'][per].append(final_min_norm)
                    risk_u_data[o]['drivers_max_norm'][per].append(final_max_norm)
                    risk_u_data[o]['case'][per].append(case)
                    risk_u_data[o]['condition'][per].append(this_condition)
                    risk_u_data[o]['tiebreaker'][per].append(this_tiebreaker)
                    if this_d_count == (len(drivers_all_intermediary_local) + len(drivers_all_uncertainty_local)):
                        risk_u_data[o]['store_uncertainty_driver_data'][per] = deepcopy(drivers_all_uncertainty_local_dict)
                        risk_u_data[o]['store_intermediary_driver_data'][per] = deepcopy(drivers_all_intermediary_local_dict)
                #
            #
        #
        # Now, we must do the exact same process but for the lists with driver data all across the spectrum of outcomes.
        # 4) Iterate across the drivers of the general outcomes:
        this_d_count = 0
        for this_d in drivers_all_intermediary + drivers_all_uncertainty:
            if this_d in drivers_all_intermediary:
                driver_type = 'intermediary'
                thr_val = deepcopy(drivers_all_intermediary_dict[this_d]['thr_val'])
                thr_val_norm = deepcopy(drivers_all_intermediary_dict[this_d]['thr_val_norm'])
                the_dir = deepcopy(drivers_all_intermediary_dict[this_d]['dir'])
            else:
                driver_type = 'uncertainty'
                thr_val = deepcopy(drivers_all_uncertainty_dict[this_d]['thr_val'])
                thr_val_norm = deepcopy(drivers_all_uncertainty_dict[this_d]['thr_val_norm'])
                the_dir = deepcopy(drivers_all_uncertainty_dict[this_d]['dir'])

            # 5) Identify the 5 cases:
            # by knowing how many directions occur and in which proportion
            dir_unique = list(set(the_dir))
            direction_content = 'none'
            if len(dir_unique) == 1:
                if 'high' in dir_unique:
                    direction_content = 'high_unanimous'
                elif 'low' in dir_unique:
                    direction_content = 'low_unanimous'
                else:
                    print('There is an issue here (1.all)')
                    sys.exit()
            elif len(dir_unique) == 2:
                high_count_list = \
                    [1 for n in the_dir if 'high' in n]
                high_count = sum(high_count_list)

                low_count_list = \
                    [1 for n in the_dir if 'low' in n]
                low_count = sum(low_count_list)

                # find the predominance:
                if len(high_count_list) > len(low_count_list):
                    direction_content = 'high_predominant'
                elif len(high_count_list) < len(low_count_list):
                    direction_content = 'low_predominant'
                else:
                    direction_content = 'tie'
            else:
                print('There is an issue here (2.all)')
                sys.exit()

            # calculate the thresholds
            high_thlds_list = \
                [thr_val_norm[n] for n in range(len(the_dir)) if 'high' in the_dir[n]]
            if len(high_thlds_list) != 0:
                high_thlds_avg = \
                    sum(high_thlds_list)/len(high_thlds_list)
                high_thlds_avg_pre = 0
                if high_thlds_avg < 0.01:
                    high_thlds_avg_pre = deepcopy(high_thlds_avg)
                    high_thlds_avg = 99
            else:
                high_thlds_avg = 99

            low_thlds_list = \
                [thr_val_norm[n] for n in range(len(the_dir)) if 'low' in the_dir[n]]
            if len(low_thlds_list) != 0:
                low_thlds_avg = \
                    sum(low_thlds_list)/len(low_thlds_list)
                low_thlds_avg_pre = 0
                if low_thlds_avg > 0.99:
                    low_thlds_avg_pre = deepcopy(low_thlds_avg)
                    low_thlds_avg = 99
            else:
                low_thlds_avg = 99

            # find the range:
            if low_thlds_avg < 0.9 and high_thlds_avg > 0.1 and high_thlds_avg != 99 and low_thlds_avg != 99:
                range_content = 'within'
            elif low_thlds_avg > 0.9 and high_thlds_avg < 0.1 and high_thlds_avg != 99 and low_thlds_avg != 99:
                range_content = 'outside'
            elif high_thlds_avg == 99 or low_thlds_avg == 99:
                range_content = 'one_sided'
            else:  # this needs to be reviewed
                range_content = 'strange'

            # so, identifying the cases (2):
            case = 99
            if direction_content in ['high_unanimous', 'low_unanimous']:
                case = 1  # this is going to be "one_sided"
            elif direction_content in ['high_predominant', 'low_predominant'] and range_content in ['within', 'strange']:
                case = 2
            elif direction_content in ['high_predominant', 'low_predominant'] and range_content in ['outside']:
                case = 3
            elif direction_content in ['high_predominant', 'low_predominant'] and range_content in ['one_sided']:
                case = 3
            elif direction_content == 'tie' and range_content == 'within':
                case = 4
            elif direction_content == 'tie' and range_content == 'outside':
                case = 5
            elif direction_content == 'tie' and range_content == 'one_sided':
                case = 1
                if low_thlds_avg == 99:
                    direction_content = 'high_predominant'
                if high_thlds_avg == 99:
                    direction_content = 'low_predominant'
            elif direction_content == 'tie' and range_content == 'strange':
                case = 2
                if high_thlds_avg > 1-low_thlds_avg:
                    direction_content = 'high_predominant'
                else:
                    direction_content = 'low_predominant'
            else:
                print('There is a combination that is not considered')
                print(outcome_type, '|', per, '|', 'All', '|', this_d)
                print(direction_content, '|', range_content)
                sys.exit()

            if case in [1, 2, 3]:  # definitive
                this_condition = 'definitive'
                this_tiebreaker = 'none'
                if 'high' in direction_content:
                    final_min_norm = high_thlds_avg
                    final_max_norm = 1
                elif 'low' in direction_content:
                    final_min_norm = 0
                    final_max_norm = low_thlds_avg
                else:
                    print('There is an issue here (3.all)')
                    sys.exit()
                if (final_min_norm > 1 or final_max_norm > 1):
                    if final_min_norm == 99:
                        final_min_norm = high_thlds_avg_pre
                    elif final_max_norm == 99:
                        final_max_norm = low_thlds_avg_pre
                    else:
                        print('There is an issue here (4.all)')
                        sys.exit()
            elif case == 4:
                this_condition = 'trade-off'
                this_tiebreaker = 'high/low average'
                final_min_norm = (low_thlds_avg + high_thlds_avg)/2
                final_max_norm = final_min_norm
            elif case == 5:
                this_condition = 'inclusive'
                this_tiebreaker = 'none'
                final_min_norm = high_thlds_avg
                final_max_norm = low_thlds_avg

            this_d_count += 1
            # 6) We must store the information related to the driver:
            if outcome_type == 'desirable':
                desi_u_data['All']['driver_type'][per].append(driver_type)
                desi_u_data['All']['drivers'][per].append(this_d)
                desi_u_data['All']['drivers_min_norm'][per].append(final_min_norm)
                desi_u_data['All']['drivers_max_norm'][per].append(final_max_norm)
                desi_u_data['All']['case'][per].append(case)
                desi_u_data['All']['condition'][per].append(this_condition)
                desi_u_data['All']['tiebreaker'][per].append(this_tiebreaker)
                if this_d_count == (len(drivers_all_intermediary) + len(drivers_all_uncertainty)):
                    desi_u_data['All']['store_uncertainty_driver_data'][per] = deepcopy(drivers_all_uncertainty_dict)
                    desi_u_data['All']['store_intermediary_driver_data'][per] = deepcopy(drivers_all_intermediary_dict)
            else:
                risk_u_data['All']['driver_type'][per].append(driver_type)
                risk_u_data['All']['drivers'][per].append(this_d)
                risk_u_data['All']['drivers_min_norm'][per].append(final_min_norm)
                risk_u_data['All']['drivers_max_norm'][per].append(final_max_norm)
                risk_u_data['All']['case'][per].append(case)
                risk_u_data['All']['condition'][per].append(this_condition)
                risk_u_data['All']['tiebreaker'][per].append(this_tiebreaker)
                if this_d_count == (len(drivers_all_intermediary) + len(drivers_all_uncertainty)):
                    risk_u_data['All']['store_uncertainty_driver_data'][per] = deepcopy(drivers_all_uncertainty_dict)
                    risk_u_data['All']['store_intermediary_driver_data'][per] = deepcopy(drivers_all_intermediary_dict)
            #
        #
    #
#

# print('stayed here 0')
# sys.exit()

# Step 3) Print the results:
# create the empty lists to print in long format
long_outcome_type = []
long_metric = []
long_period = []
long_drivers = []
long_drivers_max_norm = []
long_drivers_min_norm = []
long_case = []
long_condition = []
long_tiebreaker = []
long_driver_type = []

# fill the lists with the *desirable data*:
for metric in list_u_data_metrics:
    for p in range(len(unique_periods)):  # "unique_periods" is from above
        per = unique_periods[p]
        print_driver_list = desi_u_data[metric]['drivers'][per]
        for n in range(len(print_driver_list)):
            print_driver = desi_u_data[metric]['drivers'][per][n]
            print_driver_type = desi_u_data[metric]['driver_type'][per][n]
            print_max_norm = desi_u_data[metric]['drivers_max_norm'][per][n]
            print_min_norm = desi_u_data[metric]['drivers_min_norm'][per][n]
            print_case = desi_u_data[metric]['case'][per][n]
            print_condition = desi_u_data[metric]['condition'][per][n]
            print_tiebreaker = desi_u_data[metric]['tiebreaker'][per][n]

            long_outcome_type.append('Desirable')
            long_metric.append(metric)
            long_period.append(per)
            long_drivers.append(print_driver)
            long_driver_type.append(print_driver_type)
            long_drivers_max_norm.append(print_max_norm)
            long_drivers_min_norm.append(print_min_norm)
            long_case.append(print_case)
            long_condition.append(print_condition)
            long_tiebreaker.append(print_tiebreaker)

# fill the lists with the *risk data*:
for metric in list_u_data_metrics:
    for p in range(len(unique_periods)):  # "unique_periods" is from above
        per = unique_periods[p]
        print_driver_list = risk_u_data[metric]['drivers'][per]
        for n in range(len(print_driver_list)):
            print_driver = risk_u_data[metric]['drivers'][per][n]
            print_driver_type = risk_u_data[metric]['driver_type'][per][n]
            print_max_norm = risk_u_data[metric]['drivers_max_norm'][per][n]
            print_min_norm = risk_u_data[metric]['drivers_min_norm'][per][n]
            print_case = risk_u_data[metric]['case'][per][n]
            print_condition = risk_u_data[metric]['condition'][per][n]
            print_tiebreaker = risk_u_data[metric]['tiebreaker'][per][n]

            long_outcome_type.append('Risk')
            long_metric.append(metric)
            long_period.append(per)
            long_drivers.append(print_driver)
            long_driver_type.append(print_driver_type)
            long_drivers_max_norm.append(print_max_norm)
            long_drivers_min_norm.append(print_min_norm)
            long_case.append(print_case)
            long_condition.append(print_condition)
            long_tiebreaker.append(print_tiebreaker)

# create the dictionary with the fill data
end_result_dict = {'Outcome_Type':long_outcome_type,
                   'Metric':long_metric,
                   'Period':long_period,
                   'Driver':long_drivers,
                   'Driver_Type':long_driver_type,
                   'Min_Norm':long_drivers_min_norm,
                   'Max_Norm':long_drivers_max_norm,
                   'Case':long_case,
                   'Condition':long_condition,
                   'Tiebreaker':long_tiebreaker}
end_result_df = pd.DataFrame(end_result_dict)

# the content we want to print is:
sheet_names = ['ranges']
df_list = [end_result_df]

# storing the data:
add_ae_id = '_a' + str(ana_id) + '_e' + str(exp_id)
filename_end_result = \
    't3f4_predominant_ranges' + add_ae_id + '.xlsx'
writer_fn_end_result = pd.ExcelWriter(filename_end_result,
                                      engine='xlsxwriter')
for n in range(len(sheet_names)):
    df_list[n].to_excel(writer_fn_end_result,
                        sheet_name=sheet_names[n], index=False)
#writer_fn_end_result.save()
writer_fn_end_result.close()

print('The identification of ranges (thresholds and directions) ' + \
       'for analysis ' + str(ana_id) + ' and experiment ' + \
       str(exp_id) + ' is complete.')

#########################    
#### PASO EXTRA DE MAPEO
#########################

# libro_u=pd.ExcelFile( 'Units.xlsx' )
# hoja_u=libro_u.parse( 'Units' , skiprows = 0 )
# encabezados_u=list(hoja_u)
# col_d=list(hoja_u[encabezados_u[0]])
# col_u=list(hoja_u[encabezados_u[1]])
# dicUnits=dict(zip(col_d,col_u))


# libro=pd.ExcelFile( filename_end_result )
# hoja=libro.parse( 'ranges' , skiprows = 0 )
# encabezados=list(hoja)
# # print(encabezados)

# encabezados_mod=['Outcome_Type', 'Metric', 'Period', 'Driver', 'Driver_Type', 'Min', 'Max', 'Units', 'Min_Norm', 'Max_Norm', 'base_thr', 'thr_type', 'thr_range', 'thr_value', 'thr_value_norm', 'Case', 'Condition', 'Tiebreaker']

# col_min_norm=list( hoja['Min_Norm'] )
# col_max_norm=list( hoja['Max_Norm'] )
# matriz=list()
# for i in range(len(encabezados)):
#     matriz.append(list( hoja[encabezados[i]] ))


# tabla=pd.read_csv('sd_ana_1_exp_1_Experiment.csv')

# col_min2 = tabla['min'].tolist()
# col_max2 = tabla['max'].tolist()
# col_min_norm2 = tabla['min_norm'].tolist()
# col_max_norm2 = tabla['max_norm'].tolist()
# col_driver = tabla['driver_col'].tolist()

# ############################
# ### NUEVAS COLUMNAS
# ############################
# col_base_thr = tabla['base_thr'].tolist()
# col_thr_type = tabla['thr_type'].tolist()
# col_thr_range = tabla['thr_range'].tolist()
# col_thr_value = tabla['thr_value'].tolist()
# col_thr_value_norm = tabla['thr_value_norm'].tolist()
# ############################


# #dic_min=dict(zip(col_min_norm2,col_min2))
# #dic_max=dict(zip(col_max_norm2,col_max2))

# mapeo_min=list()
# mapeo_max=list()
# mapeo_units=list()

# mapeo_base_thr=list()
# mapeo_thr_type=list()
# mapeo_thr_range=list()
# mapeo_thr_value=list()
# mapeo_thr_value_norm=list()

# for i in range(len(matriz[0])):
#     a=1
#     for j in range(len(list(col_min2))):
#         if matriz[5][i] == col_min_norm2[j] and matriz[6][i]== col_max_norm2[j]:
#             mapeo_min.append(col_min2[j])
#             mapeo_max.append(col_max2[j])
#             mapeo_units.append(dicUnits[col_driver[j]])
#             mapeo_base_thr.append(col_base_thr[j])
#             mapeo_thr_type.append(col_thr_type[j])
#             mapeo_thr_range.append(col_thr_range[j])
#             mapeo_thr_value.append(col_thr_value[j])
#             mapeo_thr_value_norm.append(col_thr_value_norm[j])
#             a=2
#             # print('IN')
#             break
#         elif matriz[5][i] == col_min_norm2[j] and matriz[5][i] != 0 and matriz[5][i] != 1:
#             mapeo_min.append(col_min2[j])
#             mapeo_max.append(col_max2[j])
#             mapeo_units.append(dicUnits[col_driver[j]])
#             mapeo_base_thr.append(col_base_thr[j])
#             mapeo_thr_type.append(col_thr_type[j])
#             mapeo_thr_range.append(col_thr_range[j])
#             mapeo_thr_value.append(col_thr_value[j])
#             mapeo_thr_value_norm.append(col_thr_value_norm[j])
#             a=2
#             # print('IN')
#             break
#         elif matriz[5][i] == col_max_norm2[j] and matriz[5][i] != 0 and matriz[5][i] != 1:
#             mapeo_min.append(col_min2[j])
#             mapeo_max.append(col_max2[j])
#             mapeo_units.append(dicUnits[col_driver[j]])
#             mapeo_base_thr.append(col_base_thr[j])
#             mapeo_thr_type.append(col_thr_type[j])
#             mapeo_thr_range.append(col_thr_range[j])
#             mapeo_thr_value.append(col_thr_value[j])
#             mapeo_thr_value_norm.append(col_thr_value_norm[j])
#             a=2
#             # print('IN')
#             break
#     if a==1:
#         # print(i+1)
#         mapeo_min.append('CANNOT BE FOUND')
#         mapeo_max.append('CANNOT BE FOUND')
#         mapeo_units.append('CANNOT BE FOUND')
#         mapeo_base_thr.append('CANNOT BE FOUND')
#         mapeo_thr_type.append('CANNOT BE FOUND')
#         mapeo_thr_range.append('CANNOT BE FOUND')
#         mapeo_thr_value.append('CANNOT BE FOUND')
#         mapeo_thr_value_norm.append('CANNOT BE FOUND')
#     else:
#         a=1
            
# # print(len(mapeo_min),len(col_min2),len(matriz[0]))
# # print(len(mapeo_max),len(col_max2))
    

# matriz.insert(5,mapeo_min)
# matriz.insert(6,mapeo_max)
# matriz.insert(7,mapeo_units)

# matriz.insert(10,mapeo_base_thr)
# matriz.insert(11,mapeo_thr_type)
# matriz.insert(12,mapeo_thr_range)
# matriz.insert(13,mapeo_thr_value)
# matriz.insert(14,mapeo_thr_value_norm)

# wb=xlsxwriter.Workbook('t3f4_predominant_ranges_NOMINALES.xlsx')
# sheet=wb.add_worksheet('ranges')
# sheet.write_row(0,0,encabezados_mod)
# for i in range(len(matriz)):
#     sheet.write_column(1,i,matriz[i])
# wb.close()
