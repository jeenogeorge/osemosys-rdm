from datetime import date
import sys
import pandas as pd
import os
import re
import yaml
import numpy as np
import platform


def get_config_main_path(full_path, base_folder='config_main_files'):
    # Split the path into parts
    parts = full_path.split(os.sep)
    
    # Find the index of the target directory 'osemosys_momf'
    target_index = parts.index('osemosys_momf') if 'osemosys_momf' in parts else None
    
    # If the directory is found, reconstruct the path up to that point
    if target_index is not None:
        base_path = os.sep.join(parts[:target_index + 1])
    else:
        base_path = full_path  # If not found, return the original path
    
    # Append the specified directory to the base path
    appended_path = os.path.join(base_path, base_folder)
    
    return appended_path

def load_and_process_yaml(path):
    """
    Load a YAML file and replace the specific placeholder '${year_apply_discount_rate}' with the year specified in the file.
    
    Args:
    path (str): The path to the YAML file.
    
    Returns:
    dict: The updated data from the YAML file where the specific placeholder is replaced.
    """
    with open(path, 'r') as file:
        # Load the YAML content into 'params'
        params = yaml.safe_load(file)

    # Retrieve the reference year from the YAML file and convert it to string for replacement
    reference_year = str(params['year_apply_discount_rate'])

    # Function to recursively update strings containing the placeholder
    def update_strings(obj):
        if isinstance(obj, dict):
            return {k: update_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [update_strings(element) for element in obj]
        elif isinstance(obj, str):
            # Replace the specific placeholder with the reference year
            return obj.replace('${year_apply_discount_rate}', reference_year)
        else:
            return obj

    # Update all string values in the loaded YAML structure
    updated_params = update_strings(params)

    return updated_params
    
# Read yaml file with parameterization
file_config_address = get_config_main_path(os.path.abspath(''))
params = load_and_process_yaml(os.path.join(file_config_address, 'MOMF_B1_exp_manager.yaml'))
                       
                                 

sys.path.insert(0, params['Executables'])
import local_dataset_creator_0

sys.path.insert(0, params['Futures_4'])
import local_dataset_creator_f

#------------------------------------------------------------------------------------------------
# For macOS system delete a folder hidden
if platform.system() == 'Darwin':
    os.remove(os.path.join('Executables', '.DS_Store'))
#------------------------------------------------------------------------------------------------

'Define control parameters:'
file_aboslute_address = os.path.abspath(params['Bro_out_dat_cre'])
file_adress = file_aboslute_address.replace( params['Bro_out_dat_cre'], '' )

run_for_first_time = True

if run_for_first_time == True:
    local_dataset_creator_0.execute_local_dataset_creator_0_inputs()
    local_dataset_creator_f.execute_local_dataset_creator_f_inputs()

############################################################################################################
df_0_input = pd.read_csv(os.path.join(params['Executables'], params['In_dat_0']), index_col=None, header=0, low_memory=False)

# In case if you use solver='glpk' and glpk='old' uncomment this section
#----------------------------------------------------------------------------------------------------------#
# df_0_input['Strategy'] = df_0_input['Strategy'].replace('DDP50', 'DDP')
#----------------------------------------------------------------------------------------------------------#

df_f_input = pd.read_csv(os.path.join(params['Futures_4'], params['In_dat_f']), index_col=None, header=0, low_memory=False)
li_intput = [df_0_input, df_f_input]
#
df_input = pd.concat(li_intput, axis=0, ignore_index=True)
df_input.sort_values(by=params['by_2'], inplace=True)

dfa_list = [ df_input ]

today = date.today()

#
df_input = dfa_list[0]
df_input.to_csv ( params['ose_cou_in'] + '.csv', index = None, header=True)
df_input.to_csv ( params['ose_cou_in'] + '_' + str( today ).replace( '-', '_' ) + '.csv', index = None, header=True)
