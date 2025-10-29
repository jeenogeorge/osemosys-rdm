# -*- coding: utf-8 -*-
"""
@author: luisf
"""
# SOURCE: https://pypi.org/project/lhsmdu/
import os, os.path
import multiprocessing as mp
import errno
import scipy
from scipy import stats
import pandas as pd
import numpy as np
import xlrd
import csv
import os, os.path
import sys
import math
from copy import deepcopy
import time
import re
import linecache
import gc
import shutil
import pickle
import operator
# https://pythonhosted.org/pyDOE/randomized.html#latin-hypercube
from pyDOE import *

#### Seccion de lectura de datos
def LeerExcel( ubicacion ):   
    datos = pd.ExcelFile( ubicacion )
    return datos

def LeerHoja2( excel , nombre , delay_filas ):
    data = excel.parse( nombre , skiprows = delay_filas )
    return data

def LeerHeaders( hoja ):
    headers = list( hoja )
    return headers

def LeerCol( hoja , nombre ):
    Col = list( hoja[nombre] )
    return Col

def ListaHojas( excel ):
    listaHojas = excel.sheet_names
    return listaHojas

def interpolation_multiplier2( time_list, value_list, new_relative_final_value):
    # Rememeber that the 'old_relative_final_value' is 1
    #old_relative_final_value = 1
    new_value_list = []
    # We select a list that goes from the "Initial_Year_of_Uncertainty" to the Final Year of the Time Series
    initial_year_index = time_list.index( 2027 )
    #
    target_final_year_increment = 2050 - 2027
    total_final_year_increment = new_relative_final_value-1
    delta_increment = total_final_year_increment/target_final_year_increment
    #
    multiplier_list = [1]*len(time_list)
    for n in range(len(time_list)):
        if n > initial_year_index and time_list[n] < 2050:
            multiplier_list[n] = delta_increment + multiplier_list[n-1]
        elif time_list[n] >= 2050:
            multiplier_list[n] = new_relative_final_value
    #
    # We now recreate the new_value_list considering the fraction before and after the Initial_Year_of_Uncertainty
    #fraction_list_counter = 0
    for n in range( len( time_list ) ):
        new_value_list.append(float(value_list[n])*multiplier_list[n])
    #
    # We return the list:
    return new_value_list


def bubbleSort(arr,labels):
    n = len(arr)
    copia_arr=arr
    for i in range(n):
        for j in range(0, n-i-1):
            if copia_arr[j] > copia_arr[j+1] :
                copia_arr[j], copia_arr[j+1] = copia_arr[j+1], copia_arr[j] 
                labels[j], labels[j+1] = labels[j+1], labels[j]
    return(copia_arr,labels)

'''
We implement OSEMOSYS-CR in a procedimental code
The main features are:
inherited_scenarios : implemented in procedimental code
function_C_mathprog_parallel : we will insert it all in a function to run in parallel
interpolation : implemented in a function for linear of non-linear time-series
'''
#
def set_first_list( Executed_Scenario ):
    #
    first_list_raw = os.listdir( './Experimental_Platform/Futures/' + str( Executed_Scenario ) )
    #
    global first_list
    first_list = [e for e in first_list_raw if ( '.csv' not in e ) and ( 'Table' not in e ) and ( '.py' not in e ) and ( '__pycache__' not in e ) ]

############################################################################################################################################################################################################

