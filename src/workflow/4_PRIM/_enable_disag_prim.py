# -*- coding: utf-8 -*-
"""
Created on Sat Jun 10 11:00:19 2023

@author: luisf
"""

import pandas as pd
from copy import deepcopy
import sys

#--
df_ben = pd.read_csv('.\Export_file_enable_benefit_disag.csv', sep=';', index_col=None, header=0)
print(df_ben.columns.tolist())

df_ben_sec = list(set(df_ben['Sector_costos'].tolist()))
df_ben_sec.sort()
df_ben_tech = list(set(df_ben['Technology'].tolist()))
df_ben_tech.sort()

# Select 'sector' and 'technology' columns and drop duplicates
df_ben_uc = df_ben[['Sector_costos', 'Technology']].drop_duplicates()

df_ben_sec_uc = list(set(df_ben_uc['Sector_costos'].tolist()))
df_ben_sec_uc.sort()
df_ben_tech_uc = list(set(df_ben_uc['Technology'].tolist()))
df_ben_tech_uc.sort()


#--
df_emis = pd.read_csv('.\Export_file_enable_emis_disag.csv', sep=';', index_col=None, header=0)
print(df_emis.columns.tolist())

df_emis_sec = list(set(df_emis['Sector'].tolist()))
df_emis_sec.sort()
df_emis_tech = list(set(df_emis['Technology'].tolist()))
df_emis_tech.sort()

# Select 'sector' and 'technology' columns and drop duplicates
df_emis_uc = df_emis[['Sector', 'Technology']].drop_duplicates()

df_emis_sec_uc = list(set(df_emis_uc['Sector'].tolist()))
df_emis_sec_uc.sort()
df_emis_tech_uc = list(set(df_emis_uc['Technology'].tolist()))
df_emis_tech_uc.sort()


#--
# Tests:
if df_ben_sec == df_ben_sec_uc:
    print('Test 1', True)
if df_ben_tech == df_ben_tech_uc:
    print('Test 2', True)
if df_emis_sec == df_emis_sec_uc:
    print('Test 3', True)
if df_emis_tech == df_emis_tech_uc:
    print('Test 4', True)

df_ben_uc.to_csv ( 'ExportDerived_df_ben_uc.csv', index = None, header=True)
df_emis_uc.to_csv ( 'ExportDerived_df_emis_uc.csv', index = None, header=True)

# Benefits:
list_u_df_ben_uc = list(set(df_ben_uc['Sector_costos'].tolist()))
list_u_df_ben_uc.sort()
list_tech_df_ben_uc = list(set(df_ben_uc['Technology'].tolist()))
str_tech_df_ben_uc = " ; ".join(list_tech_df_ben_uc)
dict_df_ben_uc = {}
for sec in list_u_df_ben_uc:
    df_ben_subselect = df_ben_uc.loc[(df_ben_uc['Sector_costos'] == sec)]
    tech_subselect = df_ben_subselect['Technology'].tolist()
    result_string = " ; ".join(tech_subselect)
    
    # print('wth happened')
    # sys.exit()
    
    dict_df_ben_uc.update({sec:deepcopy(result_string)})

# Emissions:
list_u_df_emis_uc = list(set(df_emis_uc['Sector'].tolist()))
list_u_df_emis_uc.sort()
list_tech_df_emis_uc = list(set(df_emis_uc['Technology'].tolist()))
str_tech_df_emis_uc = " ; ".join(list_tech_df_emis_uc)
dict_df_emis_uc = {}
for sec in list_u_df_emis_uc:
    df_emis_subselect = df_emis_uc.loc[(df_emis_uc['Sector'] == sec)]
    tech_subselect = df_emis_subselect['Technology'].tolist()
    result_string = " ; ".join(tech_subselect)
    dict_df_emis_uc.update({sec:deepcopy(result_string)})






