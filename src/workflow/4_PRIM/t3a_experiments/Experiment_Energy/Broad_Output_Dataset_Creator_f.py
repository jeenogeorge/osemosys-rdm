from datetime import date
import sys
import pandas as pd
import os
import re
import numpy as np

sys.path.insert(0, 'Executables')
import local_dataset_creator_0

sys.path.insert(0, 'Experimental_Platform\Futures')
import local_dataset_creator_f

'Define control parameters:'

file_aboslute_address = os.path.abspath("Broad_Output_Dataset_Creator_f.py")
file_adress = re.escape( file_aboslute_address.replace( 'Broad_Output_Dataset_Creator_f.py', '' ) ).replace( '\:', ':' )

run_for_first_time = True

if run_for_first_time == True:
    local_dataset_creator_0.execute_local_dataset_creator_0_outputs()
    local_dataset_creator_f.execute_local_dataset_creator_f_outputs()
    local_dataset_creator_0.execute_local_dataset_creator_0_inputs()
    local_dataset_creator_f.execute_local_dataset_creator_f_inputs()

############################################################################################################
df_0_output = pd.read_csv('.\Executables\output_dataset_0.csv', index_col=None, header=0)
df_0_output['Scen_fut'] = df_0_output['Strategy'].astype(str) + "_" + df_0_output['Future.ID'].astype(str)

# print(df_0_output.columns.tolist())
# print('please review the columns and check')
# sys.exit()

df_f_output = pd.read_csv( file_adress + '\Experimental_Platform\Futures\output_dataset_f.csv', index_col=None, header=0)

li_output = [df_0_output, df_f_output]
#
df_output = pd.concat(li_output, axis=0, ignore_index=True)
df_output.sort_values(by=['Strategy','Future.ID','Fuel','Technology','Emission','Year'], inplace=True)

############################################################################################################
df_0_input = pd.read_csv('.\Executables\input_dataset_0.csv', index_col=None, header=0)

df_f_input = pd.read_csv('.\Experimental_Platform\Futures\input_dataset_f.csv', index_col=None, header=0)
li_intput = [df_0_input, df_f_input]
#
df_input = pd.concat(li_intput, axis=0, ignore_index=True)
df_input.sort_values(by=['Future.ID','Strategy.ID','Strategy','Fuel','Technology','Emission','Season','Year'], inplace=True)

#############################
#############################
libro = pd.ExcelFile(os.path.join('0_From_Confection', 'B1_Model_Structure.xlsx'))
hoja=libro.parse( 'sector' , skiprows = 0 )
encabezados=list(hoja)

col_t=list(hoja[encabezados[0]])
col_s=list(hoja[encabezados[1]])
col_ss=list(hoja[encabezados[2]])
dicSector=dict(zip(col_t,col_s))
dicSpecificSector=dict(zip(col_t,col_ss))


df_output=df_output.assign(Sector=np.nan)
df_output=df_output.assign(SpecificSector=np.nan)

df_input=df_input.assign(Sector=np.nan)
df_input=df_input.assign(SpecificSector=np.nan)


llaves=list(dicSector.keys())

for i in range(len(llaves)):
    df_output.loc[df_output['Technology'] == llaves[i], 'Sector'] =  dicSector[llaves[i]]
    df_output.loc[df_output['Technology'] == llaves[i], 'SpecificSector'] =  dicSpecificSector[llaves[i]]
    df_input.loc[df_input['Technology'] == llaves[i], 'Sector'] =  dicSector[llaves[i]]
    df_input.loc[df_input['Technology'] == llaves[i], 'SpecificSector'] =  dicSpecificSector[llaves[i]]

#############################
#############################

dfa_list = [ df_output, df_input ]

today = date.today()
#
df_output = dfa_list[0]
df_output.to_csv ( 'OSEMOSYS_JAM_Energy_Output.csv', index = None, header=True)
df_output.to_csv ( 'OSEMOSYS_JAM_Energy_Output_' + str( today ).replace( '-', '_' ) + '.csv', index = None, header=True)
#
df_input = dfa_list[1]
df_input.to_csv ( 'OSEMOSYS_JAM_Energy_Input.csv', index = None, header=True)
df_input.to_csv ( 'OSEMOSYS_JAM_Energy_Input_' + str( today ).replace( '-', '_' ) + '.csv', index = None, header=True)