def data_processor( case, Executed_Scenario, unpackaged_useful_elements, year_disc, rate_disc ):
    #
    Reference_driven_distance =     unpackaged_useful_elements[0]
    Reference_occupancy_rate =      unpackaged_useful_elements[1]
    Fleet_Groups_inv =              unpackaged_useful_elements[2]
    time_range_vector =             unpackaged_useful_elements[3]
    dict_gdp_ref      =             unpackaged_useful_elements[4]
    #
    # Briefly open up the system coding to use when processing for visualization:
    df_fuel_to_code = pd.read_excel( './0_From_Confection/A-I_Classifier_Modes_Transport.xlsx', sheet_name='Fuel_to_Code' )
    df_fuel_2_code_fuel_list        = df_fuel_to_code['Code'].tolist()
    df_fuel_2_code_plain_english    = df_fuel_to_code['Plain_English'].tolist()
    df_tech_to_code = pd.read_excel( './0_From_Confection/A-I_Classifier_Modes_Transport.xlsx', sheet_name='Tech_to_Code' )
    df_tech_2_code_fuel_list        = df_tech_to_code['Techs'].tolist()
    df_tech_2_code_plain_english    = df_tech_to_code['Plain_English'].tolist()
    #
    # 1 - Always call the structure for the model:
    #-------------------------------------------#
    structure_filename = "./0_From_Confection/B1_Model_Structure.xlsx"
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
    for col in range(1,11+1):  # 11 columns
        S_DICT_sets_structure['set'].append( sheet_sets_structure.iat[0, col] )
        S_DICT_sets_structure['initial'].append( sheet_sets_structure.iat[1, col] )
        S_DICT_sets_structure['number_of_elements'].append( int( sheet_sets_structure.iat[2, col] ) )
        #
        element_number = int( sheet_sets_structure.iat[2, col] )
        this_elements_list = []
        if element_number > 0:
            for n in range( 1, element_number+1 ):
                this_elements_list.append( sheet_sets_structure.iat[2+n, col] )
        S_DICT_sets_structure['elements_list'].append( this_elements_list )
    #
    S_DICT_params_structure = {'category':[],'parameter':[],'number_of_elements':[],'index_list':[]}
    param_category_list = []
    for col in range(1,30+1):  # 30 columns
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
    for col in range(1,43+1):  # 43 columns
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
    #-------------------------------------------#
    all_vars = ['Demand',
                'NewCapacity',
                'AccumulatedNewCapacity',
                'TotalCapacityAnnual',
                'TotalTechnologyAnnualActivity',
                'ProductionByTechnology',
                'UseByTechnology',
                'CapitalInvestment',
                'DiscountedCapitalInvestment',
                'SalvageValue',
                'DiscountedSalvageValue',
                'OperatingCost',
                'DiscountedOperatingCost',
                'AnnualVariableOperatingCost',
                'AnnualFixedOperatingCost',
                'TotalDiscountedCostByTechnology',
                'TotalDiscountedCost',
                'AnnualTechnologyEmission',
                'AnnualTechnologyEmissionPenaltyByEmission',
                'AnnualTechnologyEmissionsPenalty',
                'DiscountedTechnologyEmissionsPenalty',
                'AnnualEmissions'
                ]
    #
    more_vars = [   'DistanceDriven',
                    'Fleet',
                    'NewFleet',
                    'ProducedMobility']
    #
    filter_vars = [ 'FilterFuelType',
                    'FilterVehicleType',
                    # 'DiscountedTechnEmissionsPen',
                    #
                    'Capex'+str(year_disc), # CapitalInvestment
                    'FixedOpex'+str(year_disc), # AnnualFixedOperatingCost
                    'VarOpex'+str(year_disc), # AnnualVariableOperatingCost
                    'Opex'+str(year_disc), # OperatingCost
                    'Externalities'+str(year_disc), # AnnualTechnologyEmissionPenaltyByEmission
                    #
                    'Capex_GDP', # CapitalInvestment
                    'FixedOpex_GDP', # AnnualFixedOperatingCost
                    'VarOpex_GDP', # AnnualVariableOperatingCost
                    'Opex_GDP', # OperatingCost
                    'Externalities_GDP' # AnnualTechnologyEmissionPenaltyByEmission
                    ]
    #
    all_vars_output_dict = [ {} for e in range( len( first_list ) ) ]
    #
    output_header = [ 'Strategy', 'Future.ID','Fuel','Technology','Emission','Year']
    #-------------------------------------------------------#
    for v in range( len( all_vars ) ):
        output_header.append( all_vars[v] )
    for v in range( len( more_vars ) ):
        output_header.append( more_vars[v] )
    for v in range( len( filter_vars ) ):
        output_header.append( filter_vars[v] )
    #-------------------------------------------------------#
    this_strategy = first_list[case].split('_')[0] 
    this_future   = first_list[case].split('_')[1]
    list_gdp_ref = dict_gdp_ref[int(this_future)]
    #-------------------------------------------------------#
    #
    vars_as_appear = []
    data_name = str( './Experimental_Platform/Futures/' + str( Executed_Scenario ) + '/' + first_list[case] ) + '/' + str(first_list[case]) + '_output.txt'
    #
    n = 0
    break_this_while = False
    while break_this_while == False:
        n += 1
        structure_line_raw = linecache.getline(data_name, n)
        if 'No. Column name  St   Activity     Lower bound   Upper bound    Marginal' in structure_line_raw:
            ini_line = deepcopy( n+2 )
        if 'Karush-Kuhn-Tucker' in structure_line_raw:
            end_line = deepcopy( n-1 )
            break_this_while = True
            break
    #
    for n in range(ini_line, end_line, 2 ):
        structure_line_raw = linecache.getline(data_name, n)
        structure_list_raw = structure_line_raw.split(' ')
        #
        structure_list_raw_2 = [ s_line for s_line in structure_list_raw if s_line != '' ]
        structure_line = structure_list_raw_2[1]
        structure_list = structure_line.split('[')
        the_variable = structure_list[0]
        #
        if the_variable in all_vars:
            set_list = structure_list[1].replace(']','').replace('\n','').split(',')
            #--%
            index = S_DICT_vars_structure['variable'].index( the_variable )
            this_variable_indices = S_DICT_vars_structure['index_list'][ index ]
            #
            #--%
            if 'y' in this_variable_indices:
                data_line = linecache.getline(data_name, n+1)
                data_line_list_raw = data_line.split(' ')
                data_line_list = [ data_cell for data_cell in data_line_list_raw if data_cell != '' ]
                useful_data_cell = data_line_list[1]
                #--%
                if useful_data_cell != '0':
                    #
                    if the_variable not in vars_as_appear:
                        vars_as_appear.append( the_variable )
                        all_vars_output_dict[case].update({ the_variable:{} })
                        all_vars_output_dict[case][the_variable].update({ the_variable:[] })
                        #
                        for n in range( len( this_variable_indices ) ):
                            all_vars_output_dict[case][the_variable].update( { this_variable_indices[n]:[] } )
                    #--%
                    this_variable = vars_as_appear[-1]
                    all_vars_output_dict[case][this_variable][this_variable].append( useful_data_cell )
                    for n in range( len( this_variable_indices ) ):
                        all_vars_output_dict[case][the_variable][ this_variable_indices[n] ].append( set_list[n] )
                #
            #
            elif 'y' not in this_variable_indices:
                data_line = linecache.getline(data_name, n+1)
                data_line_list_raw = data_line.split(' ')
                data_line_list = [ data_cell for data_cell in data_line_list_raw if data_cell != '' ]
                useful_data_cell = data_line_list[1]
                #--%
                if useful_data_cell != '0':
                    #
                    if the_variable not in vars_as_appear:
                        vars_as_appear.append( the_variable )
                        all_vars_output_dict[case].update({ the_variable:{} })
                        all_vars_output_dict[case][the_variable].update({ the_variable:[] })
                        #
                        for n in range( len( this_variable_indices ) ):
                            all_vars_output_dict[case][the_variable].update( { this_variable_indices[n]:[] } )
                    #--%
                    this_variable = vars_as_appear[-1]
                    all_vars_output_dict[case][this_variable][this_variable].append( useful_data_cell )
                    for n in range( len( this_variable_indices ) ):
                        all_vars_output_dict[case][the_variable][ this_variable_indices[n] ].append( set_list[n] )
        #--%
        else:
            pass
    #
    linecache.clearcache()
    #%%
    #-----------------------------------------------------------------------------------------------------------%
    output_adress = './Experimental_Platform/Futures/' + str( Executed_Scenario ) + '/' + str( first_list[case] )
    combination_list = [] # [fuel, technology, emission, year]
    data_row_list = []
    for var in range( len( vars_as_appear ) ):
        this_variable = vars_as_appear[var]
        this_var_dict = all_vars_output_dict[case][this_variable]
        #--%
        index = S_DICT_vars_structure['variable'].index( this_variable )
        this_variable_indices = S_DICT_vars_structure['index_list'][ index ]
        #--------------------------------------#
        for k in range( len( this_var_dict[this_variable] ) ):
            this_combination = []
            #
            if 'f' in this_variable_indices:
                this_combination.append( this_var_dict['f'][k] )
            else:
                this_combination.append( '' )
            #
            if 't' in this_variable_indices:
                this_combination.append( this_var_dict['t'][k] )
            else:
                this_combination.append( '' )
            #
            if 'e' in this_variable_indices:
                this_combination.append( this_var_dict['e'][k] )
            else:
                this_combination.append( '' )
            #
            if 'l' in this_variable_indices:
                this_combination.append( '' )
            else:
                this_combination.append( '' )
            #
            if 'y' in this_variable_indices:
                this_combination.append( this_var_dict['y'][k] )
            else:
                this_combination.append( '' )
            #
            if this_combination not in combination_list:
                combination_list.append( this_combination )
                data_row = ['' for n in range( len( output_header ) ) ]
                # print('check', len(data_row), len(run_id) )
                data_row[0] = this_strategy
                data_row[1] = this_future
                data_row[2] = this_combination[0] # Fuel
                data_row[3] = this_combination[1] # Technology
                data_row[4] = this_combination[2] # Emission
                # data_row[7] = this_combination[3]
                data_row[5] = this_combination[4] # Year
                #
                var_position_index = output_header.index( this_variable )
                data_row[ var_position_index ] = this_var_dict[ this_variable ][ k ]
                data_row_list.append( data_row )
            else:
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] )
                #
                var_position_index = output_header.index( this_variable )
                #
                if 'l' in this_variable_indices: 
                    #
                    if str(this_data_row[ var_position_index ]) != '' and str(this_var_dict[ this_variable ][ k ]) != '' and ( 'Rate' not in this_variable ):
                        this_data_row[ var_position_index ] = str(  float( this_data_row[ var_position_index ] ) + float( this_var_dict[ this_variable ][ k ] ) )
                    elif str(this_data_row[ var_position_index ]) == '' and str(this_var_dict[ this_variable ][ k ]) != '':
                        this_data_row[ var_position_index ] = str( float( this_var_dict[ this_variable ][ k ] ) )
                    elif str(this_data_row[ var_position_index ]) != '' and str(this_var_dict[ this_variable ][ k ]) == '':
                        pass
                else:
                    this_data_row[ var_position_index ] = this_var_dict[ this_variable ][ k ]
                #
                data_row_list[ ref_index ]  = deepcopy( this_data_row )
                #
            #
            if this_variable == 'TotalTechnologyAnnualActivity' or this_variable == 'NewCapacity':
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                this_tech = this_combination[1]
                if this_tech in list( Fleet_Groups_inv.keys() ):
                    group_tech = Fleet_Groups_inv[ this_tech ]
                    #
                    this_year = this_combination[4]
                    this_year_index = time_range_vector.index( int( this_year ) )
                    #
                    ref_var_position_index = output_header.index( this_variable )
                    #
                    '''
                    'Techs_Auto', 'Techs_Motos', 'Techs_Buses_Pri', 'Techs_Buses_Pub', 'Techs_Buses_Micro', 'Techs_Telef', 'Techs_Trains', 'Techs_Trains_Freight', 'Techs_He_Freight', 'Techs_Li_Freight'
                    '''
                    if group_tech in ['Techs_Auto', 'Techs_Motos', 'Techs_Buses_Pri', 'Techs_Buses_Pub', 'Techs_Buses_Micro', 'Techs_He_Freight', 'Techs_Li_Freight']:
                        ''' Debug section start
                        '''
                        try:
                            driven_distance = float( Reference_driven_distance[ this_strategy ][int(this_future)][ group_tech ][ this_year_index ] )
                        except Exception:
                            print(this_strategy)
                            print(this_future)
                            print(group_tech)
                            print(this_year_index)
                            print('error here')
                        #
                        if group_tech not in ['Techs_Auto', 'Techs_Buses_Pri', 'Techs_Buses_Pub', 'Techs_Buses_Micro']:
                            passenger_per_vehicle = 1
                        else:
                            try:
                                passenger_per_vehicle = float( Reference_occupancy_rate[ this_strategy ][int(this_future)][ group_tech ][ this_year_index ]  )
                            except Exception:
                                print(list(Reference_occupancy_rate[ this_strategy ][int(this_future)].keys()), group_tech)
                                print('check alert')
                                sys.exit()
                        ''' Debug section end
                        '''
                        #
                        if this_variable == 'NewCapacity':
                            var_position_index = output_header.index( 'NewFleet' )
                            this_data_row[ var_position_index ] =  round( (10**9)*float( this_data_row[ ref_var_position_index ] )/driven_distance, 4)
                        #
                        if this_variable == 'TotalTechnologyAnnualActivity':
                            #
                            var_position_index = output_header.index( 'Fleet' )
                            this_data_row[ var_position_index ] =  round( (10**9)*float( this_data_row[ ref_var_position_index ] )/driven_distance, 4)
                            #
                            var_position_index = output_header.index( 'DistanceDriven' )
                            this_data_row[ var_position_index ] = round(driven_distance, 4)
                            #
                            var_position_index = output_header.index( 'ProducedMobility' )
                            this_data_row[ var_position_index ] =  round( float( this_data_row[ ref_var_position_index ] )*passenger_per_vehicle, 4)
                        #
                        data_row_list[ ref_index ] = deepcopy( this_data_row )
                        #
                    #
                    ###################################################################################################
                    #
                #
            #
            # Creating convinience filters for the analysis of model outputs:
            this_tech = this_combination[1]
            if this_tech in list( Fleet_Groups_inv.keys() ):
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                var_position_index = output_header.index( 'FilterFuelType' )
                ############################################
                # By Fuel Type
                for r in range( len( df_fuel_2_code_fuel_list ) ):
                    if df_fuel_2_code_fuel_list[r] in this_tech:
                        this_data_row[ var_position_index ] = df_fuel_2_code_plain_english[ r ]
                        break
                ############################################
                var_position_index = output_header.index( 'FilterVehicleType' )
                # By vehicle type
                for r in range( len( df_tech_2_code_fuel_list ) ):
                    if df_tech_2_code_fuel_list[r] in this_tech:
                        this_data_row[ var_position_index ] = df_tech_2_code_plain_english[ r ]
                        break
                data_row_list[ ref_index ] = deepcopy( this_data_row )
            #
            output_csv_r = rate_disc*100
            output_csv_year = int(year_disc)
            #
            if this_combination[2] in ['Accidents', 'Health', 'Congestion'] and this_variable == 'AnnualTechnologyEmissionPenaltyByEmission':
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                ref_var_position_index = output_header.index( 'AnnualTechnologyEmissionPenaltyByEmission' )
                new_var_position_index = output_header.index( 'Externalities'+str(output_csv_year) )
                new2_var_position_index = output_header.index( 'Externalities_GDP' )
                #
                this_year = this_combination[4]
                this_year_index = time_range_vector.index( int( this_year ) )
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = str( float(this_data_row[ ref_var_position_index ])/list_gdp_ref[this_year_index] )
                #
                data_row_list[ ref_index ] = deepcopy( this_data_row )
                #
            #
            ''' $ This is new (beginning) $ '''
            #
            if this_variable == 'CapitalInvestment':
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                ref_var_position_index = output_header.index( 'CapitalInvestment' )
                new_var_position_index = output_header.index( 'Capex'+str(output_csv_year) )
                new2_var_position_index = output_header.index( 'Capex_GDP' )
                #
                this_year = this_combination[4]
                this_year_index = time_range_vector.index( int( this_year ) )
                #
                # Here we must add an adjustment to the capital investment to make the fleet constant:
                this_cap_inv = float(this_data_row[ ref_var_position_index ])
                this_data_row[ref_var_position_index] = \
                    str(this_cap_inv)  # Here we re-write the new capacity to adjust the system
                #
                resulting_value_raw = this_cap_inv/((1 + output_csv_r/100)**(float(this_year) - output_csv_year))
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = str( float(this_data_row[ ref_var_position_index ])/list_gdp_ref[this_year_index] )
                #
                data_row_list[ ref_index ] = deepcopy( this_data_row )
                #
            #
            if this_variable == 'AnnualFixedOperatingCost':
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                ref_var_position_index = output_header.index( 'AnnualFixedOperatingCost' )
                new_var_position_index = output_header.index( 'FixedOpex'+str(output_csv_year) )
                new2_var_position_index = output_header.index( 'FixedOpex_GDP' )
                #
                this_year = this_combination[4]
                this_year_index = time_range_vector.index( int( this_year ) )
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = str( float(this_data_row[ ref_var_position_index ])/list_gdp_ref[this_year_index] )
                #
                data_row_list[ ref_index ] = deepcopy( this_data_row )
                #
            #
            if this_variable == 'AnnualVariableOperatingCost':
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                ref_var_position_index = output_header.index( 'AnnualVariableOperatingCost' )
                new_var_position_index = output_header.index( 'VarOpex'+str(output_csv_year) )
                new2_var_position_index = output_header.index( 'VarOpex_GDP' )
                #
                this_year = this_combination[4]
                this_year_index = time_range_vector.index( int( this_year ) )
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = str( float(this_data_row[ ref_var_position_index ])/list_gdp_ref[this_year_index] )
                #
                data_row_list[ ref_index ] = deepcopy( this_data_row )
                #
            #
            if this_variable == 'OperatingCost':
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                ref_var_position_index = output_header.index( 'OperatingCost' )
                new_var_position_index = output_header.index( 'Opex'+str(output_csv_year) )
                new2_var_position_index = output_header.index( 'Opex_GDP' )
                #
                this_year = this_combination[4]
                this_year_index = time_range_vector.index( int( this_year ) )
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = str( float(this_data_row[ ref_var_position_index ])/list_gdp_ref[this_year_index] )
                #
                data_row_list[ ref_index ] = deepcopy( this_data_row )
                #
            #
            ''' $ (end) $ '''
            #
        #
    #
    non_year_combination_list = []
    non_year_combination_list_years = []
    for n in range( len( combination_list ) ):
        this_combination = combination_list[ n ]
        this_non_year_combination = [ this_combination[0], this_combination[1], this_combination[2] ]
        if this_combination[4] != '' and this_non_year_combination not in non_year_combination_list:
            non_year_combination_list.append( this_non_year_combination )
            non_year_combination_list_years.append( [ this_combination[4] ] )
        elif this_combination[4] != '' and this_non_year_combination in non_year_combination_list:
            non_year_combination_list_years[ non_year_combination_list.index( this_non_year_combination ) ].append( this_combination[4] )
    #
    for n in range( len( non_year_combination_list ) ):
        if len( non_year_combination_list_years[n] ) != len(time_range_vector):
            #
            this_existing_combination = non_year_combination_list[n]
            this_existing_combination.append( '' )
            this_existing_combination.append( non_year_combination_list_years[n][0] )
            ref_index = combination_list.index( this_existing_combination )
            this_existing_data_row = deepcopy( data_row_list[ ref_index ] )
            #
            for n2 in range( len(time_range_vector) ):
                #
                if time_range_vector[n2] not in non_year_combination_list_years[n]:
                    #
                    data_row = ['' for n in range( len( output_header ) ) ]
                    data_row[0] = this_strategy
                    data_row[1] = this_future
                    data_row[2] = non_year_combination_list[n][0]
                    data_row[3] = non_year_combination_list[n][1]
                    data_row[4] = non_year_combination_list[n][2]
                    data_row[5] = time_range_vector[n2]
                    #
                    for n3 in range( len( vars_as_appear ) ):
                        this_variable = vars_as_appear[n3]
                        this_var_dict = all_vars_output_dict[case][this_variable]
                        index = S_DICT_vars_structure['variable'].index( this_variable )
                        this_variable_indices = S_DICT_vars_structure['index_list'][ index ]
                        #
                        var_position_index = output_header.index( this_variable )
                        #
                        print_true = False
                        #
                        if ( 'f' in this_variable_indices and str(non_year_combination_list[n][0]) != '' ): # or ( 'f' not in this_variable_indices and str(non_year_combination_list[n][0]) == '' ):
                            print_true = True
                        else:
                            pass
                        #
                        if ( 't' in this_variable_indices and str(non_year_combination_list[n][1]) != '' ): # or ( 't' not in this_variable_indices and str(non_year_combination_list[n][1]) == '' ):
                            print_true = True
                        else:
                            pass
                        #
                        if ( 'e' in this_variable_indices and str(non_year_combination_list[n][2]) != '' ): # or ( 'e' not in this_variable_indices and str(non_year_combination_list[n][2]) == '' ):
                            print_true = True
                        else:
                            pass
                        #
                        if 'y' in this_variable_indices and ( str( this_existing_data_row[ var_position_index ] ) != '' ) and print_true == True:
                            data_row[ var_position_index ] = '0'
                            #
                        else:
                            pass
                    #
                    data_row_list.append( data_row )
    #--------------------------------------#
    with open( output_adress + '/' + str( first_list[case] ) + '_Output' + '.csv', 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow( output_header )
        for n in range( len( data_row_list ) ):
            csvwriter.writerow( data_row_list[n] )
    #-----------------------------------------------------------------------------------------------------------%
    shutil.os.remove(data_name)
    #-----------------------------------------------------------------------------------------------------------%
    gc.collect(generation=2)
    time.sleep(0.05)
    #-----------------------------------------------------------------------------------------------------------%
    print(  'We finished with printing the outputs.', case)

############################################################################################################################################################################################################
def main_executer(n1, Executed_Scenario, packaged_useful_elements, year_disc, rate_disc):
    print('# ' + str(n1+1) + ' of ' + Executed_Scenario )
    set_first_list( Executed_Scenario )
    file_aboslute_address = os.path.abspath("experiment_manager.py")
    file_adress = re.escape( file_aboslute_address.replace( 'experiment_manager.py', '' ) ).replace( '\:', ':' )
    #
    case_address = file_adress + r'Experimental_Platform\\Futures\\' + Executed_Scenario + '\\' + str( first_list[n1] )
    #
    str_scen_fut = first_list[n1].split('_')
    str_scen, str_fut = str_scen_fut[0], str_scen_fut[-1]
    if str_scen in ['LTS', 'BAU']:
        #
        this_case = [ e for e in os.listdir( case_address ) if '.txt' in e ]
        #
        str1 = "start /B start cmd.exe @cmd /k cd " + file_adress
        #
        data_file = case_address.replace('./','').replace('/','\\') + '\\' + str( this_case[0] )
        output_file = case_address.replace('./','').replace('/','\\') + '\\' + str( this_case[0] ).replace('.txt','') + '_output' + '.txt'
        #
        str2 = "glpsol -m OSeMOSYS_Model.txt -d " + str( data_file )  +  " -o " + str(output_file)
        os.system( str1 and str2 )
        time.sleep(1)
        #
        data_processor(n1,Executed_Scenario,packaged_useful_elements, year_disc, rate_disc)
        #
    #
    else:
        print('!!! At execution, we skip: future ', str_fut, ' and scenario ', str_scen, ' !!!' )
        #
    #
#
def function_C_mathprog_parallel( fut_index, inherited_scenarios, unpackaged_useful_elements ):
    #
    scenario_list =                     unpackaged_useful_elements[0]
    S_DICT_sets_structure =             unpackaged_useful_elements[1]
    S_DICT_params_structure =           unpackaged_useful_elements[2]
    list_param_default_value_params =   unpackaged_useful_elements[3]
    list_param_default_value_value =    unpackaged_useful_elements[4]
    print_adress =                      unpackaged_useful_elements[5]
    all_futures =                       unpackaged_useful_elements[6]
    #
    Reference_driven_distance =         unpackaged_useful_elements[7]
    Fleet_Groups_inv =                  unpackaged_useful_elements[8]
    time_range_vector =                 unpackaged_useful_elements[9]
    #
    # Briefly open up the system coding to use when processing for visualization:
    df_fuel_to_code = pd.read_excel( './0_From_Confection/A-I_Classifier_Modes_Transport.xlsx', sheet_name='Fuel_to_Code' )
    df_fuel_2_code_fuel_list        = df_fuel_to_code['Code'].tolist()
    df_fuel_2_code_plain_english    = df_fuel_to_code['Plain_English'].tolist()
    df_tech_to_code = pd.read_excel( './0_From_Confection/A-I_Classifier_Modes_Transport.xlsx', sheet_name='Tech_to_Code' )
    df_tech_2_code_fuel_list        = df_tech_to_code['Techs'].tolist()
    df_tech_2_code_plain_english    = df_tech_to_code['Plain_English'].tolist()
    #
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
    # header = ['Scenario','Parameter','REGION','TECHNOLOGY','FUEL','EMISSION','MODE_OF_OPERATION','TIMESLICE','YEAR','SEASON','DAYTYPE','DAILYTIMEBRACKET','STORAGE','Value']
    header_indices = ['Scenario','Parameter','r','t','f','e','m','l','y','ls','ld','lh','s','value']
    #
    fut = all_futures[fut_index - scen*len( all_futures ) ]
    #
    print('# This is future:', fut, ' and scenario ', scenario_list[scen] )
    #
    try:
        scen_file_dir = print_adress + '/' + str( scenario_list[scen] ) + '/' + str( scenario_list[scen] ) + '_' + str( fut )
        os.mkdir( scen_file_dir )

    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        pass
    #
    this_scenario_data = inherited_scenarios[ scenario_list[scen] ][ fut ]
    #
    g= open( print_adress + '/' + str( scenario_list[scen] ) + '/' + str( scenario_list[scen] ) + '_' + str( fut ) + '/' + str( scenario_list[scen] ) + '_' + str( fut ) + '.txt',"w+")
    g.write( '###############\n#    Sets     #\n###############\n#\n' )
    g.write( 'set DAILYTIMEBRACKET :=  ;\n' )
    g.write( 'set DAYTYPE :=  ;\n' )
    g.write( 'set SEASON :=  ;\n' )
    g.write( 'set STORAGE :=  ;\n' )
    #
    for n1 in range( len( S_DICT_sets_structure['set'] ) ):
        if S_DICT_sets_structure['number_of_elements'][n1] != 0:
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
        if default_value >= 0:
            default_value = int( default_value )
        else:
            pass
        #
        this_param_index = S_DICT_params_structure['parameter'].index( this_param )
        this_param_keys = S_DICT_params_structure['index_list'][this_param_index]
        #
        if len( this_scenario_data[ this_param ]['value'] ) != 0:
            #
#            f.write( 'param ' + this_param + ':=\n' )
            if len(this_param_keys) != 2:
                g.write( 'param ' + this_param + ' default ' + str( default_value ) + ' :=\n' )
            else:
                g.write( 'param ' + this_param + ' default ' + str( default_value ) + ' :\n' )
            #
            #-----------------------------------------#
            if len(this_param_keys) == 2: #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
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
            if len(this_param_keys) == 3:
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
                            #print(val,value_indices[val],this_param)
                            these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                        for val in range( len( these_values ) ):
                            g.write( str( these_values[val] ) + ' ' )
                        g.write('\n') #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
            #%%%
            if len(this_param_keys) == 4:
                this_set_element_unique_all = []
                for pkey in range( len(this_param_keys)-2 ):
                    for i in range( 2, len(header_indices)-1 ):
                        if header_indices[i] == this_param_keys[pkey]:
                            this_set_element = this_scenario_data[ this_param ][ header_indices[i] ]
                            this_set_element_unique_all.append( list( set( this_set_element ) ) )
                #
                this_set_element_unique_1 = deepcopy( this_set_element_unique_all[0] )
                this_set_element_unique_2 = deepcopy( this_set_element_unique_all[1] )
                #
                for n1 in range( len( this_set_element_unique_1 ) ):
                    for n2 in range( len( this_set_element_unique_2 ) ): #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
                        g.write( '[' + str( this_set_element_unique_1[n1] ) + ',' + str( this_set_element_unique_2[n2] ) + ',*,*]:\n' )
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
                        #
                        for s in range( len( second_last_set_element_unique ) ):
                            g.write( second_last_set_element_unique[s] + ' ' )
                            #
                            value_indices_s = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[-2] ] ) if x == str( second_last_set_element_unique[s] ) ]
                            value_indices_n1 = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[0] ] ) if x == str( this_set_element_unique_1[n1] ) ]
                            value_indices_n2 = [ i for i, x in enumerate( this_scenario_data[ this_param ][ this_param_keys[1] ] ) if x == str( this_set_element_unique_2[n2] ) ]
                            r_index = set(value_indices_s) & set(value_indices_n1) & set(value_indices_n2)
                            value_indices = list( r_index )
                            value_indices.sort()
                            #
                            # these_values = this_scenario_data[ this_param ]['value'][ value_indices[0]:value_indices[-1]+1 ]
                            these_values = []
                            for val in range( len( value_indices ) ):
                                these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                            for val in range( len( these_values ) ):
                                g.write( str( these_values[val] ) + ' ' )
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
                this_set_element_unique_3 = deepcopy(this_set_element_unique_all[2])

                last_set_element = np.array(this_scenario_data[this_param][this_param_keys[-1]])
                last_set_element_unique = np.unique(last_set_element)

                second_last_set_element = np.array(this_scenario_data[this_param][this_param_keys[-2]])
                second_last_set_element_unique = np.unique(second_last_set_element)

                long_list1 = this_scenario_data[this_param][this_param_keys[1]]
                long_list2 = this_scenario_data[this_param][this_param_keys[2]]
                concat_result = list(map(lambda x, y: x + '-' + y, long_list1, long_list2))
                concat_result_set = list(set(concat_result))

                short_list1, short_list2 = \
                    zip(*(s.split('-') for s in concat_result_set))
                short_list1_set = list(set(short_list1))
                short_list2_set = list(set(short_list2))

                for n1 in range(len(this_set_element_unique_1)):
                    # for n2 in range(len(this_set_element_unique_2)):
                    # for n3 in range(len(this_set_element_unique_3)):
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
                                g.write('\n')

                            else:
                                print('Never happens right?')
                                sys.exit()

            #
            #g.write('\n') 
            #-----------------------------------------#
            g.write( ';\n\n' )
    #
    # remember the default values for printing:
    g.write('param AccumulatedAnnualDemand default 0 :=\n;\n')
    # if scenario_list[scen] == 'BAU':
    #     g.write('param AnnualEmissionLimit default 99999 :=\n;\n')
    g.write('param AnnualEmissionLimit default 99999 :=\n;\n') # here we are using no Emission Limit
    g.write('param AnnualExogenousEmission default 0 :=\n;\n')
    g.write('param CapacityOfOneTechnologyUnit default 0 :=\n;\n')
    g.write('param CapitalCostStorage default 0 :=\n;\n')
    g.write('param Conversionld default 0 :=\n;\n')
    g.write('param Conversionlh default 0 :=\n;\n')
    g.write('param Conversionls default 0 :=\n;\n')
    g.write('param DaySplit default 0.00137 :=\n;\n')
    g.write('param DaysInDayType default 7 :=\n;\n')
    g.write('param DepreciationMethod default 1 :=\n;\n')
    g.write('param DiscountRate default 0.0277 :=\n;\n')
    g.write('param EmissionsPenalty default 0 :=\n;\n')
    g.write('param MinStorageCharge default 0 :=\n;\n')
    g.write('param ModelPeriodEmissionLimit default 99999 :=\n;\n')
    g.write('param ModelPeriodExogenousEmission default 0 :=\n;\n')
    g.write('param OperationalLifeStorage default 1 :=\n;\n')
    g.write('param REMinProductionTarget default 0 :=\n;\n')
    g.write('param RETagFuel default 0 :=\n;\n')
    g.write('param RETagTechnology default 0 :=\n;\n')
    g.write('param ReserveMargin default 0 :=\n;\n')
    g.write('param ReserveMarginTagFuel default 0 :=\n;\n')
    g.write('param ReserveMarginTagTechnology default 0 :=\n;\n')
    g.write('param ResidualStorageCapacity default 0 :=\n;\n')
    g.write('param StorageLevelStart default 0 :=\n;\n')
    g.write('param StorageMaxChargeRate default 0 :=\n;\n')
    g.write('param StorageMaxDischargeRate default 0 :=\n;\n')
    g.write('param TechnologyFromStorage default 0 :=\n;\n')
    g.write('param TechnologyToStorage default 0 :=\n;\n')
    g.write('param TotalAnnualMaxCapacityInvestment default 99999 :=\n;\n')
    g.write('param TotalAnnualMinCapacity default 0 :=\n;\n')
    # g.write('param TotalTechnologyAnnualActivityUpperLimit default 99999 :=\n;\n')
    g.write('param TotalTechnologyModelPeriodActivityLowerLimit default 0 :=\n;\n')
    g.write('param TotalTechnologyModelPeriodActivityUpperLimit default 99999 :=\n;\n')
    g.write('param TradeRoute default 0 :=\n;\n')
    #
    g.write('#\n' + 'end;\n')
    #
    g.close()
    #
    ###########################################################################################################################
    # Furthermore, we must print the inputs separately for fast deployment of the input matrix:
    #
    basic_header_elements = [ 'Future.ID', 'Strategy.ID', 'Strategy', 'Fuel', 'Technology', 'Emission', 'Season', 'Year' ]
    #
    parameters_to_print = [ 'SpecifiedAnnualDemand',
                            'CapacityFactor',
                            'OperationalLife',
                            'ResidualCapacity',
                            'InputActivityRatio',
                            'OutputActivityRatio',
                            'EmissionActivityRatio',
                            'CapitalCost',
                            'VariableCost',
                            'FixedCost',
                            'TotalAnnualMaxCapacity',
                            'TotalAnnualMinCapacity',
                            'TotalAnnualMaxCapacityInvestment',
                            'TotalAnnualMinCapacityInvestment',
                            'TotalTechnologyAnnualActivityUpperLimit',
                            'TotalTechnologyAnnualActivityLowerLimit',
                            'EmissionsPenalty',
                            'SpecifiedDemandProfile',
                            'YearSplit']
    #
    more_params = [   'DistanceDriven',
                    'UnitCapitalCost (USD)',
                    'UnitFixedCost (USD)',
                    'BiofuelShares']
    #
    filter_params = [   'FilterFuelType',
                    'FilterVehicleType']
    #
    input_params_table_headers = basic_header_elements + parameters_to_print + more_params + filter_params
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
            #---------------------------------------------------------------------------------#
            for aide in range( len(more_params)+len(filter_params) ):
                single_data_row.append( '' )
                single_data_row_partial.append( '' )
            #---------------------------------------------------------------------------------#
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
            ##################################################################################################################
            #
            ##################################################################################################################
            #
            if parameters_to_print[p] in [ 'TotalAnnualMaxCapacity', 'CapitalCost', 'FixedCost' ]:
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( synthesized_all_data_row[ ref_index ] ) # this must be updated in a further position of the list
                #
                this_tech = this_data_row[4]
                if this_tech in list( Fleet_Groups_inv.keys() ):
                    group_tech = Fleet_Groups_inv[ this_tech ]
                    #
                    this_year = this_data_row[7]
                    this_year_index = time_range_vector.index( int( this_year ) )
                    #
                    ref_var_position_index = input_params_table_headers.index( parameters_to_print[p] )
                    #
                    if 'Telef' not in group_tech and 'Train' not in group_tech:
                        driven_distance = Reference_driven_distance[ scenario_list[scen] ][int(fut)][ group_tech ][ this_year_index ]
                        #
                        if parameters_to_print[p] == 'TotalAnnualMaxCapacity' or parameters_to_print[p] == 'FixedCost': # this will overwrite for zero-carbon techs, but will not fail.
                            var_position_index = input_params_table_headers.index( 'DistanceDriven' )
                            this_data_row[ var_position_index ] = round(driven_distance, 4)
                        #
                        if parameters_to_print[p] == 'CapitalCost':
                            var_position_index = input_params_table_headers.index( 'UnitCapitalCost (USD)' )
                            this_data_row[ var_position_index ] = round( (10**6)*float( this_data_row[ ref_var_position_index ] )*driven_distance/(10**9), 4)
                        #
                        if parameters_to_print[p] == 'FixedCost':
                            var_position_index = input_params_table_headers.index( 'UnitFixedCost (USD)' )
                            this_data_row[ var_position_index ] = round( (10**6)*float( this_data_row[ ref_var_position_index ] )*driven_distance/(10**9), 4)
                        #
                        synthesized_all_data_row[ ref_index ] = deepcopy( this_data_row )
                        #
                    #
                    ###################################################################################################
                    #
                #
                if parameters_to_print[p] == 'FixedCost':
                    # Creating convinience filters for the analysis of model outputs:
                    if 'TR' in this_tech:
                        #
                        ref_index = combination_list.index( this_combination )
                        this_data_row = deepcopy( synthesized_all_data_row[ ref_index ] ) # this must be updated in a further position of the list
                        #
                        var_position_index = input_params_table_headers.index( 'FilterFuelType' )
                        ############################################
                        # By Fuel Type
                        for r in range( len( df_fuel_2_code_fuel_list ) ):
                            if df_fuel_2_code_fuel_list[r] in this_tech:
                                this_data_row[ var_position_index ] = df_fuel_2_code_plain_english[ r ]
                                break
                        ############################################
                        var_position_index = input_params_table_headers.index( 'FilterVehicleType' )
                        # By vehicle type
                        for r in range( len( df_tech_2_code_fuel_list ) ):
                            if df_tech_2_code_fuel_list[r] in this_tech:
                                this_data_row[ var_position_index ] = df_tech_2_code_plain_english[ r ]
                                break
                        #
                        synthesized_all_data_row[ ref_index ] = deepcopy( this_data_row )
                        #
                    #
                #
            #
        #
    #
    ###########################################################################################################################
    #
    file_aboslute_address = os.path.abspath("experiment_manager.py")
    file_adress = re.escape( file_aboslute_address.replace( 'experiment_manager.py', '' ) ).replace( '\:', ':' )
    with open( file_adress + '\\Experimental_Platform\\Futures\\' + str( scenario_list[scen] ) + '\\' + str( scenario_list[scen] ) + '_' + str( fut ) + '\\' + str( scenario_list[scen] ) + '_' + str( fut ) + '_Input.csv', 'w', newline = '') as param_csv:
        csvwriter = csv.writer(param_csv, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        # Print the header:
        csvwriter.writerow( input_params_table_headers )
        # Print all else:
        for n in range( len( synthesized_all_data_row ) ):
            csvwriter.writerow( synthesized_all_data_row[n] )
    #
    
#
'''
Function 1: Notes
a) This function interpolates the time series with the most similar  rate of change (linear to non-linear).
b) This approach only affects the final value of the time series.
c) The result depends on the initial year of uncertainty which is a global parameter and is specified in experiment setup.
'''

def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3

def interpolation_multiplier( time_list, value_list, new_relative_final_value):
    # Rememeber that the 'old_relative_final_value' is 1
    old_relative_final_value = 1
    new_value_list = []
    # We select a list that goes from the "Initial_Year_of_Uncertainty" to the Final Year of the Time Series
    initial_year_index = time_list.index( Initial_Year_of_Uncertainty )
    #
    target_2050_increment = 2050 - Initial_Year_of_Uncertainty
    total_2050_increment = new_relative_final_value-1
    delta_increment = total_2050_increment/target_2050_increment
    #
    multiplier_list = [1]*len(time_list)
    for n in range(len(time_list)):
        if n > initial_year_index and time_list[n] < 2050:
            multiplier_list[n] = delta_increment + multiplier_list[n-1]
        elif time_list[n] >= 2050:
            multiplier_list[n] = new_relative_final_value
    #
    # We now recreate the new_value_list considering the fraction before and after the Initial_Year_of_Uncertainty
    fraction_list_counter = 0
    for n in range( len( time_list ) ):
        new_value_list.append(float(value_list[n])*multiplier_list[n])
    #
    # We return the list:
    return new_value_list

def interpolation_non_linear_final2(time_list, value_list, new_relative_final_value, finyear, Initial_Year_of_Uncertainty):
    # Rememeber that the 'old_relative_final_value' is 1
    old_relative_final_value = 1
    new_value_list = []
    # We select a list that goes from the "Initial_Year_of_Uncertainty" to the Final Year of the Time Series
    initial_year_index = time_list.index( Initial_Year_of_Uncertainty )
    fraction_time_list = time_list[initial_year_index:]
    fraction_value_list = value_list[initial_year_index:]

    # Subtract the time between the last year and the "finyear":
    diff_yrs = time_list[-1] - finyear

    # We now perform the 'non-linear OR linear adjustment':
    xdata = [ fraction_time_list[i] - fraction_time_list[0] for i in range(len(fraction_time_list) - diff_yrs)]
    ydata = [ float( fraction_value_list[i] ) for i in range(len(fraction_value_list) - diff_yrs)]
    ydata_whole = [ float( fraction_value_list[i] ) for i in range(len(fraction_value_list))]
    delta_ydata = [ ydata_whole[i]-ydata_whole[i-1] for i in range( 1,len( ydata_whole ) ) ]
    #
    m_original = ( ydata[-1]-ydata[0] ) / ( xdata[-1]-xdata[0] )
    #
    m_new = ( ydata[-1]*(new_relative_final_value/old_relative_final_value) - ydata[0] ) / ( xdata[-1]-xdata[0] )
    #
    if int(m_original) == 0:
        delta_ydata_new = [m_new for i in range( 0,len( ydata_whole ) ) ]
    else:
        delta_ydata_new = [ (m_new/m_original)*(ydata_whole[i]-ydata_whole[i-1]) for i in range( 1 ,len( ydata_whole ) ) ]
        delta_ydata_new = [0] + delta_ydata_new
    #
    ydata_new = [0 for i in range(len(ydata_whole))]
    # ydata_new[0] = ydata_whole[0]
    list_apply_delta_ydata_new = []

    for i in range( 0, len( delta_ydata )+1 ):
        if time_list[i+initial_year_index] <= finyear:
            apply_delta_ydata_new = delta_ydata_new[i]
            # print(i, m_original)
        else:
            apply_delta_ydata_new = sum(delta_ydata_new)/len(delta_ydata_new)
        list_apply_delta_ydata_new.append(apply_delta_ydata_new)
        
        if i == 0:
            ydata_new[i] = ydata_whole[0] + apply_delta_ydata_new          
        else:
            ydata_new[i] = ydata_new[i-1] + apply_delta_ydata_new
    #
    # We now recreate the new_value_list considering the fraction before and after the Initial_Year_of_Uncertainty
    fraction_list_counter = 0
    for n in range( len( time_list ) ):
        if time_list[n] >= Initial_Year_of_Uncertainty:
            new_value_list.append( ydata_new[ fraction_list_counter ] )
            # print(time_list[n], ydata_new[ fraction_list_counter ], value_list[n], fraction_list_counter)
            fraction_list_counter += 1
        else:
            new_value_list.append( float( value_list[n] ) )
            # print(time_list[n], float( value_list[n] ))
    #
    # print('\n\n')
    # We return the list:
    return new_value_list

def interpolation_non_linear_final( time_list, value_list, new_relative_final_value ):
    # Rememeber that the 'old_relative_final_value' is 1
    old_relative_final_value = 1
    new_value_list = []
    # We select a list that goes from the "Initial_Year_of_Uncertainty" to the Final Year of the Time Series
    initial_year_index = time_list.index( Initial_Year_of_Uncertainty )
    fraction_time_list = time_list[initial_year_index:]
    fraction_value_list = value_list[initial_year_index:]
    # We now perform the 'non-linear OR linear adjustment':
    xdata = [ fraction_time_list[i] - fraction_time_list[0] for i in range( len( fraction_time_list ) ) ]
    ydata = [ float( fraction_value_list[i] ) for i in range( len( fraction_value_list ) ) ]
    delta_ydata = [ ydata[i]-ydata[i-1] for i in range( 1,len( ydata ) ) ]
    #
    m_original = ( ydata[-1]-ydata[0] ) / ( xdata[-1]-xdata[0] )
    #
    m_new = ( ydata[-1]*(new_relative_final_value/old_relative_final_value) - ydata[0] ) / ( xdata[-1]-xdata[0] )
    #
    if int(m_original) == 0:
        delta_ydata_new = [m_new for i in range( 1,len( ydata ) ) ]
    else:
        delta_ydata_new = [ (m_new/m_original)*(ydata[i]-ydata[i-1]) for i in range( 1,len( ydata ) ) ]
    #
    ydata_new = [ 0 for i in range( len( ydata ) ) ]
    ydata_new[0] = ydata[0]
    for i in range( 0, len( delta_ydata ) ):
        ydata_new[i+1] = ydata_new[i] + delta_ydata_new[i]
    #
    # We now recreate the new_value_list considering the fraction before and after the Initial_Year_of_Uncertainty
    fraction_list_counter = 0
    for n in range( len( time_list ) ):
        if time_list[n] >= Initial_Year_of_Uncertainty:
            new_value_list.append( ydata_new[ fraction_list_counter ] )
            fraction_list_counter += 1
        else:
            new_value_list.append( float( value_list[n] ) )
    #
    # We return the list:
    return new_value_list

'''
Function 2: Notes
a) This function changes the initial value of the time series.
'''
def interpolation_non_linear_initial( time_list, value_list, new_relative_initial_value ):
    # Rememeber that the 'old_relative_final_value' is 1
    old_relative_final_value = 1
    new_value_list = []
    # We do the interpolation across all years
    xdata = [ time_list[i] - time_list[0] for i in range( len( time_list ) ) ]
    ydata = value_list
    delta_ydata = [ ydata[i]-ydata[i-1] for i in range( 1,len( ydata ) ) ]
    #
    m_original = ( ydata[-1]-ydata[0] ) / ( xdata[-1]-xdata[0] )
    m_new = ( ydata[-1] - ydata[0]*(new_relative_initial_value/old_relative_final_value) ) / ( xdata[-1]-xdata[0] )
    #
    if float(m_original) == 0.0:
        delta_ydata_new = [m_new for i in range( 1,len( ydata ) ) ]
    else:
        delta_ydata_new = [ (m_new/m_original)*(ydata[i]-ydata[i-1]) for i in range( 1,len( ydata ) ) ]
    #
    ydata_new = [ 0 for i in range( len( ydata ) ) ]
    ydata_new[0] = ydata[0]*new_relative_initial_value
    for i in range( 0, len( delta_ydata ) ):
        ydata_new[i+1] = ydata_new[i] + delta_ydata_new[i]
    # we assign the returnable
    new_value_list = ydata_new
    #
    # We return the list:
    return new_value_list

'''
Function 3: Notes
a) There is a shift of the time series for some uncertainties, reflecting uncertainty in the initial value. For this reason, we provide al alternative function to adjust the curve.
b) There is a dc shift that changes all values in a percent. This is useful for discrete investments, where there are zeros along the time series.
'''
def time_series_shift( time_list, value_list, new_relative_initial_value ):
    new_value_list = []
    # We multiply the initial value of value_list times the new_relative_value
    new_initial_value = value_list[0]*new_relative_initial_value
    shift_value = new_initial_value - value_list[0]
    #
    for n in range(len( time_list ) ):
        new_value_list.append( value_list[n] + shift_value )
    #
    # We return the list:
    return new_value_list
#
def dc_shift( time_list, value_list, new_relative_initial_value ):
    new_value_list = []
    #
    for t in range( len( time_list ) ):
        if float( value_list[t] ) == 0.0:
            new_value_list.append( 0.0 )
        else:
            new_value_list.append( round( value_list[t]*new_relative_initial_value , 4 ) )
        #
    #
    return new_value_list
    #
#
'''
Function 4: Notes
a) For old technologies, the values must go to zero at a desired year
'''
def year_when_reaches_zero( time_list, value_list, ywrz ):
    new_value_list = []
    # We interpolate the value list defining when the value reaches 0. The values go from 100% in the base year to 0% in year_when_reaches_zero
    # We will create an interpoaltion function for the percentages:
    x_coord_tofill = [] # these are indices that are NOT known - to interpolate
    xp_coord_known = [] # these are known indices - use for interpolation
    fp_coord_known = []# [100,0] # these are the values known to interpolate the whole series
    #
    original_shares = [ 100*value_list[n]/value_list[0] for n in range(len(value_list)) ]
    original_shares_add = []
    for n in range( len(original_shares) ):
        if time_list[n] <= Initial_Year_of_Uncertainty:
            fp_coord_known.append( original_shares[n] )
            original_shares_add.append( original_shares[n] )
    fp_coord_known.append( 0 )
    #
    years_with_value_different_from_zero = [ n for n in range( time_list[0],int(ywrz)+1 ) ]
    for n in range( len( years_with_value_different_from_zero ) ):
        if years_with_value_different_from_zero[n] <= Initial_Year_of_Uncertainty or years_with_value_different_from_zero[n]==ywrz:
            xp_coord_known.append( n )
        else:
            x_coord_tofill.append( n )
    #
    y_coord_filled = list( np.interp( x_coord_tofill, xp_coord_known, fp_coord_known ) )
    percentage_list = original_shares_add + y_coord_filled + [0]
    #
    for n in range( len( time_list ) ):
        if time_list[n] <= ywrz:
            new_value_list.append( (percentage_list[n]/100)*value_list[0] )
        else:
            new_value_list.append( 0.0 )
    #
    # We return the list:
    return new_value_list

'''
Function 5: Notes
a) We apply the logistic curve varying years in x
'''
def generalized_logistic_curve(x, L, Q, k, M):
  return L/( 1 + Q*math.exp( -k*( x-M ) ) )
#
def logistic_curve_controlled(L, xM, C, xo, x):
    k = np.log( L/C - 1) / ( xo-xM )
    return L/( 1 + math.exp( -k*( x-xo ) ) )
#
'''
Function 6: Notes
a) We apply the blend interpolation
'''
def interpolation_blend( start_blend_point, final_blend_point, value_list, time_range_vector ):
    #
    start_blend_year, start_blend_value = start_blend_point[0], start_blend_point[1]/100
    final_blend_year, final_blend_value = final_blend_point[0], final_blend_point[1]/100
    #
    # Now we need to interpolate:
    x_coord_tofill = [] # these are indices that are NOT known - to interpolate
    xp_coord_known = [] # these are known indices - use for interpolation
    fp_coord_known = [] # these are the values known to interpolate the whole series
    #
    for t in range( len( time_range_vector ) ):
        something_to_fill = False
        #
        if time_range_vector[t] < start_blend_year:
            fp_coord_known.append( 0.0 )
        #
        if time_range_vector[t] == start_blend_year:
            fp_coord_known.append( start_blend_value )
        #
        if ( time_range_vector[t] > start_blend_year and time_range_vector[t] < final_blend_year ):
            something_to_fill = True
        #
        if time_range_vector[t] == final_blend_year or time_range_vector[t] > final_blend_year:
            fp_coord_known.append( final_blend_value )
        #
        if something_to_fill == True:
            x_coord_tofill.append( t )
        else:
            xp_coord_known.append( t ) # means this value was stored
        #
        y_coord_filled = list( np.interp( x_coord_tofill, xp_coord_known, fp_coord_known ) )
        #
        interpolated_values = []
        for coord in range( len( time_range_vector ) ):
            if coord in xp_coord_known:
                value_index = xp_coord_known.index(coord)
                interpolated_values.append( float( fp_coord_known[value_index] ) )
            elif coord in x_coord_tofill:
                value_index = x_coord_tofill.index(coord)
                interpolated_values.append( float( y_coord_filled[value_index] ) )
        #
    #
    new_value_list = []
    for n in range( len( value_list ) ):
        new_value_list.append( value_list[n]*( 1-interpolated_values[n] ) )
    new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
    biofuel_shares = [ round(elem, 4) for elem in interpolated_values ]
    #
    return new_value_list_rounded, biofuel_shares
    #
#
if __name__ == '__main__':

    '''
    discount_book=LeerExcel('../DiscountCostsParameters.xlsx')
    discount_book_sheets=ListaHojas(discount_book)
    discount_book_sheet=LeerHoja2(discount_book,discount_book_sheets[0],0)
    header_sheet_discount=LeerHeaders(discount_book_sheet)
    discount_year=LeerCol(discount_book_sheet, header_sheet_discount[0])[0]
    discount_rate=LeerCol(discount_book_sheet, header_sheet_discount[1])[0]    
    '''
    discount_year=2025
    discount_rate=5/100
    '''
    Let us define some control inputs internally:
    '''
    # generator_or_executor = 'None'
    generator_or_executor = 'Executor' ###'Both'
    # generator_or_executor = 'Generator'
    # generator_or_executor = 'Executor'
    inputs_txt_csv = 'Both'
    # inputs_txt_csv = 'csv'
    parallel_or_linear = 'Parallel'
    # parallel_or_linear = 'Linear'
    #
    # check_assignation = True
    check_assignation = False
    #############################################################################################################################
    '''
    # 1.A) We extract the strucute setup of the model based on 'Structure.xlsx'
    '''
    structure_filename = "./0_From_Confection/B1_Model_Structure.xlsx"
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
    for col in range(1,11+1):
        S_DICT_sets_structure['set'].append( sheet_sets_structure.iat[0, col] )
        S_DICT_sets_structure['initial'].append( sheet_sets_structure.iat[1, col] )
        S_DICT_sets_structure['number_of_elements'].append( int( sheet_sets_structure.iat[2, col] ) )
        #
        element_number = int( sheet_sets_structure.iat[2, col] )
        this_elements_list = []
        if element_number > 0:
            for n in range( 1, element_number+1 ):
                this_elements_list.append( sheet_sets_structure.iat[2+n, col] )
        S_DICT_sets_structure['elements_list'].append( this_elements_list )
    #
    S_DICT_params_structure = {'category':[],'parameter':[],'number_of_elements':[],'index_list':[]}
    param_category_list = []
    for col in range(1,30+1):
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
    for col in range(1,43+1):
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
    '''
    Structural dictionary 1: Notes
    a) We use this dictionary relating a specific technology and a group technology and associate the prefix list
    '''

    Fleet_Groups = pickle.load( open( './0_From_Confection/A-O_Fleet_Groups.pickle', "rb" ))
    Fleet_Techs_Distance = pickle.load( open( './0_From_Confection/A-O_Fleet_Groups_Distance.pickle', "rb" ))
    Fleet_Techs_OR = pickle.load( open( './0_From_Confection/A-O_Fleet_Groups_OR.pickle', "rb" ))
    Fleet_Groups_techs_2_dem = pickle.load( open( './0_From_Confection/A-O_Fleet_Groups_T2D.pickle', "rb" ))

    Fleet_Groups_inv = {}
    for k in range( len( list( Fleet_Groups.keys() ) ) ):
        this_fleet_group_key = list( Fleet_Groups.keys() )[k]
        for e in range( len( Fleet_Groups[ this_fleet_group_key ] ) ):
            this_fleet_group_tech = Fleet_Groups[ this_fleet_group_key ][ e ]
            Fleet_Groups_inv.update( { this_fleet_group_tech:this_fleet_group_key } )
    
    Fleet_Groups_list = [] # list( Fleet_Groups.keys() )
    Fleet_Groups_Distance = {}
    Fleet_Techs_with_Distance = list( Fleet_Techs_Distance.keys() )
    for u in range( len( Fleet_Techs_with_Distance ) ):
        if Fleet_Groups_inv[ Fleet_Techs_with_Distance[u] ] not in Fleet_Groups_list:
            Fleet_Groups_list.append( Fleet_Groups_inv[ Fleet_Techs_with_Distance[u] ] )
            Fleet_Groups_Distance.update( { Fleet_Groups_list[-1]:Fleet_Techs_Distance[ Fleet_Techs_with_Distance[u] ] } )
    #
    global time_range_vector # This is the variable that manages time throughout the experiment
    time_range_vector = [ int(i) for i in S_DICT_sets_structure[ 'elements_list' ][0] ]
    global index_2024
    index_2024 = time_range_vector.index( 2025 )
    #
    global final_year
    final_year = time_range_vector[-1]
    global initial_year
    initial_year = time_range_vector[0]

    # Define the techs that are transport technology groups:
    trn_list = ['Techs_Auto', 'Techs_Motos', 'Techs_Buses_Pri',
                'Techs_Buses_Pub', 'Techs_Buses_Micro', 'Techs_Telef',
                'Techs_Trains', 'Techs_Trains_Freight', 'Techs_He_Freight',
                'Techs_Li_Freight']

    # We must open useful GDP data for demand projection
    df_gdp_ref = pd.read_excel('_GDP_Ref.xlsx', 'GDP')
    list_gdp_growth_ref = df_gdp_ref['GDP_Growth'].tolist()
    list_gdp_ref = df_gdp_ref['GDP'].tolist()
    df_elasticities = pd.read_excel('_GDP_Ref.xlsx', 'Elasticities')
    df_intensities = pd.read_excel('_GDP_Ref.xlsx', 'Intensities')
    #
    #############################################################################################################################
    #
    '''
    For all effects, read all the user-defined scenarios in future 0, created by hand in Base_Runs_Generator.py ;
    These data parameters serve as the basis to implement the experiment.
    '''
    #
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
    setup_table = pd.read_excel('_Experiment_Setup.xlsx' )
    scenarios_to_reproduce = str( setup_table.loc[ 0 ,'Scenario_to_Reproduce'] )
    experiment_ID = str( setup_table.loc[ 0 ,'Experiment_ID'] )
    #
    global Initial_Year_of_Uncertainty
    Initial_Year_of_Uncertainty = int( setup_table.loc[ 0 ,'Initial_Year_of_Uncertainty'] )
    '''''
    ################################# PART 1 #################################
    '''''
    print('1: I start by reading the Uncertainty Table and systematically perturbing the paramaters.')
    uncertainty_table = pd.read_excel( 'Uncertainty_Table.xlsx' )
    # use .loc to access [row, column name]
    experiment_variables = list( uncertainty_table.columns )
    #
    np.random.seed( 555 )
    P = len( uncertainty_table.index ) # variables to vary
    N = int( setup_table.loc[ 0 ,'Number_of_Runs'] )  # number of samples
    # N = 100

    # Here we need to define the number of elements that need to be included in the hypercube
    list_xlrm_IDs = uncertainty_table['XLRM_ID']
    ignore_indices = [p for p in range(len(list_xlrm_IDs)) if list_xlrm_IDs[p] == 'none']  # these are positions where we should not ask for a lhs sample
    subtracter = 0
    col_idx = {}
    for p in range( P ):
        if p in ignore_indices:
            subtracter += 1
            col_idx.update({p:'none'})
        else:
            col_idx.update({p:p-subtracter})    

    # sys.exit()

    hypercube = lhs( P-subtracter , samples = N )
    # hypercube[p] gives vector with values of variable p across the N futures, hence len( hypercube[p] ) = N
    #
    # Routine to save hypercube
    # Create a list for the index labels you want to use
    index_labels = ['Future_' + str(i) for i in range(1, hypercube.shape[0] + 1)]
    # Filter out indices where the value is 'none'
    valid_columns = list_xlrm_IDs[list_xlrm_IDs != 'none']
    # Convert hypercube to DataFrame
    df = pd.DataFrame(hypercube, index=index_labels, columns=valid_columns)
    # Export hypercube as csv file
    df.to_csv('hypercube.csv')  # Includes index and column names in the file
    
    
    experiment_dictionary = {}
    all_dataset_address = './1_Baseline_Modelling/'

    for n in range( N ):
        this_future_X_change_direction = [] # up or down
        this_future_X_change = [] # this is relative to baseline
        this_future_X_param = [] # this is NOT relative to baseline
        #
        X_Num_unique = []
        X_Num = []
        X_Cat = []
        Exact_Param_Num = []
        #
        for p in range( P ):
            #
            # Here we extract crucial infromation for each row:
            #
            math_type = str( uncertainty_table.loc[ p ,'X_Mathematical_Type'] )
            Explored_Parameter_of_X = str( uncertainty_table.loc[ p ,'Explored_Parameter_of_X'] )
            #
            Involved_Scenarios = str( uncertainty_table.loc[ p ,'Involved_Scenarios'] ).replace(' ','').split(';')
            Involved_Sets_in_Osemosys = str( uncertainty_table.loc[ p ,'Involved_Sets_in_Osemosys'] ).replace(' ','').split(';')
            Exact_Parameters_Involved_in_Osemosys = str( uncertainty_table.loc[ p ,'Exact_Parameters_Involved_in_Osemosys'] ).replace(' ','').split(';')
            Exact_X = str( uncertainty_table.loc[ p ,'X_Plain_English_Description'] )
            #
            #######################################################################
            X_Num.append( int( uncertainty_table.loc[ p ,'X_Num'] ) )
            X_Cat.append( str( uncertainty_table.loc[ p ,'X_Category'] ) )
            Exact_Param_Num.append( int( uncertainty_table.loc[ p ,'Explored_Parameter_Number'] ) )
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
                # if n == 0:
                #     print(evaluation_value_preliminary, hyper_col_idx, p)
            else:
                evaluation_value_preliminary = 1
            #
            # evaluation_value_preliminary = hypercube[n].item(p)
            #
            evaluation_value = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc, this_loc_scale)
            #
            #######################################################################
            # here, we program the conditions of a useful adoption S-curve if parameters depend on others defined previosly:
            if ( p > 1 ) and ( str( uncertainty_table.loc[ p ,'Dependency_on_Previous_Explored_Parameter'] ) != 'n.a.' ):
                #
                independent_Param_pointer = int( uncertainty_table.loc[ p ,'Dependency_on_Previous_Explored_Parameter'] )
                #
                independent_Param_index = Exact_Param_Num.index( independent_Param_pointer )
                #
                # What parameters are constrained to have a coherent experiment?
                depending_Param = str( uncertainty_table.loc[ p ,'Explored_Parameter_of_X'] ) # actually the current parameter
                independent_Param = str( uncertainty_table.loc[ independent_Param_index ,'Explored_Parameter_of_X'] )
                ##################################################################################
                independent_Param_value = this_future_X_param[ independent_Param_index ]
                ##################################################################################
                #if 'L (' in independent_Param and evaluation_value > independent_Param_value*0.5: # means we are in C
                if 'L (' in independent_Param and evaluation_value > independent_Param_value: # means we are in C
                    this_max = independent_Param_value
                    #
                #
                elif 'M (' in independent_Param: # means we are ready to estimate all the parameters
                    # we must calculate the upper limit as a function of the other parametrs for a coherent outcome
                    r2021max = 1/0.05 # 1/this_future_X_param[ independent_Param_index-2 ]
                    r2050 = 1/0.999 # 1/this_future_X_param[ independent_Param_index-1 ]
                    #
                    M = this_future_X_param[ independent_Param_index ]
                    #
                    this_C = evaluation_value
                    this_L = this_future_X_param[ independent_Param_index-1 ]
                    #
                    log_Qmax_wo_elevate = (r2021max-1)/( (r2050-1)**( (M-2021)/(M-2050) ) )
                    Q_elevation_factor = 1 - (M-2021)/(M-2050)
                    log_Qmax = np.log(log_Qmax_wo_elevate)/Q_elevation_factor
                    Qmax = np.exp( log_Qmax )
                    Cmax = this_L/( Qmax+1 )
                    #                   
                    if this_C > Cmax:
                        this_max = Cmax
                    #
                this_loc_scale = this_max - this_min
                evaluation_value = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc, this_loc_scale)
                #
                # print( independent_Param )
                if 'M (' in independent_Param:
                    this_C = evaluation_value
                    Q = this_L/this_C - 1
                    k = np.log( (r2050-1)/Q )/(M-2050)

            #######################################################################
            # here, we program the direction dependencies:
            this_depending_on_X_list = str( uncertainty_table.loc[ p ,'Sign_Dependency_on_Specified_Xs'] ).replace(' ','').split(';')
            if ( p > 1 ) and ( str( uncertainty_table.loc[ p ,'Sign_Dependency_on_Specified_Xs'] ) != 'n.a.' ) and ( len(this_depending_on_X_list) == 1 ):
                #
                depending_on_X = int( uncertainty_table.loc[ p ,'Sign_Dependency_on_Specified_Xs'] )
                #
                depending_on_X_index = X_Num.index( depending_on_X )
                # we modify the direction by changing this_loc and this_loc_scale:
                # we apply the correction only if the original probability is incompatible
                # if str(this_future_X_change_direction[depending_on_X_index]) == 'down' and evaluation_value > 0.5*(this_max + this_min): # this approach serves for symmentrical experiments only
                if str(this_future_X_change_direction[depending_on_X_index]) == 'down' and evaluation_value > 1: # this approach serves for symmentrical or assymetrical experiments
                    this_loc_scale = 0.5*(this_max - this_min)
                # elif str(this_future_X_change_direction[depending_on_X_index]) == 'up' and evaluation_value < 0.5*(this_max + this_min): # this approach serves for symmentrical experiments only
                elif str(this_future_X_change_direction[depending_on_X_index]) == 'up' and evaluation_value < 1: # this approach serves for symmentrical or assymetrical experiments
                    this_loc = this_min + 0.5*(this_max - this_min)
                #
                evaluation_value = scipy.stats.uniform.ppf(evaluation_value_preliminary, this_loc, this_loc_scale)
            #
            #######################################################################
            #
            if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline' ] ) == 'YES':
                if evaluation_value > 1:
                    this_future_X_change_direction.append('up')
                else:
                    this_future_X_change_direction.append('down')
                #
                this_future_X_change.append( evaluation_value )
                #
                this_future_X_param.append('n.a.')
            #
            elif str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline' ] ) == 'NO':
                this_future_X_change_direction.append('n.a.')
                this_future_X_change.append( 'n.a.' )
                #
                if 'C (' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                    this_future_X_param.append( [ Q, k, M ] )
                #
                else:
                    if 'Year_when_reaches_zero' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                        this_future_X_param.append( int( evaluation_value ) )
                    #
                    elif ( 'C (' not in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ) ) or ( 'Blend_Time_Series' in str( uncertainty_table.loc[ p , 'X_Mathematical_Type' ] ) ):
                        this_future_X_param.append( evaluation_value )
                    #
                    elif str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ) == 'Constant':
                        this_future_X_param.append( evaluation_value )
                        #
                #
            #
            #######################################################################
            #
            # We can now store all the information for each future in a dictionary:
            #
            if n == 0: # the dictionary is created only when the first future appears
                if int( uncertainty_table.loc[ p ,'X_Num'] ) in X_Num_unique: # by design, this means the math_type is an Adoption_Curve or Blend_Time_Series math type
                    if 'L (' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Explored_Parameter_of_X' ].append( Explored_Parameter_of_X )
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0].append( this_future_X_param[-1] )
                    elif 'C (' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Explored_Parameter_of_X' ].append('Q')
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Explored_Parameter_of_X' ].append('k')
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Explored_Parameter_of_X' ].append('M')
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] += this_future_X_param[-1]
                    elif 'Blend_Time_Series' in str( uncertainty_table.loc[ p , 'X_Mathematical_Type' ] ):
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Explored_Parameter_of_X' ].append( Explored_Parameter_of_X )
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0].append( this_future_X_param[-1] )
                    #
                #
                ###################################################################################################################################
                #
                elif int( uncertainty_table.loc[ p ,'X_Num'] ) not in X_Num_unique:
                    #
                    X_Num_unique.append( int( uncertainty_table.loc[ p ,'X_Num'] ) )
                    #
                    Relative_to_Baseline = str( uncertainty_table.loc[ p ,'Explored_Parameter_is_Relative_to_Baseline'] )
                    #
                    experiment_dictionary.update( { X_Num_unique[-1]:{ 'Category':X_Cat[-1], 'Math_Type':math_type, 'Relative_to_Baseline':Relative_to_Baseline, 'Exact_X':Exact_X } } )
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Involved_Scenarios':Involved_Scenarios })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Involved_Sets_in_Osemosys':Involved_Sets_in_Osemosys })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Exact_Parameters_Involved_in_Osemosys':Exact_Parameters_Involved_in_Osemosys })
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Futures':[x for x in range( 1, N+1 ) ] })
                    #
                    # if math_type == 'Time_Series' or math_type == 'Discrete_Investments':
                    if math_type in ['Time_Series', 'Discrete_Investments', 'Mult_Adoption_Curve', 'Mult_Restriction', 'Mult_Restriction_Start', 'Mult_Restriction_End']:
                        experiment_dictionary[ X_Num_unique[-1] ].update({ 'Explored_Parameter_of_X':Explored_Parameter_of_X } )
                        experiment_dictionary[ X_Num_unique[-1] ].update({ 'Values':[0.0 for x in range( 1, N+1 ) ] })
                        # We fill the data for future n=1 // it is important to note that the future n=0 can have completely different parameters when values are not relative to baseline
                        if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'YES':
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0] = this_future_X_change[-1] # here n=0
                            
                            
                            # if p == 9:
                            #     print('check!!!')
                            #     sys.exit()
                            
                        elif str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'NO':
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0] = this_future_X_param[-1] # here n=0
                    #
                    elif math_type == 'Adoption_Curve':
                        if 'L (' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                            experiment_dictionary[ X_Num_unique[-1] ].update({ 'Explored_Parameter_of_X':[ Explored_Parameter_of_X ] } )
                            experiment_dictionary[ X_Num_unique[-1] ].update({ 'Values':[[] for x in range( 1, N+1 ) ] })
                            # We fill the data for future n=1 // it is important to note that the future n=0 can have completely different parameters when values are not relative to baseline
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0].append( this_future_X_param[-1] ) # here n=0
                            #
                        #
                    elif math_type == 'Blend_Time_Series':
                        if 'Initial_Year' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                            experiment_dictionary[ X_Num_unique[-1] ].update({ 'Explored_Parameter_of_X':[ Explored_Parameter_of_X ] } )
                            experiment_dictionary[ X_Num_unique[-1] ].update({ 'Values':[[] for x in range( 1, N+1 ) ] })
                            # We fill the data for future n=1 // it is important to note that the future n=0 can have completely different parameters when values are not relative to baseline
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0].append( this_future_X_param[-1] ) # here n=0
                            #
                    elif math_type == 'Constant':
                        experiment_dictionary[ X_Num_unique[-1] ].update({ 'Explored_Parameter_of_X':[ Explored_Parameter_of_X ] } )
                        experiment_dictionary[ X_Num_unique[-1] ].update({ 'Values':[[] for x in range( 1, N+1 ) ] })
                        # We fill the data for future n=1 // it is important to note that the future n=0 can have completely different parameters when values are not relative to baseline
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0] = this_future_X_param[-1] # here n=0
                        #
                    #
                #
            #
            ###################################################################################################################################
            #
            else:
                #
                if int( uncertainty_table.loc[ p ,'X_Num'] ) in X_Num_unique: # by design, this means the math_type is an Adoption_Curve or Blend_Time_Series math type
                    if 'C (' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] += this_future_X_param[-1]
                    elif 'Initial_Year' not in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ) and math_type == 'Blend_Time_Series':
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n].append( this_future_X_param[-1] )
                #
                ###################################################################################################################################
                #
                elif int( uncertainty_table.loc[ p ,'X_Num'] ) not in X_Num_unique:
                    #
                    X_Num_unique.append( int( uncertainty_table.loc[ p ,'X_Num'] ) )
                    #
                    if math_type == 'Time_Series' or math_type == 'Discrete_Investments' or math_type in ['Mult_Adoption_Curve', 'Mult_Restriction', 'Mult_Restriction_Start', 'Mult_Restriction_End']:
                        if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'YES':
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] = this_future_X_change[-1]
                        elif str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'NO':
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] = this_future_X_param[-1]
                    #
                    elif math_type == 'Adoption_Curve':
                        if 'L (' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n].append( this_future_X_param[-1] )
                    #
                    elif math_type == 'Blend_Time_Series':
                        if 'Initial_Year' in str( uncertainty_table.loc[ p , 'Explored_Parameter_of_X' ] ):
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n].append( this_future_X_param[-1] )
                    #
                    elif math_type == 'Constant':
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] = this_future_X_param[-1]

                u = int( uncertainty_table.loc[ p ,'X_Num'] )
                print(u, len(experiment_dictionary[u].keys()),
                      experiment_dictionary[u]['Category'],
                      # len([i for i in experiment_dictionary[u]['Values'] if float(i) != 0.0])
                      )

    '''''
    ################################# PART 2 #################################
    '''''
    print('2: That is done. Now I initialize some key structural data.')
    '''
    # 2.B) We finish this sub-part, and proceed to read all the base scenarios.
    '''
    header_row = ['PARAMETER','Scenario','REGION','TECHNOLOGY','FUEL','EMISSION','MODE_OF_OPERATION','TIMESLICE','YEAR','SEASON','DAYTYPE','DAILYTIMEBRACKET','STORAGE','Value']
    #
    scenario_list = []
    if scenarios_to_reproduce == 'All':
        stable_scenario_list_raw = os.listdir( '1_Baseline_Modelling' )
        for n in range( len( stable_scenario_list_raw ) ):
            if stable_scenario_list_raw[n] not in ['_Base_Dataset', '_BACKUP'] and '.txt' not in stable_scenario_list_raw[n]:
                scenario_list.append( stable_scenario_list_raw[n] )
    elif scenarios_to_reproduce == 'Experiment':
        scenario_list.append( 'BAU' )
        scenario_list.append( 'LTS' )
    elif scenarios_to_reproduce != 'All' and scenarios_to_reproduce != 'Experiment':
        scenario_list.append( scenarios_to_reproduce )
    #
    # '''
    # print('brake here to check experiment scenarios')
    # sys.exit()
    # '''
    # This section reads a reference data.csv from baseline scenarios and frames Structure-OSEMOSYS_CR.xlsx
    col_position = []
    col_corresponding_initial = []
    for n in range( len( S_DICT_sets_structure['set'] ) ):
        col_position.append( header_row.index( S_DICT_sets_structure['set'][n] ) )
        col_corresponding_initial.append( S_DICT_sets_structure['initial'][n] )
    # Define the dictionary for calibrated database:
    stable_scenarios = {}
    for scen in scenario_list:
        stable_scenarios.update( { scen:{} } )
    #
    for scen in range( len( scenario_list ) ):
        #
        this_paramter_list_dir = '1_Baseline_Modelling/' + str( scenario_list[scen] )
        parameter_list = os.listdir( this_paramter_list_dir )
        #
        for p in range( len( parameter_list ) ):
            this_param = parameter_list[p].replace('.csv','')
            stable_scenarios[ scenario_list[scen] ].update( { this_param:{} } )
            # To extract the parameter input data:
            all_params_list_index = S_DICT_params_structure['parameter'].index(this_param)
            this_number_of_elements = S_DICT_params_structure['number_of_elements'][all_params_list_index]
            this_index_list = S_DICT_params_structure['index_list'][all_params_list_index]
            #
            for k in range(this_number_of_elements):
                stable_scenarios[ scenario_list[scen] ][ this_param ].update({this_index_list[k]:[]})
            stable_scenarios[ scenario_list[scen] ][ this_param ].update({'value':[]})
            # Extract data:
            with open( this_paramter_list_dir + '/' + str(parameter_list[p]), mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                #
                for row in csv_reader:
                    if row[ header_row[-1] ] != None and row[ header_row[-1] ] != '':
                        #
                        for h in range( 2, len(header_row)-1 ):
                            if row[ header_row[h] ] != None and row[ header_row[h] ] != '':
                                set_index  = S_DICT_sets_structure['set'].index( header_row[h] )
                                set_initial = S_DICT_sets_structure['initial'][ set_index ]
                                stable_scenarios[ scenario_list[scen] ][ this_param ][ set_initial ].append( row[ header_row[h] ] )
                        stable_scenarios[ scenario_list[scen] ][ this_param ][ 'value' ].append( row[ header_row[-1] ] )
                        #
    '''
    # 2.C) We call the default parameters for later use:
    '''
    list_param_default_value = pd.read_excel( './0_From_Confection/B1_Default_Param.xlsx' )
    list_param_default_value_params = list( list_param_default_value['Parameter'] )
    list_param_default_value_value = list( list_param_default_value['Default_Value'] )

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
    
    
    transport_external_demand=pd.read_csv('SpecifiedAnnualDemandTransport.csv')
    dic_transport_demand = {}
    #print(len(transport_external_demand))
    for r in range(len(transport_external_demand)):
        llave=transport_external_demand['Strategy'][r]+';'+str(transport_external_demand['Future.ID'][r])+';'+transport_external_demand['Fuel'][r]
        if llave not in list(dic_transport_demand.keys()):
            dic_transport_demand.update({llave:{int(transport_external_demand['Year'][r]):transport_external_demand['SpecifiedAnnualDemand'][r]}})
        else:
            dic_transport_demand[llave].update({int(transport_external_demand['Year'][r]):transport_external_demand['SpecifiedAnnualDemand'][r]})
    #print(dic_transport_demand)
    llaves=list(dic_transport_demand.keys())
    for r in range(len(llaves)):
        dic_aux=dic_transport_demand[llaves[r]]
        llaves2=list(dic_aux.keys())
        values2=list(dic_aux.values())
        llaves3,values3=bubbleSort(llaves2,values2)
        dic_transport_demand[llaves[r]]=dict(zip(llaves3, values3))
    #print(dic_transport_demand)
    
    
    storage_limits=pd.read_csv('StorageLimitsV7.csv')
    dic_storage_limits = {}
    #print(len(storage_limits))
    for r in range(len(storage_limits)):
        llave=storage_limits['Strategy'][r]+';'+str(storage_limits['Future.ID'][r])+';'+storage_limits['Technology'][r]
        if llave not in list(dic_storage_limits.keys()):
            dic_storage_limits.update({llave:{int(storage_limits['Year'][r]):storage_limits['TotalCapacityAnnual'][r]}})
        else:
            dic_storage_limits[llave].update({int(storage_limits['Year'][r]):storage_limits['TotalCapacityAnnual'][r]})
    #print(dic_storage_limits)
    llaves=list(dic_storage_limits.keys())
    for r in range(len(llaves)):
        dic_aux=dic_storage_limits[llaves[r]]
        llaves2=list(dic_aux.keys())
        values2=list(dic_aux.values())
        llaves3,values3=bubbleSort(llaves2,values2)
        dic_storage_limits[llaves[r]]=dict(zip(llaves3, values3))
    #print(dic_storage_limits)
    
    
    storage_limits=pd.read_csv('CostsBateries.csv')
    dic_storage_capex = dict(zip(list(storage_limits['Year']), list(storage_limits['CapitalCost'])))
    dic_storage_fixed = dict(zip(list(storage_limits['Year']), list(storage_limits['FixedCost'])))
    # print(dic_storage_capex)
    # print(dic_storage_fixed)
    # sys.exit()


    '''
    # 3.B) We iterate over the experiment dictionary for the 1 to N futures additional to future 0, implementing the orderly manipulation
    '''
    print('3: That is done. Now I systematically perturb the model parameters.')
    # Broadly speaking, we must perfrom the same calculation across futures, as all futres are independent.
    #
    reference_driven_distance = {}
    reference_occupancy_rate = {}
    #
    # We need to store some values for some adjustments:
    spec_store_freheaele = {}
    #
    for s in range( len( scenario_list ) ):
        this_s = s
        reference_driven_distance.update( { scenario_list[s]:{} } )
        reference_occupancy_rate.update( { scenario_list[s]:{} } )
        fut_id = 0
        #

        ### WHAT HAPPENED TO DEMAND???
        if scenario_list[s] == 'BAU':
            test_dict = {}
            test_dict_1 = {}
            test_dict_2 = {}
            test_dict_3 = {}
            test_dict_4 = {}


        for f in range( 1, len( all_futures )+1 ):
        # for f in range( 1, 1+1 ):
            this_f = f
            spec_store_freheaele.update({this_f:[]})
            #
            if check_assignation:
                print('\n')
                print(scenario_list[s], this_f)
            #
            reference_driven_distance[ scenario_list[s] ].update( { f:{} } )
            reference_occupancy_rate[ scenario_list[s] ].update( { f:{} } )
            #
            # NOTE 0: TotalDemand and Mode Shift must take the BAU SpeecifiedAnnualDemand for coherence.
            TotalDemand = []
            TotalDemand_BASE_BAU = []

            for u in range( 1, len(experiment_dictionary)+1 ): # u is for the uncertainty number // start at 1 because we are not experimenting the GDP
                enter_if_cycle = False

                Exact_X = experiment_dictionary[u]['Exact_X']
                X_Cat = experiment_dictionary[u]['Category']
                # Extract crucial sets and parameters to be manipulated in the model:
                Parameters_Involved = experiment_dictionary[u]['Exact_Parameters_Involved_in_Osemosys']
                Sets_Involved = deepcopy( experiment_dictionary[u]['Involved_Sets_in_Osemosys'] )
                #
                Scenarios_Involved = experiment_dictionary[u]['Involved_Scenarios']
                # Extract crucial identifiers:
                Explored_Parameter_of_X = experiment_dictionary[u]['Explored_Parameter_of_X']
                Math_Type = experiment_dictionary[u]['Math_Type']
                Relative_to_Baseline = experiment_dictionary[u]['Relative_to_Baseline']
                # Extract the values:
                Values_per_Future =  experiment_dictionary[u]['Values']
                # For the manipulation, we deploy consecutive actions on the system depending on every X parameter:
                # NOTE 1: we will perform the changes in the consecutive order of the Uncertainty_Table, using distance as a final adjustment.
                # NOTE 2: the distance reduction of DP is relative to BAU. All other uncertainties are independent of the scenario.
                # NOTE 3: we go ahead with the manipulation of the uncertainty if it is applicable to the scenario we are interested in reproducing.
                # NOTE 4: we store the TotalDemand vector to be used in the uncertainties that require it.

                if str( scenario_list[s] ) in Scenarios_Involved:
                    # We iterate over the involved parameters of the model here:
                    for p in range( len( Parameters_Involved ) ):
                        this_parameter = Parameters_Involved[p]
                        #
                        enter_if_cycle = False
                        #
                        if 'Passenger Demand' in X_Cat:
                            #
                            enter_if_cycle = True
                            #
                            if scenario_list[s] == 'BAU':
                                distribution_passenger_BAU = {}
                            # This uncertainty must be dealt with by adding the specified annual demand of the involved sets. Then, the final value is changed with the experimetn value. Finally, the time series (math type) is interpolated.
                            tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('FUEL') ]
                            summed_value_list = []
                            for a_set in range( len( Sets_Involved ) ):
                                this_set = Sets_Involved[a_set]
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                # for each index we extract the time and value in a list:
                                # extracting time:
                                time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                # extracting value:
                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                value_list = [ float(value_list[j]) for j in range( len( value_list ) ) ]
                                # performing addition of sets in the case of x = 1:
                                for element in range( len( value_list ) ):
                                    if a_set == 0:
                                        summed_value_list.append( float( value_list[element] ) )
                                    else:
                                        summed_value_list[element] += float ( value_list[element] )
                                #
                                if scenario_list[s] == 'BAU':
                                    distribution_passenger_BAU.update( { this_set:[] } )
                                    distribution_passenger_BAU[ this_set ] = deepcopy( value_list )
                                #
                            # Here we take advantage of the loop to obtain the baseline shares to apply to the BAU scenario:
                            if scenario_list[s] == 'BAU':
                                TotalDemand_BASE_BAU = deepcopy( summed_value_list )
                                for a_set_BASE in range( len( Sets_Involved ) ):
                                    this_set_distribution = [ distribution_passenger_BAU[ Sets_Involved[a_set_BASE] ][n] / TotalDemand_BASE_BAU[n] for n in range( len( TotalDemand_BASE_BAU ) ) ]
                                    distribution_passenger_BAU[ Sets_Involved[a_set_BASE] ] = deepcopy( this_set_distribution )

                            if 'EXPLICIT' in Exact_X:
                                new_value_list = [0]*len(time_list)
                                for a_set in range( len( Sets_Involved ) ):
                                    this_set = Sets_Involved[a_set]
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                    # for each index we extract the time and value in a list:
                                    # extracting time:
                                    time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                    # extracting value:
                                    value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    value_list = [ float(value_list[j]) for j in range( len( value_list ) ) ]

                                    new_value_list_set = \
                                        interpolation_multiplier(
                                            time_list, value_list,
                                            Values_per_Future[fut_id] )

                                    new_value_list = list(map(
                                        operator.add, new_value_list,
                                        new_value_list_set))

                            else:
                                # now that the value is extracted, we must manipulate the result and store in TotalDemand
                                local_df_elasticities = deepcopy(df_elasticities)
                                local_df_elasticities.iloc[-1, local_df_elasticities.columns.get_loc('e_Passenger')] = float(Values_per_Future[fut_id])
                                local_df_elasticities['e_Passenger'].interpolate(method ='linear', limit_direction ='forward', inplace = True)
                                list_e_pass = local_df_elasticities['e_Passenger'].tolist()

                                new_value_list = []
                                for y in range(len(time_range_vector)):
                                    if y < index_2024:
                                        new_value_list.append(summed_value_list[y])
                                    else:  # apply growth formula with demand elasticity
                                        gdp_growth_apply = experiment_dictionary[1]['Values'][fut_id]  # the first element in the uncertainty table
                                        last_value = new_value_list[-1]
                                        new_value_list.append(last_value*(1 + list_e_pass[y-1]*gdp_growth_apply/100))

                            # store the results now:
                            new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                            TotalDemand = deepcopy( new_value_list_rounded )
                            #
                            if scenario_list[s] == 'BAU':  # NDP needs mode shift
                                for a_set in range( len( Sets_Involved ) ):
                                    this_set = Sets_Involved[a_set]
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                    updated_value_list = []
                                    #
                                    for n in range( len(TotalDemand) ):
                                        updated_value_list.append( TotalDemand[n]*distribution_passenger_BAU[ this_set ][n] )
                                    updated_value_list_rounded = [ round(elem, 4) for elem in updated_value_list ]
                                    #
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy( updated_value_list_rounded )

                            # print('check if this happened')
                            # sys.exit()

                        
                        #
                        elif X_Cat in ['Refrigerantes','Cal','Lubricantes']:
                            for a_set in range( len( Sets_Involved ) ):
                                this_set_type_initial = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                #
                                this_set = Sets_Involved[a_set]
                                
                                dic_match = {'IMP_R32':'E5IPPUR32','LIME':'E5IPPULIME','LUBRI':'E5IPPULUBRI'}
                                this_parameter_aux = 'SpecifiedAnnualDemand'
                                this_set_type_initial_aux = 'f'
                                this_set_aux = dic_match[this_set]
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ this_set_type_initial ] ) if x == str( this_set ) ]
                                this_set_range_indices2 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter_aux ][ this_set_type_initial_aux ] ) if x == str( this_set_aux ) ]
                                this_set_range_indices3 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ][ this_set_type_initial ] ) if x == str( this_set ) ]
                                #
                                time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                # extracting value:
                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                
                                #--------------------------------------------------------------------#
                                # now that the value is extracted, we must manipulate the result and assign back
                                if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios                                           
                                    new_value_list = deepcopy(
                                        interpolation_non_linear_final2(
                                        time_list, value_list,
                                        float(Values_per_Future[fut_id]),
                                        2050,Initial_Year_of_Uncertainty))
                                        #
                                    #
                                #
                                new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                #print(new_value_list_rounded)
                                #--------------------------------------------------------------------#``
                                # Assign parameters back: for these subset of uncertainties
                                inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['value'][ this_set_range_indices3[0]:this_set_range_indices3[-1]+1 ] = deepcopy(new_value_list_rounded)
                                inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter_aux ]['value'][ this_set_range_indices2[0]:this_set_range_indices2[-1]+1 ] = deepcopy(new_value_list_rounded)

                        elif X_Cat in ['Cost of infrastructure, materials and energy']:
                            for a_set in range( len( Sets_Involved ) ):
                                this_set_type_initial = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                #
                                this_set = Sets_Involved[a_set]
                                
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ this_set_type_initial ] ) if x == str( this_set ) ]
                                #
                                if len(this_set_range_indices) != 0:
                                    time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                    # extracting value:
                                    value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                    
                                    #--------------------------------------------------------------------#
                                    # now that the value is extracted, we must manipulate the result and assign back
                                    if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios                                           
                                        new_value_list = deepcopy(
                                            interpolation_non_linear_final2(
                                            time_list, value_list,
                                            float(Values_per_Future[fut_id]),
                                            2050,Initial_Year_of_Uncertainty))
                                            #
                                        #
                                    #
                                    new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                    #--------------------------------------------------------------------#``
                                    # Assign parameters back: for these subset of uncertainties
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                        #
                        elif X_Cat in ['Cemento']:
                            for a_set in range( len( Sets_Involved ) ):
                                this_set_type_initial = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('FUEL') ]
                                #
                                this_set = Sets_Involved[a_set]
                                
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ this_set_type_initial ] ) if x == str( this_set ) ]
                                # for each index we extract the time and value in a list:
                                # extracting time:
                                time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                # extracting value:
                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )                                                                                                                                                                
                                value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #--------------------------------------------------------------------#
                                # now that the value is extracted, we must manipulate the result and assign back
                                if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios                                           
                                    new_value_list = deepcopy(
                                        interpolation_non_linear_final2(
                                        time_list, value_list,
                                        float(Values_per_Future[fut_id]),
                                        2050,Initial_Year_of_Uncertainty))
                                        #
                                    #                                             
                                #
                                new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                #--------------------------------------------------------------------#``
                                # Assign parameters back: for these subset of uncertainties
                                inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                ### AQUI DEBO METER LA RESTRICCION
                                this_set_range_indices2 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ][ 't' ] ) if x == 'PROD_CEM' ]
                                inherited_scenarios[ scenario_list[s] ][ f ]['TotalTechnologyAnnualActivityUpperLimit']['value'][ this_set_range_indices2[0]:this_set_range_indices2[-1]+1 ] = deepcopy(new_value_list_rounded)
                                
                                # Produccion de cemento
                                this_set_range_indices3 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ][ 't' ] ) if x == 'PROD_CEM' ]
                                prod_cem=inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_set_range_indices3[0]:this_set_range_indices3[-1]+1]
                                #print(prod_cem)
                                # Clinker importado y almacenado
                                this_set_range_indices4 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ][ 't' ] ) if x == 'IMP_STOR' ]
                                imp_stor=inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_set_range_indices4[0]:this_set_range_indices4[-1]+1]
                                #print(imp_stor)
                                # Produccion nacional de Clinker
                                this_set_range_indices5 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ][ 't' ] ) if x == 'PROD_CLK_TRAD' ]
                                prod_clk=inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_set_range_indices5[0]:this_set_range_indices5[-1]+1]
                                #print(prod_clk)
                                # Fctor de Clinker
                                this_set_range_indices6 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'InputActivityRatio' ][ 'f' ] ) if x == 'CLK_PROD' ]
                                this_set_range_indices7 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'InputActivityRatio' ][ 't' ] ) if x == 'PROD_CEM' ]
                                this_set_range_indices8 = list(set(this_set_range_indices6) & set(this_set_range_indices7))
                                this_set_range_indices8.sort()
                                fc=inherited_scenarios[scenario_list[s]][f]['InputActivityRatio']['value'][this_set_range_indices8[0]:this_set_range_indices8[-1]+1]
                                #print(prod_cem)
                                #print(fc)
                                #print(imp_stor)
                                new_prod_nac_clk= [a * float(b) for a, b in zip(prod_cem, fc)] # prod_cem*FC
                                new_upper_prod_clk_trad= [a - float(b) for a, b in zip(new_prod_nac_clk, imp_stor)] # prod_nac_clk-imp_stor
                                #print(new_upper_prod_clk_trad)
                                inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_set_range_indices5[0]:this_set_range_indices5[-1]+1] = deepcopy(new_upper_prod_clk_trad) 

                        #
                        elif X_Cat in [ 'Electrical Demand', 'Fuel Demand', 'Freight Demand' ]:   
                            #
                            enter_if_cycle = True
                            #
                            # Store the total electrical demand:
                            if X_Cat in ['Electrical Demand']:
                                total_elec_demand = [0]*len(time_range_vector)
                                total_elec_demand_bc = [0]*len(time_range_vector)

                            # Extract the total demands before any adjustment:
                            value_list_total = [0 for j in range(len(time_range_vector))]
                            for a_set_aux in range( len( Sets_Involved ) ):
                                tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('FUEL') ]
                                #
                                this_set_aux = Sets_Involved[a_set_aux]
                                this_set_range_indices_aux = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set_aux ) ]
                                value_list_aux = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices_aux[0]:this_set_range_indices_aux[-1]+1 ] )
                                for j in range( len( value_list_aux ) ):
                                    value_list_total[j] += deepcopy( float( value_list_aux[j] ) )
                            #
                            for a_set in range( len( Sets_Involved ) ):
                                tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('FUEL') ]
                                #
                                this_set = Sets_Involved[a_set]
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                #
                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]

                                if 'EXPLICIT' in Exact_X:
                                    new_value_list = \
                                        interpolation_multiplier(
                                            time_range_vector, value_list,
                                            Values_per_Future[fut_id] )

                                    if X_Cat in ['Electrical Demand']:
                                        total_elec_demand = list(map(
                                            operator.add, total_elec_demand,
                                            new_value_list))
                                        total_elec_demand_bc = list(map(
                                            operator.add, total_elec_demand_bc,
                                            value_list))
                                        
                                        # print(this_set, Values_per_Future[fut_id], new_value_list[-1]/value_list[-1])
                                        
                                        # if value_list[-1] != 0:
                                        #    print('review the interpolations')
                                        #    sys.exit()

                                else:
                                    if X_Cat in 'Freight Demand':
                                        # now that the value is extracted, we must manipulate the result and store in TotalDemand
                                        local_df_elasticities = deepcopy(df_elasticities)
                                        local_df_elasticities.iloc[-1, local_df_elasticities.columns.get_loc('e_Freight')] = float(Values_per_Future[fut_id])
                                        local_df_elasticities['e_Freight'].interpolate(method ='linear', limit_direction ='forward', inplace = True)
                                        list_e_fre = local_df_elasticities['e_Freight'].tolist()
    
                                        new_value_list = []
                                        for y in range(len(time_range_vector)):
                                            if y < index_2024:
                                                new_value_list.append(value_list[y])
                                            else:  # apply growth formula with demand elasticity
                                                gdp_growth_apply = experiment_dictionary[1]['Values'][fut_id]  # the first element in the uncertainty table
                                                last_value = new_value_list[-1]
                                                new_value_list.append(last_value*(1 + list_e_fre[y-1]*gdp_growth_apply/100))
    
                                    else:  # non-transport demands
                                        value_list_ratio = [value_list[j]/value_list_total[j] for j in range( len( value_list ) )]
                                        if X_Cat in 'Electrical Demand':
                                            df_intensity_col = 'i_NT_elec'
                                        elif X_Cat in 'Fuel Demand':
                                            df_intensity_col = 'i_NT_fossil'
                                        # We must now find the elements
                                        if a_set == 0:
                                            local_df_intensities = deepcopy(df_intensities)
                                            last_value_use = local_df_intensities[df_intensity_col].tolist()[-1]
                                            local_df_intensities.iloc[-1, local_df_intensities.columns.get_loc(df_intensity_col)] = float(Values_per_Future[fut_id])*last_value_use
                                            local_df_intensities[df_intensity_col].interpolate(method ='linear', limit_direction ='forward', inplace = True)
                                            list_i = local_df_intensities[df_intensity_col].tolist()

                                        new_value_list = []
                                        for y in range(len(time_range_vector)):
                                            if y < index_2024:
                                                new_value_list.append(value_list_ratio[y]*list_gdp_ref[y]*list_i[y]/1e6)
                                                last_gdp = deepcopy(list_gdp_ref[y])
                                            else:  # apply growth formula with demand elasticity
                                                gdp_growth_apply = experiment_dictionary[1]['Values'][fut_id]  # the first element in the uncertainty table
                                                new_gdp = last_gdp*(1+gdp_growth_apply/100)
                                                new_value_list.append(value_list_ratio[y]*new_gdp*list_i[y]/1e6)
                                                last_gdp = deepcopy(new_gdp)

                                # Assign parameters back: for these subset of uncertainties
                                new_value_list_rounded = [
                                    round(elem, 4) for elem in new_value_list]
                                
                                '''
                                if 'EXPLICIT' in Exact_X and X_Cat in ['Electrical Demand'] and sum(value_list) > 0:
                                    print([round(elem, 4) for elem in value_list[:15]])
                                    print(new_value_list_rounded[:15])
                                    xxx = [new_value_list[i]/anelem for i, anelem in enumerate(value_list)]
                                    print([round(elem, 4) for elem in xxx[:15]])
                                    print('\n')
                                
                                    if a_set == len(Sets_Involved)-1:
                                        print('stop and check weird stuff')
                                        sys.exit()
                                '''
                                
                                inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list_rounded)

                        # elif 'Mult_Restriction' in Math_Type:
                        #     #
                        #     enter_if_cycle = True
                        #     #
                        #     '''
                        #     The script below should work if the sets sum 100% of the generation in the base cases,
                        #     i.e., the sum of "value_list_sh" across all sets should be 100% every year.
                        #     '''

                        #     if 'Start' in Math_Type:
                        #         # Define a total denominator for normalization:
                        #         new_value_list_sh_sum = [0]*len(time_range_vector)
                        #         value_list_sh_sum = [0]*len(time_range_vector)

                        #         tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                        #         store_new_sh = {}
                        #         store_refval_sh = {}

                        #         all_set_involved = []

                        #     # Iterate across every single set
                        #     for a_set in range( len( Sets_Involved ) ):
                        #         # Get each share of Upper and Lower limit in the base case
                        #         this_set = Sets_Involved[a_set]
                        #         all_set_involved.append(this_set)
                        #         this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(this_set)]

                        #         value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]

                        #         # Get the share:
                        #         value_list_sh = [value_list[i]/total_val for i, total_val in enumerate(total_elec_demand_bc)]

                        #         store_refval_sh.update({
                        #             this_set:deepcopy(value_list_sh)})

                        #         if scenario_list[s] != 'BAU':
                        #             new_value_list_sh = \
                        #                 interpolation_multiplier(
                        #                     time_list, value_list_sh,
                        #                     Values_per_Future[fut_id])
                        #         else:
                        #             new_value_list_sh = deepcopy(
                        #                 value_list_sh)

                        #         store_new_sh.update({
                        #             this_set:deepcopy(new_value_list_sh)})

                        #         new_value_list_sh_sum = list(map(
                        #             operator.add, new_value_list_sh_sum,
                        #             new_value_list_sh))

                        #         value_list_sh_sum = list(map(
                        #             operator.add, value_list_sh_sum,
                        #             value_list_sh))

                        #         #if this_set == 'PP_HYDAMARORLAR':
                        #         #    print('check')
                        #         #    sys.exit()                           

                        #     if 'End' in Math_Type:
                                                               
                        #         #for i in range(len(time_range_vector)):
                        #         #    if time_range_vector[i] <= 2024:
                        #         #        new_value_list_sh_sum[i] = 1
                                
                        #         # Iterate again to apply normalization:
                        #         for a_set in range( len( all_set_involved ) ):
                        #             this_set = all_set_involved[a_set]
                        #             this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(this_set)]

                        #             value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]

                        #             # Get the share:
                        #             value_list_sh = [value_list[i]/total_val for i, total_val in enumerate(total_elec_demand_bc)]

                        #             # Normalize the share:
                        #             new_value_list_sh_norm = [store_new_sh[this_set][i]*value_list_sh_sum[i]/sh_sum for i, sh_sum in enumerate(new_value_list_sh_sum)]

                        #             # Calculate the magnitude according to adjusted demand:
                        #             new_value_list = [new_value_list_sh_norm[i]*total_val for i, total_val in enumerate(total_elec_demand)]

                        #             # Add a filter for wind generation:
                        #             if this_set == 'PP_WND_US':
                        #                 max_prod_in_gwh = 0.88 * 0.5214 * 0.95 * 8760
                        #                 sec_val = 0.98
                        #                 max_prod_in_pj = max_prod_in_gwh * 0.0036 * sec_val
                        #                 for i in range(len(new_value_list)):
                        #                     if new_value_list[i] > max_prod_in_pj:
                        #                         new_value_list[i] = max_prod_in_pj

                        #                 #if scenario_list[s] == 'LTS':
                        #                 #    print('please review this')
                        #                 #    sys.exit()

                        #             # Assign parameters back: for these subset of uncertainties
                        #             new_value_list_rounded = [
                        #                 round(elem, 4) for elem in new_value_list]
                        #             inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list_rounded)

                        #             # If the UpperLimit needs update, do it:
                        #             multiplier_list_2 = [1]*len(time_range_vector)
                        #             for i, val in enumerate(new_value_list):
                        #                 if value_list[i] > 0:
                        #                     multiplier_list_2[i] = val/value_list[i]
                                    
                        #             this_param_2 = 'TotalTechnologyAnnualActivityUpperLimit'
                        #             this_set_range_indices_2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_2][tsti]) if x == str(this_set)]
                        #             if len(this_set_range_indices_2) != 0:
                        #                 value_list_2 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1]]
                        #                 new_value_list_2 = [multiplier_list_2[i]*val for i, val in enumerate(value_list_2)]
                        #                 new_value_list_rounded_2 = [
                        #                     round(elem, 4) for elem in new_value_list_2]
                        #                 inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1] = deepcopy(new_value_list_rounded_2)
                        #                 # print('check again 1')
                        #                 # sys.exit()
                                    

                        #         # Get the sets that have not been adjusted and adjust relative to the new demand:
                        #         all_possible_sets = list(set(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]))
                        #         pending_sets = [i for i in all_possible_sets if i not in all_set_involved and ('PP_' in i or 'PPI' in i) and ('HYD' not in i) and ('GEO' not in i)]
                        #         for a_set in range( len( pending_sets ) ):
                        #             # Get the set:
                        #             this_set = pending_sets[a_set]
                        #             this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(this_set)]

                        #             # Perform the adjustment:|
                        #             value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]
                        #             new_value_list = [value_list[i]*total_val/total_elec_demand_bc[i] for i, total_val in enumerate(total_elec_demand)]

                        #             # Assign parameters back: for these subset of uncertainties
                        #             new_value_list_rounded = [
                        #                 round(elem, 4) for elem in new_value_list]
                        #             inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list_rounded)

                        #             # if this_set == 'PP_SPV_DG' and scenario_list[s] == 'LTS' and f == 2:
                        #             #     print('check again 2')
                        #             #     sys.exit()

                        #             # If the UpperLimit needs update, do it:
                        #             multiplier_list_2 = [1]*len(time_range_vector)
                        #             for i, val in enumerate(new_value_list):
                        #                 if value_list[i] > 0:
                        #                     multiplier_list_2[i] = val/value_list[i]
                                    
                        #             this_param_2 = 'TotalTechnologyAnnualActivityUpperLimit'
                        #             this_set_range_indices_2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_2][tsti]) if x == str(this_set)]
                        #             if len(this_set_range_indices_2) != 0:
                        #                 value_list_2 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1]]
                        #                 new_value_list_2 = [multiplier_list_2[i]*val for i, val in enumerate(value_list_2)]
                        #                 new_value_list_rounded_2 = [
                        #                     round(elem, 4) for elem in new_value_list_2]
                        #                 inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1] = deepcopy(new_value_list_rounded_2)

                        #             # Increase MaxCapacity if necessary:
                        #             this_param_3 = 'TotalAnnualMaxCapacity'
                        #             this_set_range_indices_3 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_3][tsti]) if x == str(this_set)]
                        #             if len(this_set_range_indices_3) != 0 and multiplier_list_2[-1] > 1:
                        #                 value_list_3 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_3]['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1]]
                        #                 new_value_list_3 = [multiplier_list_2[i]*val for i, val in enumerate(value_list_3)]
                        #                 new_value_list_rounded_3 = [
                        #                     round(elem, 4) for elem in new_value_list_3]
                        #                 inherited_scenarios[scenario_list[s]][f][this_param_3]['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1] = deepcopy(new_value_list_rounded_3)

                        #                 # if this_set == 'PP_SPV_DG' and scenario_list[s] == 'LTS' and f == 2:
                        #                 #     print('check again 2-2')
                        #                 #     # sys.exit()

                        #         # Override the restriction of "T5CRUTRN":
                        #         this_set_range_indices_3 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit'][tsti]) if x == str("T5CRUCRUTRN")]
                        #         value_list_3 = [float(val) for val in inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1]]
                        #         new_value_list_3 = []
                        #         if len(value_list_3) > 0:
                        #             for i in range(len(time_range_vector)):
                        #                 # if time_range_vector[i] <= 2023:
                        #                 #     new_value_list_3.append(value_list_3[i])
                        #                 # else:
                        #                 #     new_value_list_3.append(99999)
                        #                 new_value_list_3.append(99999)
                        #             new_value_list_rounded_3 = [
                        #                 round(elem, 4) for elem in new_value_list_3]
                        #             inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1] = deepcopy(new_value_list_rounded_3)

                        #         this_set_range_indices_4 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit'][tsti]) if x == str("T4_DSLPUB")]
                        #         value_list_4 = [float(val) for val in inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_set_range_indices_4[0]:this_set_range_indices_4[-1]+1]]

                                # print('what is wrong here')
                                # sys.exit()
                                
                        elif X_Cat in [ 'Transport Demand', 'Costs Samples', 'Storage Costs']:
                            #FALTA ACA
                            diccionario_match_costos = {'DIST_DSL':'DIST_DSL',
                                                        'T5DSLCOM':'DIST_DSL',
                                                        'T5DSLRES':'DIST_DSL',
                                                        'T5DSLINDCEM':'DIST_DSL',
                                                        'T5DSLINDBAX':'DIST_DSL',
                                                        'T5DSLINDSUM':'DIST_DSL',
                                                        'T5DSLINDOTM':'DIST_DSL',
                                                        'T5DSLCON':'DIST_DSL',
                                                        'T5DSLTMA':'DIST_DSL',
                                                        'T5DSLTRO':'DIST_DSL',
                                                        
                                                        'DIST_GSL':'DIST_GSL',
                                                        'T5GSLCOM':'DIST_GSL',
                                                        'T5GSLRES':'DIST_GSL',
                                                        'T5GSLINDCEM':'DIST_GSL',
                                                        'T5GSLINDBAX':'DIST_GSL',
                                                        'T5GSLINDSUM':'DIST_GSL',
                                                        'T5GSLINDOTM':'DIST_GSL',
                                                        'T5GSLCON':'DIST_GSL',
                                                        'T5GSLTRO':'DIST_GSL',
                                                        
                                                        'DIST_LPG':'DIST_LPG',
                                                        'T5LPGCOM':'DIST_LPG',
                                                        'T5LPGRES':'DIST_LPG',
                                                        'T5LPGTMA':'DIST_LPG',
                                                        'T5LPGTRO':'DIST_LPG',
                                                        
                                                        'DIST_FOI':'DIST_FOI',
                                                        'T5FOIINDCEM':'DIST_FOI',
                                                        'T5FOIINDBAX':'DIST_FOI',
                                                        'T5FOIINDSUM':'DIST_FOI',
                                                        'T5FOIINDOTM':'DIST_FOI',
                                                        'T5FOICON':'DIST_FOI',
                                                        'T5FOITMA':'DIST_FOI',
                                                        'T5FOITRO':'DIST_FOI',

                                                        'DIST_JET':'DIST_KER',
                                                        'T5JETTAE':'DIST_KER'
                                                        }
                            if X_Cat in ['Costs Samples']:
                                
                                for a_set in range( len( Sets_Involved ) ):
                                    
                                    this_set = Sets_Involved[a_set]
                                    tecno_aux=diccionario_match_costos[this_set]
                                    tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                    this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(this_set)]
    
                                    value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]
                                    
                                    new_value_list = list(dic_variable_cost[scenario_list[s]+';'+str(f)+';'+tecno_aux].values())
                                    inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list)
                                
                            elif X_Cat in ['Transport Demand']:
                                
                                for a_set in range( len( Sets_Involved ) ):
                                    
                                    this_set = Sets_Involved[a_set]
                                    tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('FUEL') ]
                                    this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(this_set)]
    
                                    value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]
                                    
                                    new_value_list = list(dic_transport_demand[scenario_list[s]+';'+str(f)+';'+this_set].values())
                                    inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list)

                            elif X_Cat in ['Storage Costs']:
                                
                                #print('############################################ ENTRA ################################################')
                                #print(Sets_Involved)
                                for a_set in range( len( Sets_Involved ) ):
                                    
                                    this_set = Sets_Involved[a_set]
                                    tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                    this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(this_set)]
    
                                    value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]
                                    
                                    time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                    
                                    new_value_list = deepcopy(
                                        interpolation_non_linear_final2(
                                        time_list, value_list,
                                        float(Values_per_Future[fut_id]),
                                        2055,Initial_Year_of_Uncertainty))
                                    
                                    year_re_tech = list(dic_storage_limits[scenario_list[s]+';'+str(f)+';'+this_set].keys())
                                    capacity_re_tech_f0 = list(dic_storage_limits[scenario_list[s]+';'+str(0)+';'+this_set].values())
                                    capacity_re_tech = list(dic_storage_limits[scenario_list[s]+';'+str(f)+';'+this_set].values())
                                    capacity_re_tech_norm = [n/d if d != 0 else 0 for n, d in zip(capacity_re_tech, capacity_re_tech_f0)]
                                    #print(f)
                                    #print(capacity_re_tech_norm)
                                    
                                    if this_parameter in ['CapitalCost']:
                                        battery_costs=list(dic_storage_capex.values())
                                    else:
                                        battery_costs=list(dic_storage_fixed.values())
                                    
                                    #FALTA ACA
                                    new_value_list2=list()
                                    for ite in range(len(new_value_list)):
                                        if time_list[ite] <= 2035:
                                            new_value_list2.append(new_value_list[ite])
                                        else:
                                            new_value_list2.append(new_value_list[ite]+capacity_re_tech_norm[ite]*battery_costs[ite])
                                            
                                    inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list2)
                                #print('SALIMOS')
                                #sys.exit()


                        elif 'Mult_Restriction' in Math_Type:
                            ###
                            ### ACA NO SE ENTRA
                            ###
                            print('Penetracion de renovables')
                            print('Energy_3')
                            #
                            enter_if_cycle = True
                            #
                            '''
                            The script below should work if the sets sum 100% of the generation in the base cases,
                            i.e., the sum of "value_list_sh" across all sets should be 100% every year.
                            '''

                            if 'Start' in Math_Type:
                                # Define a total denominator for normalization:
                                new_value_list_sh_sum = [0]*len(time_range_vector)
                                value_list_sh_sum = [0]*len(time_range_vector)

                                this_set_type_initial = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                store_new_sh = {}
                                store_refval_sh = {}

                                all_set_involved = []

                            # Iterate across every single set
                            for a_set in range( len( Sets_Involved ) ):
                                # Get each share of Upper and Lower limit in the base case
                                this_set = Sets_Involved[a_set]
                                all_set_involved.append(this_set)
                                this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][this_set_type_initial]) if x == str(this_set)]
                                #print(this_set)
                                value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]

                                # Get the share:
                                value_list_sh = [value_list[i]/total_val for i, total_val in enumerate(total_elec_demand_bc)]

                                store_refval_sh.update({
                                    this_set:deepcopy(value_list_sh)})

                                if scenario_list[s] != 'BAU':
                                    new_value_list_sh = \
                                        interpolation_multiplier2(
                                            time_list, value_list_sh,
                                            Values_per_Future[fut_id])
                                else:
                                    new_value_list_sh = deepcopy(
                                        value_list_sh)

                                store_new_sh.update({
                                    this_set:deepcopy(new_value_list_sh)})

                                new_value_list_sh_sum = list(map(
                                    operator.add, new_value_list_sh_sum,
                                    new_value_list_sh))

                                value_list_sh_sum = list(map(
                                    operator.add, value_list_sh_sum,
                                    value_list_sh))                      

                            if 'End' in Math_Type:

                                #for i in range(len(time_range_vector)):
                                #    if time_range_vector[i] <= params['change_year']:
                                #        new_value_list_sh_sum[i] = 1
                                
                                # Iterate again to apply normalization:
                                for a_set in range( len( all_set_involved ) ):
                                    
                                    this_set = all_set_involved[a_set]
                                    this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][this_set_type_initial]) if x == str(this_set)]
                                    
                                    value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]

                                    # Get the share:
                                    value_list_sh = [value_list[i]/total_val for i, total_val in enumerate(total_elec_demand_bc)]

                                    # Normalize the share:
                                    new_value_list_sh_norm = [store_new_sh[this_set][i]*value_list_sh_sum[i]/sh_sum for i, sh_sum in enumerate(new_value_list_sh_sum)]

                                    # Calculate the magnitude according to adjusted demand:
                                    new_value_list = [new_value_list_sh_norm[i]*total_val for i, total_val in enumerate(total_elec_demand)]

                                    # Add a filter for wind on-shore generation:
                                    if this_set in ['PPWNDON','PPWNDONS']:
                                        max_prod_in_gwh = 0.88 * 0.5214 * 0.95 * 8760
                                        sec_val = 0.98
                                        max_prod_in_pj = max_prod_in_gwh * 0.0036 * sec_val
                                        for i in range(len(new_value_list)):
                                            if new_value_list[i] > max_prod_in_pj:
                                                new_value_list[i] = max_prod_in_pj

                                    # Add a filter for wind off-shore generation:
                                    if this_set == 'PPWNDOFF':
                                        max_prod_in_gwh = 0.88 * 0.5214 * 0.95 * 8760
                                        sec_val = 0.98
                                        max_prod_in_pj = max_prod_in_gwh * 0.0036 * sec_val
                                        for i in range(len(new_value_list)):
                                            if new_value_list[i] > max_prod_in_pj:
                                                new_value_list[i] = max_prod_in_pj

                                    # Assign parameters back: for these subset of uncertainties
                                    new_value_list_rounded = [
                                        round(elem, 4) for elem in new_value_list]
                                    inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list_rounded)

                                    # If the UpperLimit needs update, do it:
                                    multiplier_list_2 = [1]*len(time_range_vector)
                                    for i, val in enumerate(new_value_list):
                                        if value_list[i] > 0:
                                            multiplier_list_2[i] = val/value_list[i]
                                    
                                    this_param_2 = 'TotalTechnologyAnnualActivityUpperLimit'
                                    this_set_range_indices_2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_2][this_set_type_initial]) if x == str(this_set)]
                                    if len(this_set_range_indices_2) != 0:
                                        value_list_2 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1]]
                                        new_value_list_2 = [multiplier_list_2[i]*val for i, val in enumerate(value_list_2)]

                                        new_value_list_rounded_2 = [
                                                round(elem, 4) for elem in new_value_list_2]
                                        
                                        inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1] = deepcopy(new_value_list_rounded_2)


                                    # Change values of 'CapacityFactor' to check TotalTechnologyAnnualActivityLowerLimit isn't bigger tan TotalAnnualMaxCapacity
                                    this_param_3 = 'TotalTechnologyAnnualActivityLowerLimit'
                                    this_set_range_indices_3 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_3][this_set_type_initial]) if x == str(this_set)]
                                    this_param_4 = 'TotalAnnualMaxCapacity'
                                    this_set_range_indices_4 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_4][this_set_type_initial]) if x == str(this_set)]
                                    this_param_5 = 'CapacityFactor'
                                    this_set_range_indices_5 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_5][this_set_type_initial]) if x == str(this_set)]
                                    if len(this_set_range_indices_4) != 0 and len(this_set_range_indices_5) != 0:
                                        # 'TotalTechnologyAnnualActivityLowerLimit'
                                        value_list_3 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_3]['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1]]
                                        # 'TotalAnnualMaxCapacity'
                                        value_list_4 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_4]['value'][this_set_range_indices_4[0]:this_set_range_indices_4[-1]+1]]
                                        # 'CapacityFactor'
                                        value_list_5 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_5]['value'][this_set_range_indices_5[0]:this_set_range_indices_5[-1]+1]]
                                        
                                        # if this_set == 'PPCCTDSL' and scenario_list[s] == 'LTS' and f == 9:
                                        #     print('Vamos bien')

                                        # Iterate over the lists and adjust value_list_5 if necessary
                                        for i in range(len(value_list_3)):
                                            lower_limit = value_list_3[i]
                                            max_capacity = value_list_4[i]
                                            capacity_factor = value_list_5[i]
                                            
                                            # Define a small increment
                                            increment = 0.0001
                                            
                                            while lower_limit > max_capacity * capacity_factor * 31.356:
                                                # print(this_set, i, "########################################################################")
                                                # Adjust the value of CapacityFactor incrementally to satisfy the inequality
                                                # capacity_factor += increment
                                                # value_list_5[i] = capacity_factor
                                                
                                                # Adjust the value of TotalTechnologyAnnualActivityLowerLimit decrementally to satisfy the inequality
                                                lower_limit -= increment
                                            value_list_3[i] = lower_limit

                                        # # For CapacityFactor
                                        # new_value_list_rounded_5 = [
                                        #         round(elem, params['round_#']) for elem in value_list_5]
                                        
                                        # inherited_scenarios[scenario_list[s]][f][this_param_5]['value'][this_set_range_indices_5[0]:this_set_range_indices_5[-1]+1] = deepcopy(new_value_list_rounded_5)

                                        # For TotalTechnologyAnnualActivityLowerLimit
                                        new_value_list_rounded_3 = [
                                                round(elem, 4) for elem in value_list_3]
                                        
                                        inherited_scenarios[scenario_list[s]][f][this_param_3]['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1] = deepcopy(new_value_list_rounded_3)






                                    # Change values of 'TotalTechnologyAnnualActivityLowerLimit' to check TotalTechnologyAnnualActivityLowerLimit isn't bigger tan TotalTechnologyAnnualActivityUpperLimit
                                    if this_parameter == 'TotalTechnologyAnnualActivityLowerLimit' or this_parameter == 'TotalTechnologyAnnualActivityUpperLimit':
                                        this_param_6 = 'TotalTechnologyAnnualActivityLowerLimit'
                                        this_set_range_indices_6 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_6][this_set_type_initial]) if x == str(this_set)]
                                        if len(this_set_range_indices_2) != 0:
                                            value_list_2 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1]]
                                            new_value_list_2 = [multiplier_list_2[i]*val for i, val in enumerate(value_list_2)]
                                            value_list_6 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_6]['value'][this_set_range_indices_6[0]:this_set_range_indices_6[-1]+1]]
                                            new_value_list_2 = [max(v2, v6) if v6 > v2 else v2 for v2, v6 in zip(new_value_list_2, value_list_6)]
      
                                            new_value_list_rounded_2 = [
                                                    round(elem, 4) for elem in new_value_list_2]
                                            
                                            inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1] = deepcopy(new_value_list_rounded_2)
                                                
                                    # if 
                                    # this_parameter == 'TotalTechnologyAnnualActivityLowerLimit' or this_parameter == 'TotalTechnologyAnnualActivityUpperLimit'
                                 # Get the sets that have not been adjusted and adjust relative to the new demand:
                                all_possible_sets = list(set(inherited_scenarios[scenario_list[s]][f][this_parameter][this_set_type_initial]))
                                pending_sets = [i for i in all_possible_sets if i not in all_set_involved and ('PP' in i or 'PPI' in i) and ('PPH' not in i) and ('GEO' not in i)]
                                # if scenario_list[s] == 'LTS' and f == 3:
                                #     print('##########')
                                #     print('CHEQUEAR')
                                #     print(all_possible_sets,pending_sets)
                                #     print('##########')
                                for a_set in range( len( pending_sets ) ):
                                    # Get the set:
                                    this_set = pending_sets[a_set]
                                    this_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][this_set_type_initial]) if x == str(this_set)]

                                    # Perform the adjustment:|
                                    value_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1]]
                                    new_value_list = [value_list[i]*total_val/total_elec_demand_bc[i] for i, total_val in enumerate(total_elec_demand)]
                                    # print('##########')
                                    # print('CHEQUEAR 2')
                                    # print(value_list,new_value_list)
                                    # print('##########')

                                    # Assign parameters back: for these subset of uncertainties
                                    new_value_list_rounded = [
                                        round(elem, 4) for elem in new_value_list]
                                    inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list_rounded)

                                    # if this_set == 'PP_SPV_DG' and scenario_list[s] == '' and f == 2:
                                    #     print('check again 2')
                                    #     sys.exit()

                                    # If the UpperLimit needs update, do it:
                                    multiplier_list_2 = [1]*len(time_range_vector)
                                    for i, val in enumerate(new_value_list):
                                        if value_list[i] > 0:
                                            multiplier_list_2[i] = val/value_list[i]
                                    
                                    this_param_2 = 'TotalTechnologyAnnualActivityUpperLimit'
                                    this_set_range_indices_2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_2][this_set_type_initial]) if x == str(this_set)]
                                    if len(this_set_range_indices_2) != 0:
                                        # print('###################')
                                        # print('CHEQUEAR SI ENTRA')
                                        # print('###################')
                                        value_list_2 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1]]
                                        new_value_list_2 = [multiplier_list_2[i]*val for i, val in enumerate(value_list_2)]
                                        new_value_list_rounded_2 = [
                                            round(elem, 4) for elem in new_value_list_2]
                                        inherited_scenarios[scenario_list[s]][f][this_param_2]['value'][this_set_range_indices_2[0]:this_set_range_indices_2[-1]+1] = deepcopy(new_value_list_rounded_2)

                                    # Increase MaxCapacity if necessary:
                                    this_param_3 = 'TotalAnnualMaxCapacity'
                                    this_set_range_indices_3 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_param_3][this_set_type_initial]) if x == str(this_set)]
                                    if len(this_set_range_indices_3) != 0 and multiplier_list_2[-1] > 1:
                                        value_list_3 = [float(val) for val in inherited_scenarios[scenario_list[s]][f][this_param_3]['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1]]
                                        new_value_list_3 = [multiplier_list_2[i]*val for i, val in enumerate(value_list_3)]
                                        new_value_list_rounded_3 = [
                                            round(elem, 4) for elem in new_value_list_3]
                                        inherited_scenarios[scenario_list[s]][f][this_param_3]['value'][this_set_range_indices_3[0]:this_set_range_indices_3[-1]+1] = deepcopy(new_value_list_rounded_3)

                        #------------------------------------------------------------------------------------------------------------------------------------------#
                        elif X_Cat == 'Rail Demand': # THIS SEEMS UNUSED
                            #
                            enter_if_cycle = True
                            #
                            for a_set in range( len( Sets_Involved ) ):
                                #
                                this_set = Sets_Involved[ a_set ]
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 't' ] ) if x == str( this_set ) ]
                                #
                                # extracting time:
                                time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                # extracting value:
                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #                                
                                new_value_list = deepcopy( dc_shift( time_list, value_list, float(Values_per_Future[fut_id] ) ) )
                                new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                #
                                inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy( new_value_list_rounded )

                        #------------------------------------------------------------------------------------------------------------------------------------------#
                        # The X type below is manipulated with immediate restitution after adjustment.
                        elif Math_Type in ['Adoption_Curve', 'Mult_Adoption_Curve'] and X_Cat == 'Mode Shift':
                            #
                            enter_if_cycle = True
                            #
                            for a_set in range( len( Sets_Involved ) ):
                                tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('FUEL') ]
                                #
                                this_set = Sets_Involved[a_set]
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]

                                # for each index we extract the time and value in a list:
                                # extracting time:
                                time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]

                                if Math_Type == 'Adoption_Curve':
                                    #--------------------------------------------------------------------------#
                                    # before manipulating the variables for Mode Shift, we must use use the reference ratio of the future 0 - BAU. It is crucial to conceive the change as a relative of this baseline for more critcal comparison. BAU does not change this share. Finally, we leave Non-Motorized out of this procedure because it does not affect the BAU.
                                    #
                                    passpub_range_indices_BAU = [ i for i, x in enumerate( stable_scenarios['BAU'][ 'SpecifiedAnnualDemand' ][ tsti ] ) if x == str( 'E6TDPASPUB' ) ]
                                    passpub_value_list_BAU_0 = deepcopy( stable_scenarios['BAU'][ 'SpecifiedAnnualDemand' ]['value'][ passpub_range_indices_BAU[0]:passpub_range_indices_BAU[-1]+1 ] )
                                    passpub_value_list_BAU_0 = [ float( passpub_value_list_BAU_0[j] ) for j in range( len( passpub_value_list_BAU_0 ) ) ]
                                    #
                                    passpriv_range_indices_BAU = [ i for i, x in enumerate( stable_scenarios['BAU'][ 'SpecifiedAnnualDemand' ][ tsti ] ) if x == str( 'E6TDPASPRI' ) ]
                                    passpriv_value_list_BAU_0 = deepcopy( stable_scenarios['BAU'][ 'SpecifiedAnnualDemand' ]['value'][ passpriv_range_indices_BAU[0]:passpriv_range_indices_BAU[-1]+1 ] )
                                    passpriv_value_list_BAU_0 = [ float( passpriv_value_list_BAU_0[j] ) for j in range( len( passpriv_value_list_BAU_0 ) ) ]
                                    #
                                    passpub_share_list_BAU_0 = [ passpub_value_list_BAU_0[j]/(passpub_value_list_BAU_0[j]+passpriv_value_list_BAU_0[j]) for j in range( len(passpub_value_list_BAU_0) ) ]
                                    #
                                    passpriv_share_list_BAU_0 = [ passpriv_value_list_BAU_0[j]/(passpub_value_list_BAU_0[j]+passpriv_value_list_BAU_0[j]) for j in range( len(passpriv_value_list_BAU_0) ) ]
                                    #
                                    #--------------------------------------------------------------------------#
                                    #  WE DO NOT NEED TO EXTRACT THE EXACT VALUE:
                                    # now that the value is extracted, we must manipulate the result and assign back
                                    L_index = 0
                                    Q_index = 1
                                    k_index = 2
                                    M_index = 3
                                    #
                                    L = Values_per_Future[fut_id][L_index]
                                    Q = Values_per_Future[fut_id][Q_index]
                                    k = Values_per_Future[fut_id][k_index]
                                    M = Values_per_Future[fut_id][M_index]
                                    #
                                    shift_years = [ n for n in range( Initial_Year_of_Uncertainty+1,final_year+1 ) ]
                                    shift_year_counter = 0
                                    adoption_shift = []
                                    #
                                    for t in range( len( time_list ) ):
                                        if time_list[t] > Initial_Year_of_Uncertainty:
                                            x = int( shift_years[shift_year_counter] )
                                            adoption_shift.append( generalized_logistic_curve(x, L, Q, k, M))
                                            shift_year_counter += 1
                                        else:
                                            adoption_shift.append( 0.0 )
                                    ######################################################################################################################################################
                                    new_value_list = []
                                    for n in range( len( time_list ) ):
                                        if 'E6TDPASPUB' in this_set:
                                            new_value_list.append( ( passpub_share_list_BAU_0[n] + adoption_shift[n] )*( TotalDemand[n] ) )
                                            #
                                        #
                                        elif 'E6TRNOMOT' in this_set:
                                            new_value_list.append( ( adoption_shift[n] )*( TotalDemand[n] ) )
                                    # 
                                    new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                    #
                                    # Assign parameters back: for these subset of uncertainties
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy( new_value_list_rounded )
                                    #
                                    #-----------------------------------------------------------------------#

                                elif Math_Type == 'Mult_Adoption_Curve':
                                    passpub_range_indices = [ i for i, x in enumerate( stable_scenarios[scenario_list[s]][ 'SpecifiedAnnualDemand' ][ tsti ] ) if x == str( 'E6TDPASPUB' ) ]
                                    passpub_value_list_0 = deepcopy( stable_scenarios[scenario_list[s]][ 'SpecifiedAnnualDemand' ]['value'][ passpub_range_indices[0]:passpub_range_indices[-1]+1 ] )
                                    passpub_value_list_0 = [ float( passpub_value_list_0[j] ) for j in range( len( passpub_value_list_0 ) ) ]
                                    #
                                    passpriv_range_indices = [ i for i, x in enumerate( stable_scenarios[scenario_list[s]][ 'SpecifiedAnnualDemand' ][ tsti ] ) if x == str( 'E6TDPASPRI' ) ]
                                    passpriv_value_list_0 = deepcopy( stable_scenarios[scenario_list[s]][ 'SpecifiedAnnualDemand' ]['value'][ passpriv_range_indices[0]:passpriv_range_indices[-1]+1 ] )
                                    passpriv_value_list_0 = [ float( passpriv_value_list_0[j] ) for j in range( len( passpriv_value_list_0 ) ) ]
                                    #
                                    passnomot_range_indices = [ i for i, x in enumerate( stable_scenarios[scenario_list[s]][ 'SpecifiedAnnualDemand' ][ tsti ] ) if x == str( 'E6TRNOMOT' ) ]
                                    passnomot_value_list_0 = deepcopy( stable_scenarios[scenario_list[s]][ 'SpecifiedAnnualDemand' ]['value'][ passnomot_range_indices[0]:passnomot_range_indices[-1]+1 ] )
                                    passnomot_value_list_0 = [ float( passnomot_value_list_0[j] ) for j in range( len( passnomot_value_list_0 ) ) ]
                                    #
                                    pass_sum_list_0 = [sum(x) for x in zip(
                                        passpub_value_list_0,
                                        passpriv_value_list_0,
                                        passnomot_value_list_0)]
                                    #
                                    passpub_share_list_0 = [passpub_value_list_0[j]/pass_sum_list_0[j] for j in range(len(pass_sum_list_0))]
                                    passpriv_share_list_0 = [passpriv_value_list_0[j]/pass_sum_list_0[j] for j in range(len(pass_sum_list_0))]
                                    passnomot_share_list_0 = [passnomot_value_list_0[j]/pass_sum_list_0[j] for j in range(len(pass_sum_list_0))]
                                    #
                                    passpub_share_adj = \
                                        interpolation_multiplier(
                                            time_list, passpub_share_list_0,
                                            Values_per_Future[fut_id] )
                                    passpriv_share_adj = \
                                        interpolation_multiplier(
                                            time_list, passpriv_share_list_0,
                                            Values_per_Future[fut_id] )
                                    passnomot_share_adj = \
                                        interpolation_multiplier(
                                            time_list, passnomot_share_list_0,
                                            Values_per_Future[fut_id] )

                                    ######################################################################################################################################################
                                    new_value_list = []

                                    for n in range(len(time_list)):
                                        if 'E6TDPASPUB' in this_set:
                                            new_value_list.append(passpub_share_adj[n]*(TotalDemand[n]))
                                        elif 'E6TRNOMOT' in this_set:
                                            new_value_list.append(passnomot_share_adj[n]*(TotalDemand[n]))
                                    # 
                                    new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                    #                                   
                                    # Assign parameters back: for these subset of uncertainties
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy( new_value_list_rounded )

                                else:
                                    print('Missing a Mode Shift method!')
                                    sys.exit()

                                # Note that because of the Experimental Table setup, after the non-motorized assignation we can adjust the values for PRIVATE TRANSPORT.
                                if 'E6TRNOMOT' in this_set:
                                    nonmot_values = deepcopy( new_value_list_rounded )# this retrieves non-motorized
                                    # we must retrieve the value of public transport
                                    passpub_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ][ tsti ] ) if x == str( 'E6TDPASPUB' ) ]
                                    passpub_values = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'SpecifiedAnnualDemand' ]['value'][ passpub_range_indices[0]:passpub_range_indices[-1]+1 ] )
                                    # we estimate the new private transport demand here:
                                    passpriv_new_value_list = []
                                    for n in range( len(TotalDemand) ):
                                        passpriv_new_value_list.append( TotalDemand[n] - nonmot_values[n] - passpub_values[n] )
    
                                    passpriv_new_value_list_rounded = [ round(elem, 4) for elem in passpriv_new_value_list ]
    
                                    if passpriv_new_value_list_rounded[-1] < 0:
                                        print('waaaaaait')
                                        sys.exit()
    
                                    # Assign parameters back:
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ][ tsti ] ) if x == str( 'E6TDPASPRI' ) ]
                                    inherited_scenarios[ scenario_list[s] ][ f ][ 'SpecifiedAnnualDemand' ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy( passpriv_new_value_list_rounded )

                        #------------------------------------------------------------------------------------------------------------------------------------------#
                        elif Math_Type == 'Time_Series' and X_Cat == 'Mode Shift':  # this generally applies to freight rail
                            #
                            enter_if_cycle = True
                            #
                            # CODE HERE THE MODIFICATION OF THE CAPACITY OF RAIL
                            this_set = Sets_Involved[0]

                            # We need to call the group capacity
                            this_set_indices = [ i for i, x in enumerate( inherited_scenarios[scenario_list[s]][f][ this_parameter ][ 't' ] ) if x == str( this_set ) ]
                            value_list = deepcopy( inherited_scenarios[scenario_list[s]][f][ this_parameter ]['value'][ this_set_indices[0]:this_set_indices[-1]+1 ] )
                            value_list = [ float(value_list[j]) for j in range( len( time_range_vector ) ) ]

                            # We also need the demand correspoding to this set before any adjustments (stable_scenarios) // demand-based adjustments occurs later
                            this_demand_set = Fleet_Groups_techs_2_dem[ this_set ]
                            this_demand_set_range_indices = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ 'SpecifiedAnnualDemand' ][ 'f' ] ) if x == str( this_demand_set ) ]
                            this_demand_set_value = deepcopy( stable_scenarios[ scenario_list[ s ] ][ 'SpecifiedAnnualDemand' ]['value'][ this_demand_set_range_indices[0]:this_demand_set_range_indices[-1]+1 ] )
                            this_demand_set_value = [ float(this_demand_set_value[j]) for j in range( len( time_range_vector ) ) ]

                            # Linear interpolation of freight modal shift
                            v_2050 = float(Values_per_Future[fut_id] )
                            x_coord_tofill, xp_coord_known, yp_coord_known = [], [], []
                            for y in range( len( time_range_vector ) ):
                                not_known_e = True
                                if time_range_vector[y] < Initial_Year_of_Uncertainty:
                                    xp_coord_known.append( y )
                                    yp_coord_known.append( 0 )
                                    not_known_e = False
                                if time_range_vector[y] == 2050:
                                    xp_coord_known.append( y )
                                    yp_coord_known.append( v_2050 )
                                    not_known_e = False
                                if not_known_e is True:
                                    x_coord_tofill.append( y )
                            #
                            y_coord_filled = list( np.interp( x_coord_tofill, xp_coord_known, yp_coord_known ) )
                            interpolated_values = []
                            for coord in range( len( time_range_vector ) ):
                                if coord in xp_coord_known:
                                    value_index = xp_coord_known.index(coord)
                                    interpolated_values.append( float( yp_coord_known[value_index] ) )
                                elif coord in x_coord_tofill:
                                    value_index = x_coord_tofill.index(coord)
                                    interpolated_values.append( float( y_coord_filled[value_index] ) )

                            # We redifine the new capacity of trains according to demand:
                            new_value_list = [ float( interpolated_values[j]*this_demand_set_value[j] ) for j in range( len( time_range_vector ) ) ]
                            new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                            inherited_scenarios[scenario_list[s]][f][ this_parameter ]['value'][ this_set_indices[0]:this_set_indices[-1]+1 ] = deepcopy( new_value_list_rounded )

                            # We must adjust the capacity of the complementary set of *Techs_Trains_Freight*
                            this_set_complement_dict = {'Techs_Trains_Freight':'Techs_He_Freight'}
                            this_set_complement = this_set_complement_dict[this_set]
                            this_set_complement_indices = [ i for i, x in enumerate( inherited_scenarios[scenario_list[s]][f][ this_parameter ][ 't' ] ) if x == str( this_set_complement ) ]
                            value_list_complement = deepcopy( inherited_scenarios[scenario_list[s]][f][ this_parameter ]['value'][ this_set_complement_indices[0]:this_set_complement_indices[-1]+1 ] )
                            value_list_complement = [ float(value_list_complement[j]) for j in range( len( time_range_vector ) ) ]

                            # Extract OR parameters:
                            or_group_tech_indices = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ 'OutputActivityRatio' ][ 't' ] ) if x == str( this_set_complement ) ]
                            or_group_tech_values = deepcopy( stable_scenarios[ scenario_list[ s ] ][ 'OutputActivityRatio' ]['value'][ or_group_tech_indices[0]:or_group_tech_indices[-1]+1 ] )
                            or_group_tech_values = [ float( or_group_tech_values[j] ) for j in range( len( or_group_tech_values ) ) ]

                            # Define new heavy truck capacity
                            if this_parameter == 'TotalAnnualMaxCapacity':
                                security_multiplier_factor = 1.01
                            elif this_parameter == 'TotalTechnologyAnnualActivityLowerLimit':
                                security_multiplier_factor = 0.999

                            new_value_list_comp = []
                            for y in range(len(time_range_vector)):
                                if time_range_vector[y] < Initial_Year_of_Uncertainty:
                                    new_value_list_comp.append(value_list_complement[y])
                                else:
                                    new_value_list_comp.append( security_multiplier_factor*(this_demand_set_value[y] - new_value_list_rounded[y])/or_group_tech_values[y] )

                            new_value_list_comp_rounded = [ round(elem, 4) for elem in new_value_list_comp ]
                            inherited_scenarios[scenario_list[s]][f][ this_parameter ]['value'][ this_set_complement_indices[0]:this_set_complement_indices[-1]+1 ] = deepcopy( new_value_list_comp_rounded )

                        #------------------------------------------------------------------------------------------------------------------------------------------#
                        #
                        # The X type below is manipulated with immidiate restitution after adjustment.
                        elif ( Math_Type=='Time_Series' and ( Explored_Parameter_of_X=='Initial_Value' or
                                                              Explored_Parameter_of_X=='Final_Value' or
                                                              Explored_Parameter_of_X=='Shift_as_percent_of_Initial_Value'
                                                              or Explored_Parameter_of_X=='Year_when_reaches_zero' )
                                                              and ('Distance' not in X_Cat)
                                                              and ('Demand' not in X_Cat)
                                                              and ('Non-Rail' not in X_Cat)
                                                              and ('Mode Shift' not in X_Cat) ) or ( Math_Type=='Discrete_Investments' ):
                            #
                            enter_if_cycle = True
                            #
                            if 'InputActivityRatio' == this_parameter: # we must carefully select the fuels for IAR!
                                #
                                for a_set in range( len( Sets_Involved ) ):
                                    #
                                    this_set = Sets_Involved[a_set]
                                    this_set_range_indices_tech = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 't' ] ) if x == str( this_set ) ]
                                    #
                                    this_set_fuel_list = []
                                    for test_j in range( len( this_set_range_indices_tech ) ):
                                        if float( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices_tech[test_j] ] ) != 1.0:
                                            this_set_fuel_list.append( deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['f'][ this_set_range_indices_tech[test_j] ] ) )
                                        #
                                    #
                                    this_set_fuel_list_unique = list( set( this_set_fuel_list ) )
                                    #
                                    for a_fuel in range( len( this_set_fuel_list_unique ) ):
                                        this_set_fuel = this_set_fuel_list_unique[ a_fuel ]
                                        #
                                        this_set_range_indices_fuel = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 'f' ] ) if x == str( this_set_fuel ) ]
                                        #
                                        r_index = set(this_set_range_indices_tech) & set(this_set_range_indices_fuel)
                                        this_set_range_indices = list( r_index )
                                        this_set_range_indices.sort()
                                        #
                                        # extracting time:
                                        time_list = []
                                        for i_list in this_set_range_indices:
                                            # time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                            time_list.append(deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ i_list ] ))
                                        time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                        # extracting value:
                                        value_list = []
                                        for i_list in this_set_range_indices:
                                            # value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                            value_list.append(deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ i_list ] ))
                                        value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                        #
                                        if Explored_Parameter_of_X=='Final_Value':
                                            new_value_list = deepcopy( interpolation_non_linear_final2( time_list, value_list, float(Values_per_Future[fut_id] ), 2050,Initial_Year_of_Uncertainty) )
                                        #
                                        if Explored_Parameter_of_X=='Shift_as_percent_of_Initial_Value':
                                            new_value_list = deepcopy( time_series_shift( time_list, value_list, float(Values_per_Future[fut_id] ) ) )
                                        #--------------------------------------------------------------------#
                                        new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                        #
                                        for i_list_idx in range(len(this_set_range_indices)):
                                            i_list = this_set_range_indices[i_list_idx]
                                            inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ i_list ] = deepcopy( new_value_list_rounded[i_list_idx] )
                                        #
                                        '''
                                        if X_Cat == 'Unit BEV Cost':
                                            xx1 = value_list
                                            xx2 = new_value_list
                                            print('check this IAR issue internal')
                                            sys.exit()
                                        '''
                                    #
                                    '''
                                    if X_Cat == 'Unit BEV Cost':
                                        print('check this IAR issue')
                                        sys.exit()
                                    '''
                                    #
                                #
                            #
                            #
                            else:
                                for a_set in range( len( Sets_Involved ) ):
                                    tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                    #
                                    this_set = Sets_Involved[a_set]
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                    #
                                    if this_parameter != 'CapacityFactor' and len(this_set_range_indices) != 0:
                                        # for each index we extract the time and value in a list:
                                        # extracting time:
                                        time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                        # extracting value:
                                        value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                        #--------------------------------------------------------------------#
                                        # now that the value is extracted, we must manipulate the result and assign back
                                        if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios
                                            if this_parameter == 'OutputActivityRatio' and 'Adjustment OAR' not in X_Cat:
                                                if scenario_list[s] == 'BAU':  # bypass this
                                                    new_value_list = deepcopy( interpolation_non_linear_final2( time_list, value_list, float(Values_per_Future[fut_id] ), 2050,Initial_Year_of_Uncertainty) ) 
                                                    reference_occupancy_rate[ scenario_list[s] ][f].update( { this_set:new_value_list } )
                                                #
                                                else:
                                                    # Store the pre-modification values for the BAU
                                                    reference_occupancy_rate[ 'BAU' ][f].update( { this_set:value_list } )
                                                    new_value_list = deepcopy( interpolation_non_linear_final2( time_list, value_list, float(Values_per_Future[fut_id] ), 2050,Initial_Year_of_Uncertainty) ) 
                                                    reference_occupancy_rate[ scenario_list[s] ][f].update( { this_set:new_value_list } )
                                                    #
                                                ###############################################################################
                                                '''
                                                Accidents removed
                                                # Take advantage of this action and make adjustment to accident externalities with changed occupancy rate:
                                                oar_indices_BASE = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ 'OutputActivityRatio' ][ 't' ] ) if x == str( this_set ) ]
                                                oar_values_BASE = deepcopy( stable_scenarios[ scenario_list[ s ] ][ 'OutputActivityRatio' ]['value'][ oar_indices_BASE[0]:oar_indices_BASE[-1]+1 ] )
                                                oar_values_BASE = [ float(oar_values_BASE[j]) for j in range( len(oar_values_BASE) )]
                                                #
                                                time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                                time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                                #
                                                # Use 'new_value_list' to adjust the system:
                                                base_set_range_indices_tech = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ 'EmissionActivityRatio' ][ tsti ] ) if x == str( this_set ) ]
                                                base_set_range_indices_emission = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ 'EmissionActivityRatio' ][ 'e' ] ) if x == str( 'Accidents' ) ]
                                                base_set_range_indices_adjust = list( set(base_set_range_indices_tech) & set(base_set_range_indices_emission) )
                                                base_set_range_indices_adjust.sort()
                                                #--#
                                                this_set_range_indices_tech = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'EmissionActivityRatio' ][ tsti ] ) if x == str( this_set ) ]
                                                this_set_range_indices_emission = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'EmissionActivityRatio' ][ 'e' ] ) if x == str( 'Accidents' ) ]
                                                this_set_range_indices_adjust = list( set(this_set_range_indices_tech) & set(this_set_range_indices_emission) )
                                                this_set_range_indices_adjust.sort()
                                                #
                                                this_tech_externality_emission = deepcopy( stable_scenarios[ scenario_list[ s ] ][ 'EmissionActivityRatio' ]['value'][ base_set_range_indices_adjust[0]:base_set_range_indices_adjust[-1]+1 ] )
                                                #
                                                new_tech_externality_emission = [ float( this_tech_externality_emission[n] )*float( new_value_list[n] )/float( oar_values_BASE[n] ) for n in range( len( this_tech_externality_emission ) ) ]
                                                new_tech_externality_emission_rounded = [ round(elem, 4) for elem in new_tech_externality_emission ]
                                                #
                                                inherited_scenarios[ scenario_list[s] ][ f ][ 'EmissionActivityRatio' ]['value'][ this_set_range_indices_adjust[0]:this_set_range_indices_adjust[-1]+1 ] = deepcopy( new_tech_externality_emission_rounded )
                                                '''
                                                ################################################################################
                                            #
                                            else:
                                                #
                                                if 'CapacityFactor' in Parameters_Involved:
                                                    sec_mult_cf_ll = 0.99
                                                else:
                                                    sec_mult_cf_ll = 1
                                                new_value_list = deepcopy(interpolation_non_linear_final2(time_list, value_list, sec_mult_cf_ll*float(Values_per_Future[fut_id]), 2050,Initial_Year_of_Uncertainty))
                                                #
                                            #
                                        #
                                        elif Explored_Parameter_of_X=='Initial_Value':
                                            new_value_list = deepcopy( interpolation_non_linear_initial( time_list, value_list, float(Values_per_Future[fut_id] ) ) )
                                        elif Explored_Parameter_of_X=='Shift_as_percent_of_Initial_Value':
                                            new_value_list = deepcopy( time_series_shift( time_list, value_list, float(Values_per_Future[fut_id] ) ) )
                                        elif Explored_Parameter_of_X=='Year_when_reaches_zero':
                                            new_value_list = deepcopy( year_when_reaches_zero( time_list, value_list, int(Values_per_Future[fut_id] ) ) )
                                        elif Explored_Parameter_of_X=='Overall_DC_Shift':
                                            new_value_list = deepcopy( dc_shift( time_list, value_list, float(Values_per_Future[fut_id] ) ) )
                                        #
                                        new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                        #--------------------------------------------------------------------#
                                        #
                                        if this_parameter == 'OutputActivityRatio' and 'Adjustment OAR' not in X_Cat: # We must adjust the transport group capacities once we obtain new occupancy rates.
                                            
                                            # let's extract rail capacity to adjust this apropiately
                                            train_pass_capacity_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMaxCapacity' ][ 't' ] ) if x == str( 'Techs_Trains' ) ]
                                            train_pass_capacity_values = inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ train_pass_capacity_indices[0]:train_pass_capacity_indices[-1]+1 ]
                                            if Fleet_Groups_techs_2_dem[ Sets_Involved[ a_set ] ] == 'E6TDPASPUB' and scenario_list[ s ] == 'LTS':
                                                subtract_list = [float(train_pass_capacity_values[j]) for j in range(len(train_pass_capacity_values))]
                                            else:
                                                subtract_list = [0 for j in range(len(train_pass_capacity_values))]
                                            
                                            # subtract_list = [0]*len(time_range_vector)

                                            # let's extract the initial demand
                                            demand_indices_BASE = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ 'SpecifiedAnnualDemand' ][ 'f' ] ) if x == str( Fleet_Groups_techs_2_dem[ this_set ] ) ]
                                            demand_values_BASE = deepcopy( stable_scenarios[ scenario_list[ s ] ][ 'SpecifiedAnnualDemand' ]['value'][ demand_indices_BASE[0]:demand_indices_BASE[-1]+1 ] )
                                            demand_values_BASE = [ float( demand_values_BASE[j] ) - subtract_list[j] for j in range( len( demand_values_BASE ) ) ]
                                            # let's extract the newly assigned demand
                                            demand_indices_NEW = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ][ 'f' ] ) if x == str( Fleet_Groups_techs_2_dem[ this_set ] ) ]
                                            demand_values_NEW = deepcopy( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ]['value'][ demand_indices_NEW[0]:demand_indices_NEW[-1]+1 ] )
                                            demand_values_NEW = [ float( demand_values_NEW[j] ) - subtract_list[j] for j in range( len( demand_values_NEW ) ) ]
                                            #
                                            this_set_range_indices_max_cap = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMaxCapacity' ][ tsti ] ) if x == str( this_set ) ]
                                            old_max_cap_values = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ this_set_range_indices_max_cap[0]:this_set_range_indices_max_cap[-1]+1 ] )
                                            old_max_cap_values = [ float( old_max_cap_values[j] ) for j in range( len( old_max_cap_values ) ) ]
                                            #
                                            new_max_cap_values = [0 for n in range( len( old_max_cap_values ) )]
                                            for n in range( len( time_list ) ):
                                                if time_list[n] >= Initial_Year_of_Uncertainty:
                                                    new_max_cap_values[n] = 1.01*old_max_cap_values[n]*( ( demand_values_NEW[n] / new_value_list[n] ) / ( demand_values_BASE[n] / value_list[n] ) )
                                                else:
                                                    new_max_cap_values[n] = old_max_cap_values[n]
                                            #
                                            new_max_cap_values_rounded = [ round(elem, 4) for elem in new_max_cap_values ]
                                            inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ this_set_range_indices_max_cap[0]:this_set_range_indices_max_cap[-1]+1 ] = deepcopy( new_max_cap_values_rounded )
                                            #
                                            this_set_range_indices_min_cap = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ][ tsti ] ) if x == str( this_set ) ]
                                            old_min_cap_values = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'][ this_set_range_indices_min_cap[0]:this_set_range_indices_min_cap[-1]+1 ] )
                                            old_min_cap_values = [ float( old_min_cap_values[j] ) for j in range( len( old_min_cap_values ) ) ]
                                            #
                                            new_min_cap_values = [0 for n in range( len( old_min_cap_values ) )]
                                            for n in range( len( time_list ) ):
                                                if time_list[n] >= Initial_Year_of_Uncertainty:
                                                    new_min_cap_values[n] = 0.99*old_min_cap_values[n]*( ( demand_values_NEW[n] / new_value_list[n] ) / ( demand_values_BASE[n] / value_list[n] ) )
                                                else:
                                                    new_min_cap_values[n] = old_min_cap_values[n]
                                            #
                                            new_min_cap_values_rounded = [ round(elem, 4) for elem in new_min_cap_values ]
                                            inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'][ this_set_range_indices_min_cap[0]:this_set_range_indices_min_cap[-1]+1 ] = deepcopy( new_min_cap_values_rounded )
                                            #
                                            if this_set == 'Techs_Auto': # we must adjust motorcycles for demand, as it is not explored for occupancy rate
                                                #
                                                motorcycle_range_indices_max_cap = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMaxCapacity' ][ tsti ] ) if x == str( 'Techs_Motos' ) ]
                                                old_max_cap_values = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ motorcycle_range_indices_max_cap[0]:motorcycle_range_indices_max_cap[-1]+1 ] )
                                                old_max_cap_values = [ float( old_max_cap_values[j] ) for j in range( len( old_max_cap_values ) ) ]
                                                #
                                                new_max_cap_values = [ old_max_cap_values[n]*( demand_values_NEW[n] / demand_values_BASE[n] ) for n in range( len( old_max_cap_values ) ) ]
                                                new_max_cap_values_rounded = [ round(elem, 4) for elem in new_max_cap_values ]
                                                inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ motorcycle_range_indices_max_cap[0]:motorcycle_range_indices_max_cap[-1]+1 ] = deepcopy( new_max_cap_values_rounded )
                                                #
                                                motorcycle_range_indices_min_cap = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ][ tsti ] ) if x == str( 'Techs_Motos' ) ]
                                                old_min_cap_values = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'][ motorcycle_range_indices_min_cap[0]:motorcycle_range_indices_min_cap[-1]+1 ] )
                                                old_min_cap_values = [ float( old_min_cap_values[j] ) for j in range( len( old_min_cap_values ) ) ]
                                                #
                                                new_min_cap_values = [ old_min_cap_values[n]*( demand_values_NEW[n] / demand_values_BASE[n] ) for n in range( len( old_min_cap_values ) ) ]
                                                new_min_cap_values_rounded = [ round(elem, 4) for elem in new_min_cap_values ]
                                                inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'][ motorcycle_range_indices_min_cap[0]:motorcycle_range_indices_min_cap[-1]+1 ] = deepcopy( new_min_cap_values_rounded )

                                                # print('review')
                                                # sys.exit()

                                        #--------------------------------------------------------------------#``
                                        # Assign parameters back: for these subset of uncertainties
                                        inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)

                                    #--------------------------------------------------------------------#
                                    elif this_parameter == 'CapacityFactor':
                                        season_list = ['All']
                                        for season in range( len( season_list ) ):
                                            this_l_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 'l' ] ) if x == str( season_list[season] ) ]
                                            #
                                            this_set_range_indices_useful = intersection(this_set_range_indices, this_l_range_indices)
                                            #
                                            # for each index we extract the time and value in a list:
                                            # extracting time:
                                            time_list = []
                                            for useful_index in range( len( this_set_range_indices_useful ) ):
                                                time_list.append( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices_useful[ useful_index ] ] )
                                            time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                            # extracting value:
                                            value_list = []
                                            for useful_index in range( len( this_set_range_indices_useful ) ):
                                                value_list.append( deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices_useful[ useful_index ] ] ) )
                                            value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                            #--------------------------------------------------------------------#
                                            # now that the value is extracted, we must manipulate the result and assign back
                                            if Explored_Parameter_of_X=='Final_Value': # By design, this must always happen.
                                                new_value_list = deepcopy( interpolation_non_linear_final2( time_list, value_list, float(Values_per_Future[fut_id] ), 2050,Initial_Year_of_Uncertainty) ) 
                                            #--------------------------------------------------------------------#``
                                            new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                            #
                                            # Assign parameters back: for these subset of uncertainties
                                            for useful_index in range( len( this_set_range_indices_useful ) ):
                                                inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices_useful[ useful_index ]  ] = new_value_list_rounded[ useful_index ]

                        elif Math_Type in ['Adoption_Curve', 'Mult_Adoption_Curve'] and ('Electrification' in X_Cat or 'Penetration' in X_Cat):
                            #
                            enter_if_cycle = True
                            #
                            for a_set in range( len( Sets_Involved ) ):
                                tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                #
                                this_set = Sets_Involved[a_set]
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                preliminary_pass = True

                                if len(this_set_range_indices) > 0:
                                    value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                    if value_list[-1] > 98:
                                        preliminary_pass = False

                                if preliminary_pass is False:
                                    print('please review')
                                    sys.exit()

                                if len(this_set_range_indices) == len(time_range_vector) and preliminary_pass is True:
                                    # extracting time:
                                    time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                    #
                                    value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                    value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                    if this_set == 'TRYTKELE':
                                        spec_store_freheaele[this_f] = deepcopy(value_list)

                                    group_tech_set = Fleet_Groups_inv[ this_set ]
                                    group_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( group_tech_set ) ]
                                    group_value_list = inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ group_set_range_indices[0]:group_set_range_indices[-1]+1 ]
                                    group_value_list = [ float( j ) for j in group_value_list ]

                                    group_set_range_indices_st = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ this_parameter ][ tsti ] ) if x == str( group_tech_set ) ]
                                    group_value_list_st = stable_scenarios[ scenario_list[s] ][ this_parameter ]['value'][ group_set_range_indices_st[0]:group_set_range_indices_st[-1]+1 ]
                                    group_value_list_st = [ float( j ) for j in group_value_list_st ]

                                    if Math_Type == 'Adoption_Curve':
                                        #  WE DO NOT NEED TO EXTRACT THE EXACT VALUE:
                                        # now that the value is extracted, we must manipulate the result and assign back
                                        L_index = 0
                                        Q_index = 1
                                        k_index = 2
                                        M_index = 3
                                        #
                                        L = Values_per_Future[fut_id][L_index]
                                        Q = Values_per_Future[fut_id][Q_index]
                                        k = Values_per_Future[fut_id][k_index]
                                        M = Values_per_Future[fut_id][M_index]
                                        #
                                        shift_years = [ n for n in range( Initial_Year_of_Uncertainty,final_year+1 ) ]
                                        shift_year_counter = 0
                                        adoption_share = []
                                        for t in range( len( time_list ) ):
                                            if time_list[t] > Initial_Year_of_Uncertainty:
                                                x = int( shift_years[shift_year_counter] )
                                                adoption_share.append( generalized_logistic_curve(x, L, Q, k, M))
                                                shift_year_counter += 1
                                            else:
                                                adoption_share.append( 0.0 )

                                    elif Math_Type == 'Mult_Adoption_Curve':
                                        value_list_sh = [value_list[i]/val for i, val in enumerate(group_value_list)]
                                        adoption_share = \
                                            interpolation_multiplier(
                                                time_list, value_list_sh,
                                                Values_per_Future[fut_id] )

                                        adoption_share = [min(x, 0.98) for x in adoption_share]
                                        # if 0.98 in adoption_share:
                                        #     print('check this out')
                                        #     sys.exit()

                                        if 'Electrification of Private Transport' == X_Cat and group_tech_set == 'Techs_Auto':
                                            electric_sedan_adoption_sh_orig = \
                                                deepcopy(value_list_sh)
                                            electric_sedan_adoption_sh = \
                                                deepcopy(adoption_share)
                                            # print('Review this please')
                                            # sys.exit()

                                    else:
                                        print('No MathType defined.')
                                        sys.exit()

                                    #
                                    if this_parameter == 'TotalAnnualMaxCapacity':
                                        sec_multiplier = 1.001
                                    elif this_parameter == 'TotalTechnologyAnnualActivityLowerLimit':
                                        sec_multiplier = 0.999
                                    #
                                    new_value_list = []
                                    for n in range( len( time_list ) ):
                                        new_value_list.append( sec_multiplier*group_value_list[n]*adoption_share[n] )
                                    #
                                    # Here we must include the exceptions for hydrgoen for the NDP no to surpass the limit of the group technology:
                                    if this_set in [ 'TRMBSHYD', 'TRBPRHYD', 'TRBPUHYD', 'TRYTKHYD' ]:
                                        # We know Hydrogen only has TotalTechnologyAnnualActivityLowerLimit. We must compare each Hydrogen technology with the corresponding electric technology (previously determined).
                                        if this_set == 'TRMBSHYD':
                                            corresponding_set = 'TRMBSELE'
                                        if this_set == 'TRBPRHYD':
                                            corresponding_set = 'TRBPRELE'
                                        if this_set == 'TRBPUHYD':
                                            corresponding_set = 'TRBPUELE'
                                        if this_set == 'TRYTKHYD':
                                            corresponding_set = 'TRYTKELE'
                                            # print('HAPPENS???')
                                            # sys.exit()
                                        #
                                        
                                        # print('I got here', this_set)
                                        # sys.exit()
                                        
                                        the_group_value_list = deepcopy( group_value_list )
                                        #
                                        the_electric_tech_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 't' ] ) if x == str( corresponding_set ) ]
                                        the_electric_tech_values = inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ the_electric_tech_indices[0]:the_electric_tech_indices[-1]+1 ]
                                        the_electric_tech_values = [ float( the_electric_tech_values[j] ) for j in range( len( the_electric_tech_values ) ) ]
                                        #
                                        new_value_list_fix = [] # Note that 'new_value_list' is for Hydrogen:
                                        for n in range( len( time_list ) ):
                                            if ( new_value_list[n] > (the_group_value_list[n] - the_electric_tech_values[n])*0.98 ) and ( this_parameter == 'TotalTechnologyAnnualActivityLowerLimit' ): # here we must leave the max capacity untouched
                                                new_value_list_fix.append( ( the_group_value_list[n] - the_electric_tech_values[n] )*0.98 )
                                                if int(time_list[n]) == 2050:
                                                    print(fut_id, 'pay attention!')
                                                    # sys.exit()
                                            else:
                                                new_value_list_fix.append( new_value_list[n]*0.999 )  # Maximum of 98%
                                        new_value_list_rounded = [ round(elem, 4) for elem in new_value_list_fix ]
                                        #
                                    else:
                                        new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                    #
                                    inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                    # 
                                    # All the technologies that are not electric, we need to modify
                                    exception_list = ['TRBPUHYD', 'TRYTKHYD'] # this should happen when hydrogen is modified afterwards
                                    special_list = ['']
                                    special_list_dict = {'TRYTKHYD':['TRYTKELE', 'TRYTKHYD']}

                                    # if this_set not in exception_list and this_parameter in ['TotalTechnologyAnnualActivityLowerLimit', 'TotalAnnualMaxCapacity']:
                                    # if this_set not in exception_list and this_parameter in ['TotalTechnologyAnnualActivityLowerLimit']:
                                    if this_set not in exception_list and this_parameter in ['TotalTechnologyAnnualActivityLowerLimit']:

                                        this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ][ 't' ] ) if x == str( 'TRYTKHD') ]
                                        value_list_max = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        value_list_max = [ float(value_list_max[j]) for j in range( len( value_list_max ) ) ]
                                        this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ][ 't' ] ) if x == str( 'TRYTKHD') ]
                                        # value_list_min = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        # value_list_min = [ float(value_list_min[j]) for j in range( len( value_list_min ) ) ]
                                        # diff = [i1 - i2 for i1, i2 in zip(value_list_max, value_list_min)]
                                        # has_negative = any(value < 0 for value in diff)
                                        # print('xxx1', u, Exact_X, f, this_parameter, has_negative, diff)

                                        rem_sets = [i for i in Fleet_Groups[group_tech_set] if i != this_set and 'ELE' not in i and 'HYD' not in i]
                                        # Get sum:
                                        rem_sets_sum = [0]*len(time_range_vector)
                                        for r_set in rem_sets:
                                            r_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(r_set)]
                                            if len(r_set_range_indices) != 0:
                                                print(r_set)
                                                r_value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter ]['value'][r_set_range_indices[0]:r_set_range_indices[-1]+1])
                                                r_value_list = [float(r_value_list[j]) for j in range(len(r_value_list))]
                                                rem_sets_sum = [sum(x) for x in zip(rem_sets_sum, r_value_list)]

                                        if any(x == 0 for x in rem_sets_sum):
                                            rem_sets_sum[-1] = 0.1
                                            # print('print problem')
                                            # sys.exit()

                                        # Now get the complement:
                                        difference_list = [
                                            new_val - val for new_val, val in zip(new_value_list, value_list)]
                                        rem_sets_sum_adj = [
                                            rem_sum - diff for rem_sum, diff in zip(rem_sets_sum, difference_list)]
                                        if 'TRMOTGSL' in rem_sets:
                                            # print(rem_sets)
                                            rem_sets_sum_adj_mult = [1]*len(time_range_vector)
                                        else:
                                            rem_sets_sum_adj_mult = [
                                                rem_sum_adj/rem_sum for rem_sum, rem_sum_adj in zip(rem_sets_sum, rem_sets_sum_adj)]

                                        # if rem_sets_sum[-1]:
                                        #    print('print problem')
                                        #    sys.exit()

                                        # Adjust:
                                        for r_set in rem_sets:
                                            r_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(r_set)]
                                            r_set_range_indices_2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f]['TotalAnnualMaxCapacity'][tsti]) if x == str(r_set)]
                                            if len(r_set_range_indices) != 0:
                                                r_value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter ]['value'][r_set_range_indices[0]:r_set_range_indices[-1]+1])
                                                r_value_list = [float(r_value_list[j]) for j in range(len(r_value_list))]
                                                multer_low = [1]*7 + [0.98]*(len(time_range_vector)-7)
                                                r_value_list_new = [
                                                    a_multer * adj_mult * val for a_multer, adj_mult, val in zip(multer_low, rem_sets_sum_adj_mult, r_value_list)]
                                                inherited_scenarios[scenario_list[s]][f][this_parameter ]['value'][r_set_range_indices[0]:r_set_range_indices[-1]+1] = deepcopy(r_value_list_new)

                                                # We must additionally adjust the TotalAnnualMaxCapacity if it exists, because we want to avoid inconsistencies
                                                if len(r_set_range_indices_2) != 0:
                                                    r_value_list_2 = deepcopy(inherited_scenarios[scenario_list[s]][f]['TotalAnnualMaxCapacity']['value'][r_set_range_indices_2[0]:r_set_range_indices_2[-1]+1])
                                                    if any(r2 > 500 for r2 in [float(value2) for value2 in r_value_list_2]):
                                                        pass
                                                    else:
                                                        multer_max = [1]*7 + [1.02]*(len(time_range_vector)-7)
                                                        r_value_list_new_2 = [
                                                            a_multer * adj_mult * val for a_multer, adj_mult, val in zip(multer_max, rem_sets_sum_adj_mult, r_value_list)]
                                                        if r_set_range_indices_2:
                                                            inherited_scenarios[scenario_list[s]][f]['TotalAnnualMaxCapacity']['value'][r_set_range_indices_2[0]:r_set_range_indices_2[-1]+1] = deepcopy(r_value_list_new_2)

                                        # print('review this')
                                        # sys.exit()

                                        # print('*', rem_sets_sum_adj_mult)
                                        # if 'TRMOTGSL' not in rem_sets:
                                        #    print('**', rem_sets_sum_adj)
                                        #    print('***', rem_sets_sum)

                                        this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ][ 't' ] ) if x == str( 'TRYTKHD') ]
                                        value_list_max = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        value_list_max = [ float(value_list_max[j]) for j in range( len( value_list_max ) ) ]
                                        this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ][ 't' ] ) if x == str( 'TRYTKHD') ]
                                        # value_list_min = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        # value_list_min = [ float(value_list_min[j]) for j in range( len( value_list_min ) ) ]
                                        # diff = [i1 - i2 for i1, i2 in zip(value_list_max, value_list_min)]
                                        # has_negative = any(value < 0 for value in diff)
                                        # print('xxx2',  u, Exact_X, f, this_parameter, has_negative, diff)
                                        # if has_negative:
                                        #    print('Alert!')
                                        #    sys.exit()

                                    if this_set in special_list:
                                        non_rem_sets = special_list_dict[this_set]
                                        non_rem_sets_comp = [i for i in non_rem_sets if i != this_set]
                                        rem_sets = [i for i in Fleet_Groups[group_tech_set] if i not in non_rem_sets]
                                        # Get sum:
                                        rem_sets_sum = [0]*len(time_range_vector)
                                        for r_set in rem_sets:
                                            r_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(r_set)]
                                            if len(r_set_range_indices) > 0:
                                                r_value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter ]['value'][r_set_range_indices[0]:r_set_range_indices[-1]+1])
                                                r_value_list = [float(r_value_list[j]) for j in range(len(r_value_list))]
                                                rem_sets_sum = [sum(x) for x in zip(rem_sets_sum, r_value_list)]
                                        # Now get the complement:
                                        value_list_sum = [sum(x) for x in zip(value_list, spec_store_freheaele[this_f])]
                                        new_value_list_sum = deepcopy(new_value_list)
                                        for spec_set in non_rem_sets_comp:
                                            spec_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(spec_set)]
                                            spec_value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter ]['value'][spec_set_range_indices[0]:spec_set_range_indices[-1]+1])
                                            spec_value_list = [float(spec_value_list[j]) for j in range(len(spec_value_list))]
                                            new_value_list_sum = [sum(x) for x in zip(new_value_list_sum, spec_value_list)]

                                        difference_list = [
                                            new_val - val for new_val, val in zip(new_value_list_sum, value_list_sum)]
                                        rem_sets_sum_adj = [
                                            rem_sum - diff for rem_sum, diff in zip(rem_sets_sum, difference_list)]
                                        rem_sets_sum_adj_mult = [
                                            rem_sum_adj/rem_sum for rem_sum, rem_sum_adj in zip(rem_sets_sum, rem_sets_sum_adj)]
                                        # Adjust:
                                        for r_set in rem_sets:
                                            r_set_range_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter][tsti]) if x == str(r_set)]
                                            if len(r_set_range_indices) > 0:
                                                r_value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter ]['value'][r_set_range_indices[0]:r_set_range_indices[-1]+1])
                                                r_value_list = [float(r_value_list[j]) for j in range(len(r_value_list))]
                                                r_value_list_new = [
                                                    adj_mult*val for adj_mult, val in zip(rem_sets_sum_adj_mult, r_value_list)]
                                                inherited_scenarios[scenario_list[s]][f][this_parameter ]['value'][r_set_range_indices[0]:r_set_range_indices[-1]+1] = deepcopy(r_value_list_new)

                                        # if this_parameter == 'TotalTechnologyAnnualActivityLowerLimit':
                                        #    print('review this')
                                        #    sys.exit()
                                    #-----------------------------------------------------------------------#
                                #
                            #
                        elif 'Distance' in X_Cat: # This is the last adjustment

                            enter_if_cycle = True

                            if p == 0:
                                dem_adj_public = True
                                dem_adj_private = True
                                dem_adj_heafre = True
                                dem_adj_midfre = True
                                dem_adj_ligfre = True

                            for a_set in range( len( Sets_Involved ) ):
                                # Distance is a parameter that is not in Osemosys directly, but is implicit in multiple parameters.
                                # Now, we proceed to estimate the change in the curve of distance across futures. Note that this modification does not depend on the baseline values.
                                #
                                tsti = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                #
                                this_set = Sets_Involved[a_set] # these are GROUP TECHS, please do not forget
                                #
                                base_distance = Fleet_Groups_Distance[this_set]

                                new_distance = deepcopy( interpolation_non_linear_final2( time_range_vector, base_distance, float(Values_per_Future[fut_id] ), 2050,Initial_Year_of_Uncertainty) )
                                reference_driven_distance[ scenario_list[s] ][f].update( {this_set:new_distance} )

                                this_demand_set = Fleet_Groups_techs_2_dem[ Sets_Involved[ a_set ] ]
                                if ((this_demand_set == 'E6TDPASPRI' and dem_adj_private is True) or
                                    (this_demand_set == 'E6TDPASPUB' and dem_adj_public is True) or
                                    (this_demand_set == 'E6TDFREHEA' and dem_adj_heafre is True) or
                                    (this_demand_set == 'DEMTRNFREMED' and dem_adj_midfre is True) or
                                    (this_demand_set == 'E6TDFRELIG' and dem_adj_ligfre is True)):

                                    # let's extract rail capacity to adjust this apropiately
                                    train_pass_capacity_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMaxCapacity' ][ 't' ] ) if x == str( 'Techs_Trains' ) ]
                                    train_pass_capacity_values = inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ train_pass_capacity_indices[0]:train_pass_capacity_indices[-1]+1 ]
                                    if Fleet_Groups_techs_2_dem[ Sets_Involved[ a_set ] ] == 'E6TDPASPUB' and scenario_list[ s ] == 'LTS':
                                        subtract_list = [float(train_pass_capacity_values[j]) for j in range(len(train_pass_capacity_values))]
                                    else:
                                        subtract_list = [0 for j in range(len(train_pass_capacity_values))]

                                    # subtract_list = [0]*len(time_range_vector)

                                    demand_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ][ 'f' ] ) if x == str( this_demand_set ) ]
                                    demand_list_str = deepcopy( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ]['value'][ demand_indices[0]:demand_indices[-1]+1 ] )
                                    demand_list = [float(val) for val in demand_list_str]
                                    #
                                    new_value_list = []
                                    for n in range( len( value_list ) ):
                                        if n < index_2024:
                                            new_value_list.append( demand_list[n] )
                                        else:
                                            new_value_list.append( (demand_list[n]-subtract_list[n])*new_distance[n]/base_distance[n] )
                                            new_value_list[-1] += subtract_list[n]
                                    new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                    #
                                    inherited_scenarios[ scenario_list[s] ][ f ][ 'SpecifiedAnnualDemand' ]['value'][ demand_indices[0]:demand_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                    #                                       
                                    if this_demand_set == 'E6TDPASPRI':
                                        demand_indices = [ i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f]['SpecifiedAnnualDemand']['f']) if x == str('E6TRNOMOT')]
                                        demand_list = [float(val) for val in inherited_scenarios[scenario_list[s]][f]['SpecifiedAnnualDemand']['value'][demand_indices[0]:demand_indices[-1]+1]]
                                        #
                                        new_value_list = []
                                        for n in range( len( value_list ) ):
                                            if n < index_2024:
                                                new_value_list.append( demand_list[n] )
                                            else:
                                                new_value_list.append( demand_list[n]*new_distance[n]/base_distance[n] )
                                        new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                        #
                                        inherited_scenarios[ scenario_list[s] ][ f ][ 'SpecifiedAnnualDemand' ]['value'][ demand_indices[0]:demand_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                        dem_adj_private = False
                                        #
                                    if this_demand_set == 'E6TDPASPUB':
                                        dem_adj_public = False
                                        #
                                    if this_demand_set == 'E6TDFREHEA':
                                        dem_adj_heafre = False
                                        #
                                    if this_demand_set == 'DEMTRNFREMED':
                                        dem_adj_midfre = False
                                        #
                                    if this_demand_set == 'E6TDFRELIG':
                                        dem_adj_ligfre = False

                                if (this_set in trn_list and this_parameter in ['TotalAnnualMaxCapacity', 'TotalTechnologyAnnualActivityLowerLimit'] ): # THIS CONDITION WILL ALWAYS BE TRUE
                                    #
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( this_set ) ]
                                    #
                                    if len(this_set_range_indices) != 0:
                                        # The obtained distance change is used appropiately from here on (...)
                                        # We must proceed with the group set IF the parameter is adequate:
                                        value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                        value_list = [ float(value_list[j]) for j in range( len(value_list) ) ]
                                        #
                                        new_value_list = []
                                        for n in range( len( value_list ) ):
                                            if n < index_2024:
                                                new_value_list.append( value_list[n] )
                                            else:
                                                new_value_list.append( value_list[n]*new_distance[n]/base_distance[n] )
                                        #
                                        if this_parameter == 'TotalAnnualMaxCapacity' and this_set in ['Techs_Buses_Pri', 'Techs_Buses_Pub', 'Techs_Buses_Micro', 'Techs_Trains']:
                                            new_value_list_rounded = [ round(elem*1.02, 4) for elem in new_value_list ]
                                        else:
                                            new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                        inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy( new_value_list_rounded )

                                        '''
                                        if this_set == 'Techs_He_Freight' and scenario_list[s] != 'BAU':  # here we need to adjust the capacity of freight rail for consistency
                                            tsri_frerail = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ tsti ] ) if x == str( 'Techs_Trains_Freight' ) ]
                                            value_list_frerail = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ tsri_frerail[0]:tsri_frerail[-1]+1 ] )
                                            value_list_frerail = [ float(value_list_frerail[j]) for j in range( len(value_list_frerail) ) ]
                                            #
                                            new_value_list_frerail = []
                                            for n in range( len( value_list_frerail ) ):
                                                new_value_list_frerail.append( value_list_frerail[n]*new_distance[n]/base_distance[n] )
                                            #
                                            new_value_list_frerail_rounded = [ round(elem, 4) for elem in new_value_list_frerail ]
                                            inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ]['value'][ tsri_frerail[0]:tsri_frerail[-1]+1 ] = deepcopy( new_value_list_frerail_rounded )
                                        '''

                                # Me must act upon the parameters that get affected by the distance change. We must the read the scenario and extract a list of the technologies that require the change.
                                go_to_file = all_dataset_address + scenario_list[s] + '/' + this_parameter + '.csv'
                                df_getter = pd.read_csv( go_to_file )
                                # We first need to obtain the sets that are affected, i.e. new technologies considering the shift effect of residual technologies:
                                get_tech_list_raw_raw = df_getter.loc[ df_getter['YEAR'] == initial_year ]
                                get_tech_list_raw = list( get_tech_list_raw_raw['TECHNOLOGY'] ) # this has the technologies with a given restriction
                                #
                                applicable_transport_techs = Fleet_Groups[ this_set ]
                                this_transport_techs = []
                                #
                                for n in range( len( get_tech_list_raw ) ):
                                    if get_tech_list_raw[n] in applicable_transport_techs:
                                        this_transport_techs.append( get_tech_list_raw[n] )
                                #
                                # now we must iterate and check whether the values are adjustable;
                                # adjustable means that the values are not 99999 for TotalAnnualMaxCapacity for techs
                                for n in range( len( this_transport_techs ) ):
                                    proceed_with_adjustment = True
                                    if this_parameter == 'TotalAnnualMaxCapacity':
                                        the_2050_value_raw = df_getter.loc[ ( df_getter['TECHNOLOGY'].str.contains( this_transport_techs[n] ) ) & (df_getter['YEAR'] == final_year ) ]
                                        the_2050_value = float( "{0:.3f}".format( the_2050_value_raw['Value'].iloc[0] ) )
                                        if the_2050_value >= 99:
                                            proceed_with_adjustment = False
                                    #
                                    if proceed_with_adjustment == True:
                                        #
                                        adjust_cap_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 't' ] ) if x == str( this_transport_techs[n] ) ]
                                        adjustment_values = deepcopy( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ]['value'][ adjust_cap_indices[0]:adjust_cap_indices[-1]+1 ] )
                                        adjustment_values = [ float( adjustment_values[j] ) for j in range( len( adjustment_values ) ) ]
                                        #--#
                                        # now we perform the adjustment for 02 techs:
                                        adjustment_values_new = []
                                        for z in range( len( adjustment_values ) ):
                                            adjustment_values_new.append( adjustment_values[z]*( new_distance[z]/base_distance[z] ) )
                                        #
                                        adjustment_values_new_rounded = [ round(elem, 4) for elem in adjustment_values_new ]
                                        inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ]['value'][ adjust_cap_indices[0]:adjust_cap_indices[-1]+1 ] = deepcopy( adjustment_values_new_rounded )

                            # !!! Here we override max cap to prevent infeasibilities
                            # At this point we need to see if total annual max capacity factors have a negative rate at some point, in whcih case we would need to correct the trajectory.
                            # Get all the technologies that belong to the max cap
                            if this_parameter == 'TotalAnnualMaxCapacity':
                                max_cap_t_all = inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalAnnualMaxCapacity' ]['t']
                                max_cap_groups = [i for i in max_cap_t_all if 'Techs' in i or 'TR' in i]
                                for mcg in max_cap_groups:
                                    adjust_cap_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 't' ] ) if x == mcg ]
                                    adjustment_values = deepcopy( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ]['value'][ adjust_cap_indices[0]:adjust_cap_indices[-1]+1 ] )
                                    adjustment_values = [ float( adjustment_values[j] ) for j in range( len( adjustment_values ) ) ]
                                    adjusted_values = deepcopy(adjustment_values)

                                    # Initialize the last non-decreasing value with the first element of the list
                                    last_non_decreasing_value = adjusted_values[0]

                                    # Iterate through the list starting from the second element
                                    for i in range(1, len(adjusted_values)):
                                        # If the current element is less than the last non-decreasing value,
                                        # update it to the last non-decreasing value
                                        if adjusted_values[i] < last_non_decreasing_value:
                                            adjusted_values[i] = last_non_decreasing_value
                                        else:
                                            # Otherwise, update the last non-decreasing value to the current element
                                            last_non_decreasing_value = adjusted_values[i]

                                    inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ]['value'][ adjust_cap_indices[0]:adjust_cap_indices[-1]+1 ] = deepcopy(adjusted_values)

                                    # if scenario_list[ s ] == 'LTS' and 'Motos' in mcg:
                                    #    print('review 2')
                                    #    sys.exit()

                        # Also check that things entered.
                        if check_assignation:
                            print('    ', u, X_Cat, Parameters_Involved[p], enter_if_cycle)

                if 'Adjustment OAR' in X_Cat: # right after maximum vehicle capacity, for all scenarios, to include the changes in OutputActivityRatio
                    ####### USE THIS LINE FOR AUTOMATIC ADJUSTMENT // BY DESIGN THIS CAN BE DONE AFTER MAXIMUM VEHICLE CAPACITY HAS BEEN MANIPULATED #######
                    # %% WE CAN TAKE ADVANTAGE HERE AND ADJUST ALL GROUP TECHS FOR COHERENCE %%
                    #
                    enter_if_cycle = True

                    # ADD AN EXCEPTION LIST BELOW TO SHOW THE GROUPS THAT SHOULD NOT BE ADJUSTED TO AVOID DOUBLING THE WORK:
                    except_techs = ['Techs_Auto', 'Techs_Motos', 'Techs_Buses_Pri', 'Techs_Buses_Pub', 'Techs_Buses_Micro', 'Techs_Telef', 'Techs_Trains', 'Techs_Trains_Freight']
                    except_scen = ['LTS']
                    #
                    params_to_adjust = [ 'TotalAnnualMaxCapacity', 'TotalTechnologyAnnualActivityLowerLimit' ]
                    for par in range( len( params_to_adjust ) ):
                        for a_set in range( len( Sets_Involved ) ):
                            #
                            this_set = Sets_Involved[ a_set ]
                            if this_set in except_techs and scenario_list[ s ] in except_scen:  # except, pass
                                #print(Sets_Involved[ a_set ])
                                pass
                            else:
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ params_to_adjust[par] ][ 't' ] ) if x == this_set]
                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ params_to_adjust[par] ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #
                                demand_indices_BASE = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ 'SpecifiedAnnualDemand' ][ 'f' ] ) if x == Fleet_Groups_techs_2_dem[this_set]]
                                demand_list_BASE = deepcopy( stable_scenarios[ scenario_list[ s ] ][ 'SpecifiedAnnualDemand' ]['value'][ demand_indices_BASE[0]:demand_indices_BASE[-1]+1 ] )
                                demand_list_BASE = [ float(demand_list_BASE[j]) for j in range(len(demand_list_BASE)) ]
                                #
                                demand_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ][ 'f' ] ) if x == Fleet_Groups_techs_2_dem[this_set]]
                                demand_list = deepcopy( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'SpecifiedAnnualDemand' ]['value'][ demand_indices[0]:demand_indices[-1]+1 ] )
                                demand_list = [ float(demand_list[j]) for j in range(len(demand_list)) ]
                                #
                                new_value_list_old_base = deepcopy( value_list )
                                new_value_list = [ new_value_list_old_base[n]*(demand_list[n]/demand_list_BASE[n]) for n in range( len( new_value_list_old_base ) )]
                                new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                #
                                inherited_scenarios[ scenario_list[s] ][ f ][ params_to_adjust[par] ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)

                    # -.-.-.-.-.-.-.-.-.--.-.-.-.-.-.-.-.-.-.--.-.-.-.-.-.-.-.-.-.-.- #
                    # Go with TotalAnnualMaxCapacity and TotalTechnologyAnnualActivityLowerLimit changes:
                    for par in range( len( params_to_adjust ) ):
                        #
                        if params_to_adjust[par] == 'TotalAnnualMaxCapacity':
                            security_multiplier_factor = 1.001
                        elif params_to_adjust[par] == 'ResidualCapacity':
                            security_multiplier_factor = 1
                        elif params_to_adjust[par] == 'TotalTechnologyAnnualActivityLowerLimit':
                            security_multiplier_factor = 0.999

                        ##############################################################################################################################
                        #
                        go_to_file = all_dataset_address + '/' + scenario_list[s] + '/' + params_to_adjust[par] + '.csv'
                        df_getter = pd.read_csv( go_to_file )
                        # We first need to obtain the sets that are affected, i.e. new technologies considering the shift effect of residual technologies:
                        get_tech_list_raw_raw = df_getter.loc[ df_getter['YEAR'] == final_year ]
                        get_tech_list_raw = list( get_tech_list_raw_raw['TECHNOLOGY'] )
                        #
                        applicable_transport_techs = list( Fleet_Groups_inv.keys() )
                        this_transport_techs = []
                        #
                        for n in range( len( get_tech_list_raw ) ):
                            if get_tech_list_raw[n] in applicable_transport_techs:
                                this_transport_techs.append( get_tech_list_raw[n] )
                        #
                        for n in range( len( this_transport_techs ) ):
                            proceed_with_adjustment = True
                            if params_to_adjust[par] == 'TotalAnnualMaxCapacity':
                                the_2050_value_raw = df_getter.loc[ ( df_getter['TECHNOLOGY'].str.contains( this_transport_techs[n] ) ) & (df_getter['YEAR'] == final_year ) ]
                                the_2050_value = float( "{0:.3f}".format( the_2050_value_raw['Value'].iloc[0] ) )
                                if the_2050_value >= 99 or this_transport_techs[n] in ['TRXTRAIELE']:
                                    proceed_with_adjustment = False
                            #
                            if proceed_with_adjustment is True:
                                #
                                adjust_cap_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ params_to_adjust[par] ][ 't' ] ) if x == str( this_transport_techs[n] ) ]
                                adjust_cap_values = deepcopy( inherited_scenarios[ scenario_list[ s ] ][ f ][ params_to_adjust[par] ]['value'][ adjust_cap_indices[0]:adjust_cap_indices[-1]+1 ] )
                                adjust_cap_values = [ float( adjust_cap_values[j] ) for j in range( len( adjust_cap_values ) ) ]
                                #
                                this_group_tech = Fleet_Groups_inv[ this_transport_techs[n] ]
                                # here we obtain the magnitude that must be considered for the adjustment
                                capacity_indices_BASE = [ i for i, x in enumerate( stable_scenarios[ scenario_list[ s ] ][ params_to_adjust[par] ][ 't' ] ) if x == str( this_group_tech ) ]
                                capacity_values_BASE = deepcopy( stable_scenarios[ scenario_list[ s ] ][ params_to_adjust[par] ]['value'][ capacity_indices_BASE[0]:capacity_indices_BASE[-1]+1 ] )
                                capacity_values_BASE = [ float( capacity_values_BASE[j] ) for j in range( len( capacity_values_BASE ) ) ]
                                #
                                capacity_indices_NEW = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ params_to_adjust[par] ][ 't' ] ) if x == str( this_group_tech ) ]
                                capacity_values_NEW = deepcopy( inherited_scenarios[ scenario_list[ s ] ][ f ][ params_to_adjust[par] ]['value'][ capacity_indices_NEW[0]:capacity_indices_NEW[-1]+1 ] )
                                capacity_values_NEW = [ float( capacity_values_NEW[j] ) for j in range( len( capacity_values_NEW ) ) ]
                                #
                                # we are now prepared to estimate the new values
                                adjust_cap_values_new = []
                                for z in range( len( adjust_cap_values ) ):
                                    if time_range_vector[z] > Initial_Year_of_Uncertainty:
                                        adjust_cap_values_new.append( security_multiplier_factor*adjust_cap_values[z]*( capacity_values_NEW[z]/capacity_values_BASE[z] ) )
                                    else:
                                        adjust_cap_values_new.append( adjust_cap_values[z])
                                #
                                adjust_cap_values_new_rounded = [ round(elem, 4) for elem in adjust_cap_values_new ]
                                inherited_scenarios[ scenario_list[ s ] ][ f ][ params_to_adjust[par] ]['value'][ adjust_cap_indices[0]:adjust_cap_indices[-1]+1 ] = deepcopy( adjust_cap_values_new_rounded )
                                #
                            #
                        #
                    #

                    params_to_adjust = [ 'TotalAnnualMaxCapacity']
                    for par in range( len( params_to_adjust ) ):
                        for a_set in range( len( Sets_Involved ) ):
                            #
                            this_set = Sets_Involved[ a_set ]
                           
                            if this_set in ['Techs_Buses_Pri', 'Techs_Buses_Pub', 'Techs_Buses_Micro', 'Techs_Trains']:  # except, pass
                                this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ params_to_adjust[par] ][ 't' ] ) if x == this_set]
                                value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ params_to_adjust[par] ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #
                                if par == 'TotalAnnualMaxCapacity':
                                    mult_public_adj = 1.02
                                else:
                                    mult_public_adj = 1
                                #
                                new_value_list = [ mult_public_adj*value_list[n] for n in range( len( value_list ) )]
                                new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                #
                                inherited_scenarios[ scenario_list[s] ][ f ][ params_to_adjust[par] ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                    

                    #--------------------------------------------------------------------#

                # if 'LTS' == scenario_list[s] and u > 13:
                #     this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ][ 't' ] ) if x == str( 'TRYTKHD') ]
                #     value_list_max = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalAnnualMaxCapacity' ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                #     value_list_max = [ float(value_list_max[j]) for j in range( len( value_list_max ) ) ]
                #     # this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ][ 't' ] ) if x == str( 'TRYTKHD') ]
                #     # value_list_min = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                #     # value_list_min = [ float(value_list_min[j]) for j in range( len( value_list_min ) ) ]
                #     # diff = [i1 - i2 for i1, i2 in zip(value_list_max, value_list_min)]
                #     # has_negative = any(value < 0 for value in diff)
                #     # print('!!!!',  u, Exact_X, f, has_negative)

                # if check_assignation:
                #     print(u, X_Cat, enter_if_cycle)                

            fut_id += 1
    
    #
    print( '    We have finished the experiment and inheritance' )
    #
    
    
    time_list = []
    #
    scenario_list_print = scenario_list
    # scenario_list_print = ['LTS']

    # We must export useful GDP data for denominator:
    gdp_dict = experiment_dictionary[1]
    gdp_growth_values = gdp_dict['Values'] # start to apply in 2024

    applicable_years = time_range_vector[index_2024+1:]

    gdp_dict_export = {}
    gdp_dict_export.update( { 0:deepcopy( list_gdp_ref ) } )
    for n in range( 1, len( gdp_growth_values )+1 ):
        this_gdp_list = deepcopy( list_gdp_ref )
        this_growth = gdp_growth_values[n-1]
        for y in applicable_years:
            index_this_year = time_range_vector.index( y )
            index_prev_year = time_range_vector.index( y-1 )

            this_gdp_list[ index_this_year ] = this_gdp_list[ index_prev_year ] * ( 1 + this_growth / 100 )
            gdp_dict_export.update( { n:deepcopy( this_gdp_list ) } )

    with open( 'GDP_dict.pickle', 'wb') as handle:
        pickle.dump( gdp_dict_export, handle, protocol=pickle.HIGHEST_PROTOCOL)
    handle.close()
    
    print('##########################')
    print('##########################')
    #print(reference_driven_distance)
    #print(Fleet_Groups_inv)
    print('##########################')
    print('##########################')
    #sys.exit()
    with open( 'reference_driven_distance.pickle', 'wb') as handle:
        pickle.dump( reference_driven_distance, handle, protocol=pickle.HIGHEST_PROTOCOL)
    handle.close()

    with open( 'reference_occupancy_rate.pickle', 'wb') as handle:
        pickle.dump( reference_occupancy_rate, handle, protocol=pickle.HIGHEST_PROTOCOL)
    handle.close()

    # Before printing the experiment dictionary, be sure to add future 0:
    experiment_dictionary[1]['Futures'] = [0] + experiment_dictionary[1]['Futures']
    experiment_dictionary[1]['Values'] = [3] + experiment_dictionary[1]['Values']  # 3% GDP growth is the basics

    with open('experiment_dictionary.pickle', 'wb') as handle:
        pickle.dump(experiment_dictionary, handle, protocol=pickle.HIGHEST_PROTOCOL)
    handle.close()

    # '''
    # print('brake this already processed')
    #sys.exit()
    # '''
    if generator_or_executor == 'Generator' or generator_or_executor == 'Both':
        #
        print('4: We will now print the input .txt files of diverse future scenarios.')
        #
        print_adress = './Experimental_Platform/Futures/'
        packaged_useful_elements = [scenario_list_print, S_DICT_sets_structure, S_DICT_params_structure,
                                    list_param_default_value_params, list_param_default_value_value,
                                    print_adress, all_futures, reference_driven_distance,
                                    Fleet_Groups_inv, time_range_vector ]
        #
        if parallel_or_linear == 'Parallel':
            print('Entered Parallelization')
            #
            x = len(all_futures)*len(scenario_list_print)
            # max_x_per_iter = int( setup_table.loc[ 0 ,'Parallel_Use'] ) # FLAG: This is an input
            max_x_per_iter = int( setup_table.loc[ 0 ,'Parallel_Use'] )
            y = x / max_x_per_iter
            y_ceil = math.ceil( y )

            #'''
            for n in range(0,y_ceil):
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
                    #
                    if scenario_list_print[scen] == 'LTS' or scenario_list_print[scen] == 'BAU':
                        p = mp.Process(target=function_C_mathprog_parallel, args=(n2,inherited_scenarios,packaged_useful_elements,) )
                        processes.append(p)
                        p.start()
                    else:
                        print('!!! At generation, we skip: future ', fut, ' and scenario ', scenario_list[scen], ' !!!' )

                    # p = mp.Process(target=function_C_mathprog_parallel, args=(n2,inherited_scenarios,packaged_useful_elements,) )
                    # processes.append(p)
                    # p.start()
            
                for process in processes:
                    process.join()
                end_1 = time.time()
                time_elapsed_1 = -start1 + end_1
                print( str( time_elapsed_1 ) + ' seconds' )
                time_list.append( time_elapsed_1 )
                #
            print('   The total time producing the input .txt files has been:' + str( sum( time_list ) ) + ' seconds')
            #'''
        '''
        ##########################################################################
        '''
        if parallel_or_linear == 'Linear':
            print('Started Linear Runs')
            #
            x = len(all_futures)*len(scenario_list_print)
            for n in range( x ):
                function_C_mathprog_parallel(n,inherited_scenarios,packaged_useful_elements)
        '''
        ##########################################################################
        '''
        #
    #
    #########################################################################################
    #
    if generator_or_executor == 'Executor' or generator_or_executor == 'Both':
        #
        print('5: We will produce the outputs and store the data.')
        #
        for a_scen in range( len( scenario_list_print ) ):
            #
            # packaged_useful_elements = [ specific_tech_to_group_tech, prefix_list, group_tech_ALL, BAU_reference_driven_distance, NDP_reference_driven_distance, NDP_A_reference_driven_distance, OP15C_reference_driven_distance, BAU_reference_occupancy_rate, NDP_reference_occupancy_rate, NDP_A_reference_occupancy_rate, OP15C_reference_occupancy_rate ]
            packaged_useful_elements = [reference_driven_distance, reference_occupancy_rate, Fleet_Groups_inv, time_range_vector, gdp_dict_export]
            #
            Executed_Scenario = scenario_list_print[ a_scen ]
            set_first_list(Executed_Scenario)
            #
            x = len(first_list)
            #
            max_x_per_iter = int( setup_table.loc[ 0 ,'Parallel_Use'] ) # FLAG: This is an input.
            # max_x_per_iter = 20
            #
            y = x / max_x_per_iter
            y_ceil = math.ceil( y )
            #
            # sys.exit()
            #'''
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
                    print(n2)
                    p = mp.Process(target=main_executer, args=(n2,Executed_Scenario,packaged_useful_elements,discount_year,discount_rate) )
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
                #'''
                #
            #
        #
    #
    print('   The total time producing outputs and storing data has been: ' + str( sum( time_list ) ) + ' seconds')
    '''
    ##########################################################################
    '''
    #
    #######################################################################################
    #
    print( 'For all effects, this has been the end. It all took: ' + str( sum( time_list ) ) + ' seconds')