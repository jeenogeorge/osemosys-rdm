import os, sys
import pandas as pd
from copy import deepcopy
import time


def make_new_paths(a_path):
    try:
        os.makedirs(a_path)
    except OSError:
        print ("The directory %s already existed" % a_path)
    else:
        print ("Successfully created the directory %s" % a_path)

element_dict_2_co2 = {
 'CO2e_WASTE':'CO2e',
 'CO2e_PP': 'CO2e',
 'CO2e_DE': 'CO2e',
 'CO2e_CEM':'CO2e',
 'CO2e_HFC':'CO2e',
 'CO2e_LIME':'CO2e',
 'CO2e_LUBRI':'CO2e',
 'CO2e_TRN':'CO2e',
 'CO2e': 'CO2e'
} ### 'CO2eQ', 'CO2eO'


valid_columns_final = [
    "Strategy",
    "Future.ID",
    "Fuel",
    "Technology",
    "Emission",
    "Year",
    "Demand",
    "NewCapacity",
    "AccumulatedNewCapacity",
    "TotalCapacityAnnual",
    "TotalTechnologyAnnualActivity",
    "ProductionByTechnology",
    "UseByTechnology",
    "CapitalInvestment",
    "OperatingCost",
    "DiscountedOperatingCost",
    "AnnualVariableOperatingCost",
    "AnnualFixedOperatingCost",
    "TotalDiscountedCostByTechnology",
    "AnnualTechnologyEmission",
    "AnnualTechnologyEmissionPenaltyByEmission",
    "Capex2025",
    "FixedOpex2025",
    "VarOpex2025",
    "Opex2025",
    "Externalities2025",
    "Submodel"
]

use_column_names_piup_and_waste = [
    "Strategy",
    "Future.ID",
    "Fuel",
    "Technology",
    "Emission",
    "Year",
    "Demand",
    "NewCapacity",
    "AccumulatedNewCapacity",
    "TotalCapacityAnnual",
    "TotalTechnologyAnnualActivity",
    "ProductionByTechnology",
    "UseByTechnology",
    "CapitalInvestment",
    "DiscountedCapitalInvestment",
    "SalvageValue",
    "DiscountedSalvageValue",
    "OperatingCost",
    "DiscountedOperatingCost",
    "AnnualVariableOperatingCost",
    "AnnualFixedOperatingCost",
    "TotalDiscountedCostByTechnology",
    "TotalDiscountedCost",
    "AnnualTechnologyEmission",
    "AnnualTechnologyEmissionPenaltyByEmission",
    "AnnualTechnologyEmissionsPenalty",
    "DiscountedTechnologyEmissionsPenalty",
    "AnnualEmissions",
    "Capex2025",
    "FixedOpex2025",
    "VarOpex2025",
    "Opex2025",
    "Externalities2025",
    "Capex_GDP",
    "FixedOpex_GDP",
    "VarOpex_GDP",
    "Opex_GDP",
    "Externalities_GDP",
]

start1 = time.time()

dir_exps = './t3a_experiments'
list_exps = os.listdir(dir_exps)

list_exps = [i for i in list_exps if '.' not in i]

exception_experiments = ['Experiment_Integrated']

included_scen_underscore = ['BAU_', 'LTS_']
included_scen = ['BAU', 'LTS']

futs = 100
target_list_len = len(list_exps)*(futs + 1)

data_output_files = {}
for scen in included_scen:
    data_output_files.update({scen:{}})
    for f in range(futs+1):
        data_output_files[scen].update({f:[]})
data_output_files_app = deepcopy(data_output_files)

for exp in list_exps:
    if exp not in exception_experiments:
        elements_per_exp_file = os.listdir(dir_exps + '/' + exp)
        elements_in_exec = os.listdir(
            dir_exps + '/' + exp + '/' + 'Executables')
        elements_in_exec_scen = []
        for scen in included_scen_underscore:
            elements_in_exec_scen += [
                i for i in elements_in_exec if scen in i]
        for scen in elements_in_exec_scen:
            scen_str = scen.split('_')[0]
            elements_in_exec_2 = os.listdir(
                dir_exps + '/' + exp + '/' + 'Executables/' + scen)
            csv_file_name = [i for i in elements_in_exec_2 if 'Output.csv' in i][0]
            csv_file_dir = dir_exps + '/' + exp + '/' + 'Executables/' + \
                scen + '/' + csv_file_name 
            csv_df_raw = pd.read_csv(csv_file_dir, index_col=None, header=0)

            # Make baseline adjustments for AFOLU
            if 'AFOLU' in exp:
                csv_df_raw = csv_df_raw.rename(columns={'Run.ID': 'Strategy'})
                csv_df_raw['Strategy'] = csv_df_raw['Strategy'].replace('DDP50', 'DDP')
                csv_df_raw.insert(1, 'Future.ID', [0]*len(csv_df_raw.index.tolist()))
                csv_df_raw['VarOpex2025'] = csv_df_raw['DiscountedOperatingCost']
                csv_df_raw['Opex2025'] = csv_df_raw['DiscountedOperatingCost']
                csv_df_raw['VarOpex_GDP'] = [0]*len(csv_df_raw.index.tolist())
                csv_df_raw['Opex_GDP'] = [0]*len(csv_df_raw.index.tolist())
                valid_column_names = [
                    "Strategy",
                    "Future.ID",
                    "Fuel",
                    "Technology",
                    "Emission",
                    "Year",
                    "Demand",
                    "NewCapacity",
                    "AccumulatedNewCapacity",
                    "TotalCapacityAnnual",
                    "TotalTechnologyAnnualActivity",
                    "ProductionByTechnology",
                    "UseByTechnology",
                    "OperatingCost",
                    "DiscountedOperatingCost",
                    "AnnualVariableOperatingCost",
                    "TotalDiscountedCostByTechnology",
                    "TotalDiscountedCost",
                    "AnnualTechnologyEmission",
                    "AnnualEmissions",
                    "VarOpex2025",
                    "FixedOpex2025",
                    "Opex2025",
                    "VarOpex_GDP",
                    "Opex_GDP"]
                csv_df = deepcopy(csv_df_raw[valid_column_names])
                csv_df["Submodel"] = 'AFOLU'
            elif 'Energy' in exp:
                csv_df = deepcopy(csv_df_raw)
                csv_df["Submodel"] = 'Energy'
            elif 'Transport' in exp:
                csv_df = deepcopy(csv_df_raw)
                csv_df["Submodel"] = 'Transport'
            elif 'PIUP' in exp:
                csv_df = deepcopy(csv_df_raw[use_column_names_piup_and_waste])
                csv_df["Submodel"] = 'PIUP'
            elif 'Waste' in exp:
                csv_df = deepcopy(csv_df_raw[use_column_names_piup_and_waste])
                csv_df["Submodel"] = 'Waste'
            else:
                print('Experiment name not defined for base cases.')
                sys.exit()

            csv_df['Emission'] = csv_df['Emission'].replace(element_dict_2_co2)
            data_output_files[scen_str][0].append(deepcopy(csv_df))

            # print('rev exec')
            # sys.exit()

        elements_in_exp_plat = os.listdir(
            dir_exps + '/' + exp + '/' + 'Experimental_Platform/Futures')
        elements_in_exp_plat_scen = []
        for scen in included_scen:
            elements_in_exp_plat_scen += [
                i for i in elements_in_exp_plat if scen in i]
        for scen in elements_in_exp_plat_scen:
            elements_in_exp_plat_scen_2 = os.listdir(
                dir_exps + '/' + exp + '/' + \
                'Experimental_Platform/Futures/' + scen)
            for f in range(len(elements_in_exp_plat_scen_2)):
                element_in_fut_str = elements_in_exp_plat_scen_2[f]
                fut_id = int(element_in_fut_str.split('_')[-1])
                elements_in_fut = os.listdir(
                    dir_exps + '/' + exp + '/' + \
                        'Experimental_Platform/Futures/' + scen + '/' + \
                        elements_in_exp_plat_scen_2[f])
                csv_file_name = [
                    i for i in elements_in_fut if 'Output.csv' in i][0]
                csv_file_dir = dir_exps + '/' + exp + '/' + \
                    'Experimental_Platform/Futures/' + scen + '/' + \
                    elements_in_exp_plat_scen_2[f] + '/' + csv_file_name
                csv_df_raw = pd.read_csv(csv_file_dir, index_col=None, header=0)

                # Make baseline adjustments for AFOLU
                if 'AFOLU' in exp:
                    null_columns_f, valid_columns_f = [], []
                    for acol in csv_df_raw.columns.tolist():
                        # Check if all values in the column are null
                        if csv_df_raw[acol].isnull().all():
                            null_columns_f.append(acol)
                        else:
                            valid_columns_f.append(acol)
                    csv_df = deepcopy(csv_df_raw[valid_columns_f])
                    #csv_df = deepcopy(csv_df_raw)
                    csv_df["Submodel"] = 'AFOLU'
                elif 'Energy' in exp:
                    csv_df = deepcopy(csv_df_raw)
                    csv_df["Submodel"] = 'Energy'
                elif 'Transport' in exp:
                    csv_df = deepcopy(csv_df_raw)
                    csv_df["Submodel"] = 'Transport'
                elif 'PIUP' in exp:
                    csv_df = deepcopy(csv_df_raw[use_column_names_piup_and_waste])
                    csv_df["Submodel"] = 'PIUP'
                elif 'Waste' in exp:
                    csv_df = deepcopy(csv_df_raw[use_column_names_piup_and_waste])
                    csv_df["Submodel"] = 'Waste'
                else:
                    print('Experiment name not defined for base cases.')
                    sys.exit()

                csv_df['Emission'] = csv_df['Emission'].replace(
                    element_dict_2_co2)
                data_output_files[scen][fut_id].append(deepcopy(csv_df))

                # print('rev futs')
                # sys.exit()

        # print(exp)
        # sys.exit()

# print('Review')
# sys.exit()

# define the name of the directory to be created to store the new data
path_exp_integrated = "./t3a_experiments/Experiment_Integrated"
if 'Experiment_Integrated' not in list_exps:
    make_new_paths(path_exp_integrated)
    make_new_paths(path_exp_integrated + '/Executables')
    make_new_paths(path_exp_integrated + '/Experimental_Platform')
    make_new_paths(path_exp_integrated + '/Experimental_Platform/Futures')

# Iterate across all the internal lists:
for scen in included_scen:
    for f in range(futs+1):
        if f == 0:
            apply_path = \
                path_exp_integrated + '/Executables/' + scen + '_' + str(f)
            make_new_paths(apply_path)
        else:
            apply_path = \
                path_exp_integrated + '/Experimental_Platform/Futures/' + \
                scen + '/' + scen + '_' + str(f)
            make_new_paths(apply_path)

        list_csvs = data_output_files[scen][f]
        df_app_raw = pd.concat(list_csvs, axis=0, ignore_index=True)
        df_app = df_app_raw[valid_columns_final]
        data_output_files_app[scen][f] = deepcopy(df_app)

        # Print the elements:
        df_app.to_csv(apply_path + '/' + scen + '_' + str(f) + '_Output.csv',
                      index = None, header=True)

# End the script:
end1 = time.time()
time_elapsed_1 = -start1 + end1
print( '\nTime elapsed:', str( time_elapsed_1 ) + ' seconds' )