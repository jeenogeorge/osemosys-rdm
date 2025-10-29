# -*- coding: utf-8 -*-
"""
@author: luisf
"""

import Auxiliares as AUX
import multiprocessing as mp
import pandas as pd
import numpy as np
import os, os.path, errno, sys
import math, time
from copy import deepcopy
import re, linecache, gc, csv, scipy, shutil#, pickle
from pyDOE import * # SOURCE: https://pypi.org/project/lhsmdu/. https://pythonhosted.org/pyDOE/randomized.html#latin-hypercube

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


def data_processor( case, Executed_Scenario, time_range_vector, year_disc, rate_disc):
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
            output_csv_r = rate_disc*100
            output_csv_year = int(year_disc)
            #
            if this_combination[2] in ['RM', 'FERT_ORG', 'salud_residuos', 'contam_agua', 'turismo_residuos','water_reuse'] and this_variable == 'AnnualTechnologyEmissionPenaltyByEmission':
                ref_index = combination_list.index( this_combination )
                this_data_row = deepcopy( data_row_list[ ref_index ] ) # this must be updated in a further position of the list
                #
                ref_var_position_index = output_header.index( 'AnnualTechnologyEmissionPenaltyByEmission' )
                new_var_position_index = output_header.index( 'Externalities'+str(output_csv_year) )
                new2_var_position_index = output_header.index( 'Externalities_GDP' )
                #
                this_year = this_combination[4]
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = np.nan
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
                this_data_row[new2_var_position_index] = np.nan
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
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = np.nan
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
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = np.nan 
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
                #
                resulting_value_raw = float(this_data_row[ ref_var_position_index ]) / ( ( 1 + output_csv_r/100 )**( float(this_year) - output_csv_year ) )
                resulting_value = round( resulting_value_raw, 4)
                #
                this_data_row[new_var_position_index] = str( resulting_value )
                this_data_row[new2_var_position_index] = np.nan
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
def main_executer(n1, Executed_Scenario, time_range_vector, year_disc, rate_disc):
    print('# ' + str(n1+1) + ' of ' + Executed_Scenario )
    set_first_list( Executed_Scenario )
    file_aboslute_address = os.path.abspath("experiment_manager.py")
    file_adress = re.escape( file_aboslute_address.replace( 'experiment_manager.py', '' ) ).replace( '\:', ':' )
    #
    case_address = file_adress + r'Experimental_Platform\\Futures\\' + Executed_Scenario + '\\' + str( first_list[n1] )
    #
    this_case = [ e for e in os.listdir( case_address ) if '.txt' in e ]
    #
    str1 = "start /B start cmd.exe @cmd /k cd " + file_adress
    #
    data_file = case_address.replace('./','').replace('/','\\') + '\\' + str( this_case[0] )
    output_file = case_address.replace('./','').replace('/','\\') + '\\' + str( this_case[0] ).replace('.txt','') + '_output' + '.txt'
    #
    str2 = "glpsol -m OSeMOSYS_Model.txt -d " + str( data_file )  +  " -o " + str(output_file) + " --nopresol"
    os.system( str1 and str2 )
    
    #########################
    #####
    #########################
    # str_start = "start cmd.exe /k cd " + file_adress
    # output_file = case_address.replace('./','').replace('/','\\') + '\\' + str( this_case[0] ).replace('.txt','') + '_output'
    
    # str_solve = 'glpsol -m OSeMOSYS_Model.txt -d ' + str( data_file ) + ' --wglp ' + output_file + '.glp --write ' + output_file + '.sol'
    # os.system( str_start and str_solve)
    #########################
    #########################
    
    time.sleep(1)
    #
    data_processor(n1,Executed_Scenario, time_range_vector, year_disc, rate_disc)
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
                        last_set_element = this_scenario_data[ this_param ][ this_param_keys[-1] ] 
                        last_set_element_unique = [] # list( set( last_set_element ) )
                        for u in range( len( last_set_element ) ):
                            if last_set_element[u] not in last_set_element_unique:
                                last_set_element_unique.append( last_set_element[u] )
                        #
                        for y in range( len( last_set_element_unique ) ):
                            g.write( str( last_set_element_unique[y] ) + ' ')
                        g.write(':=\n')
                        #
                        second_last_set_element = this_scenario_data[ this_param ][ this_param_keys[-2] ]
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
                            these_values = []
                            for val in range( len( value_indices ) ):
                                these_values.append( this_scenario_data[ this_param ]['value'][ value_indices[val] ] )
                            for val in range( len( these_values ) ):
                                g.write( str( these_values[val] ) + ' ' )
                            g.write('\n') #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
            #%%%
            if len(this_param_keys) == 5:
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
            #-----------------------------------------#
            g.write( ';\n\n' )
    #
    # remember the default values for printing:
    g.write('param AccumulatedAnnualDemand default 0 :=\n;\n')
    # if scenario_list[scen] == 'BAU':
    #     g.write('param AnnualEmissionLimit default 99999 :=\n;\n')
    g.write('param AnnualEmissionLimit default 99999 :=\n;\n') # here we are using no Emission Limit
    g.write('param AnnualExogenousEmission default 0 :=\n;\n')
    #g.write('param TotalAnnualMaxCapacity default 99999 :=\n;\n')
    g.write('param TotalAnnualMinCapacity default 0 :=\n;\n')
    g.write('param CapacityOfOneTechnologyUnit default 0 :=\n;\n')
    # g.write('param FixedCost default 0 :=\n;\n')
    # g.write('param CapitalCost default 0 :=\n;\n')
    g.write('param CapitalCostStorage default 0 :=\n;\n')
    # g.write('param ResidualCapacity default 0 :=\n;\n')
    # g.write('param CapacityFactor default 0 :=\n;\n')
    # g.write('param AvailabilityFactor default 0 :=\n;\n')
    # g.write('param CapacityToActivityUnit default 1 :=\n;\n')
    g.write('param Conversionld default 0 :=\n;\n')
    g.write('param Conversionlh default 0 :=\n;\n')
    g.write('param Conversionls default 0 :=\n;\n')
    g.write('param DaySplit default 0.00137 :=\n;\n')
    g.write('param DaysInDayType default 7 :=\n;\n')
    g.write('param DepreciationMethod default 1 :=\n;\n')
    g.write('param DiscountRate default 0.08 :=\n;\n')
    # g.write('param EmissionsPenalty default 0 :=\n;\n')
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
    #g.write('param TotalAnnualMinCapacityInvestment default 0 :=\n;\n')
    # if scenario_list[scen] == 'BAU':
    #     g.write('param TotalAnnualMinCapacity default 0 :=\n;\n')
    #g.write('param TotalTechnologyAnnualActivityUpperLimit default 99999 :=\n;\n')
    g.write('param TotalTechnologyModelPeriodActivityLowerLimit default 0 :=\n;\n')
    g.write('param TotalTechnologyModelPeriodActivityUpperLimit default 99999 :=\n;\n')
    g.write('param TradeRoute default 0 :=\n;\n')
    # g.write('param SpecifiedDemandProfile default 1 :=\n;\n')
    g.write('#\n' + 'end;\n')
    g.close()

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
            this_combination_str = str(1) + strcode
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
            #################################################################################################################
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
'''
Function 3: Notes
a) There is a shift of the time series for some uncertainties, reflecting uncertainty in the initial value. For this reason, we provide al alternative function to adjust the curve.
b) There is a dc shift that changes all values in a percent. This is useful for discrete investments, where there are zeros along the time series.
'''

#
if __name__ == '__main__':

    #discount_book=LeerExcel('../DiscountCostsParameters.xlsx')
    #discount_book_sheets=ListaHojas(discount_book)
    #discount_book_sheet=LeerHoja2(discount_book,discount_book_sheets[0],0)
    #header_sheet_discount=LeerHeaders(discount_book_sheet)
    discount_year= 2025 #LeerCol(discount_book_sheet, header_sheet_discount[0])[0]
    discount_rate= 0.0504 #LeerCol(discount_book_sheet, header_sheet_discount[1])[0]    

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
    #
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
    #
    global time_range_vector # This is the variable that manages time throughout the experiment
    time_range_vector = [ int(i) for i in S_DICT_sets_structure[ 'elements_list' ][0] ]
    #
    global final_year
    final_year = time_range_vector[-1]
    global initial_year
    initial_year = time_range_vector[0]
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
    book=pd.ExcelFile('Interface_RDM.xlsx')
    setup_table = book.parse( 'Setup' , 0)
    scenarios_to_reproduce = str( setup_table.loc[ 0 ,'Scenario_to_Reproduce'] )
    experiment_ID = str( setup_table.loc[ 0 ,'Experiment_ID'] )
    #
    global Initial_Year_of_Uncertainty
    Initial_Year_of_Uncertainty = int( setup_table.loc[ 0 ,'Initial_Year_of_Uncertainty'] )
    '''''
    ################################# PART 1 #################################
    '''''
    print('1: I start by reading the Uncertainty Table and systematically perturbing the paramaters.')
    uncertainty_table = book.parse( 'Uncertainty_Table' )
    # use .loc to access [row, column name]
    experiment_variables = list( uncertainty_table.columns )
    #
    np.random.seed( 555 )
    P = len( uncertainty_table.index ) # variables to vary
    N = int( setup_table.loc[ 0 ,'Number_of_Runs'] )  # number of samples

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

    hypercube = lhs( P , samples = N )
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
            else:
                evaluation_value_preliminary = 1
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
            #######################################################################
            # We can now store all the information for each future in a dictionary:
            #
            if n == 0: # the dictionary is created only when the first future appears
                ###################################################################################################################################
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
                if math_type == 'Time_Series' or math_type == 'Discrete_Investments':
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Explored_Parameter_of_X':Explored_Parameter_of_X } )
                    experiment_dictionary[ X_Num_unique[-1] ].update({ 'Values':[0.0 for x in range( 1, N+1 ) ] })
                    # We fill the data for future n=1 // it is important to note that the future n=0 can have completely different parameters when values are not relative to baseline
                    if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'YES':
                        experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][0] = this_future_X_change[-1] # here n=0
                #
            ###################################################################################################################################
            #
            else:
                if int( uncertainty_table.loc[ p ,'X_Num'] ) not in X_Num_unique: 
                    #
                    X_Num_unique.append( int( uncertainty_table.loc[ p ,'X_Num'] ) )
                    #
                    if math_type == 'Time_Series' or math_type == 'Discrete_Investments':
                        if str( uncertainty_table.loc[ p , 'Explored_Parameter_is_Relative_to_Baseline'] ) == 'YES':
                            experiment_dictionary[ int( uncertainty_table.loc[ p ,'X_Num'] ) ][ 'Values' ][n] = this_future_X_change[-1]
                    #
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
    # This section reads a reference data.csv from baseline scenarios and frames Structure-OSEMOSYS.xlsx
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
                        stable_scenarios[ scenario_list[scen] ][ this_param ][ 'value' ].append( round(float(row[ header_row[-1] ] ), 16 ) )
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

    '''
    # 3.B) We iterate over the experiment dictionary for the 1 to N futures additional to future 0, implementing the orderly manipulation
    '''
    print('3: That is done. Now I systematically perturb the model parameters.')
    # Broadly speaking, we must perfrom the same calculation across futures, as all futres are independent.
    #
    for s in range( len( scenario_list ) ):
        this_s = s
        fut_id = 0
        #

        for f in range( 1, len( all_futures )+1 ):
            this_f = f
            #
            # NOTE 0: TotalDemand and Mode Shift must take the BAU SpeecifiedAnnualDemand for coherence.
            TotalDemand = []
            TotalDemand_BASE_BAU = []

            for u in range( 1, len(experiment_dictionary)+1 ): # u is for the uncertainty number
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
                # NOTE 2: we go ahead with the manipulation of the uncertainty if it is applicable to the scenario we are interested in reproducing.

                if str( scenario_list[s] ) in Scenarios_Involved:
                    # We iterate over the involved parameters of the model here:
                    for p in range( len( Parameters_Involved ) ):
                        this_parameter = Parameters_Involved[p]
                        #
                        list_variation_waste = [
                            'Variacion en la cantidad de inorganicos reciclados y organicos compostados',
                            'Variacion en la cantidad de aguas residuales tratadas']
                        
                        ## FALTA CHEQUEAR
                        if X_Cat in list_variation_waste:
                            # print('##############')
                            # print('ENTRA 1')
                            # print(this_parameter)
                            # print('##############')
                            if 'inorganicos reciclados y organicos compostados' in X_Cat:
                                common_complement = [
                                    'LANDFILL', 'NO_CONTR_OD', 'OPEN_BURN', 'SIT_CLAN', 'NO_OSS_BLEND',
                                    'NO_OSS_NO_COLL', 'BLEND_NO_DCOLL', 'BLEND_NO_COLL', 'NO_SS']

                            if 'aguas residuales tratadas' in X_Cat:
                                common_complement = [
                                    #'WWWOT', 'WWWT', 'SEWERWWWOT', 'TWWWOT',
                                    #'SEWERWW', 'STWW']
                                    'LATR', 'EFLT_DISC', 'SEWER_NO_T',
                                    'WWWOT', 'DIRECT_DISC']# , 'AERO_PTAR', 'SEPT_SYST', 'WWWT', 'SEWERWW']
                            # First, sum the variation of all the non_varied sets:
                            sum_value_list_orig_nvs = [0]*len(time_range_vector)
                            sum_value_list_orig_chg = [0]*len(time_range_vector)
                            sum_value_list_new_nvs = [0]*len(time_range_vector)
                            sum_value_list_new_chg = [0]*len(time_range_vector)

                            # Across non-varied sets:
                            for nvs in common_complement:
                                this_nvs_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter]['t']) if x == str(nvs)]
                                value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_nvs_indices[0]:this_nvs_indices[-1]+1])
                                sum_value_list_orig_nvs = [sum(x) for x in zip(sum_value_list_orig_nvs, value_list)]

                            # Across varied sets:
                            for a_set in Sets_Involved:
                                this_aset_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter]['t']) if x == str(a_set)]
                                value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_aset_indices[0]:this_aset_indices[-1]+1])
                                sum_value_list_orig_chg = [sum(x) for x in zip(sum_value_list_orig_chg, value_list)]

                            sum_value_list_orig = [sum(x) for x in zip(sum_value_list_orig_nvs, sum_value_list_orig_chg)]
                                
                            # We must find multipliers:
                            sum_value_list_new_chg_target = \
                                AUX.interpolation_non_linear_final(
                                    time_range_vector, sum_value_list_orig_chg,
                                    float(Values_per_Future[fut_id]), 2050, Initial_Year_of_Uncertainty)                                

                            sum_value_list_mult_chg = [
                                sum_value_list_new_chg_target[i]/v for i, v in
                                enumerate(sum_value_list_orig_chg)]

                            # Change:
                            sum_value_list_diff_chg = [
                                sum_value_list_new_chg_target[i] - v
                                for i, v in enumerate(sum_value_list_orig_chg)]

                            # Find the complement multiplier:
                            sum_value_list_new_nvs_target = [
                                v - sum_value_list_diff_chg[i]
                                for i, v in enumerate(sum_value_list_orig_nvs)]
                            sum_value_list_mult_nvs = [
                                sum_value_list_new_nvs_target[i]/v for i, v in
                                enumerate(sum_value_list_orig_nvs)]

                            # Iterate again across the non-varied sets:
                            for nvs in common_complement:
                                this_nvs_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter]['t']) if x == str(nvs)]
                                value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_nvs_indices[0]:this_nvs_indices[-1]+1])
                                new_value_list = [v*sum_value_list_mult_nvs[i] for i, v in enumerate(value_list)]

                                inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_nvs_indices[0]:this_nvs_indices[-1]+1] = deepcopy(new_value_list)
                                if nvs in ['LATR', 'EFLT_DISC','AERO_PTAR_RU','SEWER_NO_T']:
                                    this_adj_indices2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['t'] ) if x == str(nvs)]
                                    inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_adj_indices2[0]:this_adj_indices2[-1]+1] = deepcopy(new_value_list)

                                sum_value_list_new_nvs = [sum(x) for x in zip(sum_value_list_new_nvs, new_value_list)]

                            # Iterate again across the varied sets:
                            for a_set in Sets_Involved:
                                this_aset_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][this_parameter]['t']) if x == str(a_set)]
                                value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_aset_indices[0]:this_aset_indices[-1]+1])
                                new_value_list = [v*sum_value_list_mult_chg[i] for i, v in enumerate(value_list)]

                                inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_aset_indices[0]:this_aset_indices[-1]+1] = deepcopy(new_value_list)
                                #if a_set == 'COMPOST':
                                #    print(new_value_list)
                                sum_value_list_new_chg = [sum(x) for x in zip(sum_value_list_new_chg, new_value_list)]

                            sum_value_list_new = [sum(x) for x in zip(sum_value_list_new_nvs, sum_value_list_new_chg)]

                        # The X type below is manipulated with immidiate restitution after adjustment.
                        elif ( Math_Type=='Time_Series' and ( Explored_Parameter_of_X=='Initial_Value' or
                                                              Explored_Parameter_of_X=='Final_Value' ) ):
                            #
                            for a_set in range( len( Sets_Involved ) ):
                                this_set_type_initial = S_DICT_sets_structure['initial'][ S_DICT_sets_structure['set'].index('TECHNOLOGY') ]
                                #
                                this_set = Sets_Involved[a_set]
                                if this_parameter == 'SpecifiedAnnualDemand':
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 'f' ] ) if x == str( this_set ) ]
                                else:
                                    this_set_range_indices = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ this_set_type_initial ] ) if x == str( this_set ) ]
                                    #print(this_parameter,this_set_range_indices)
                                    if X_Cat in ['Emisiones por aguas residuales industriales'] and len(this_set_range_indices) != 0:
                                        this_set_range_indices2 = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ][ this_set_type_initial ] ) if x == str( this_set ) ]
                                    #print(this_set_range_indices)
                                    #print(this_set_range_indices2)
                                if this_parameter == 'EmissionActivityRatio': # NO ENTRA ACÁ PERO LO DEJO PARA INCLUIR SI FUERA NECESARIO EN GUATEMALA U OTRO PROYECTO
                                    count_good = 0
                                    emis_list = list(set(inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['e'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ]))
                                    for e in emis_list:
                                        this_set_range_indices_e = [ i for i, x in enumerate( inherited_scenarios[ scenario_list[ s ] ][ f ][ this_parameter ][ 'e' ] ) if x == str( e ) ]
                                        all_indices_app = list(set(this_set_range_indices) & set(this_set_range_indices_e))
                                        all_indices_app.sort()
                                        if len(all_indices_app) != 0:
                                            time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ all_indices_app[0]:all_indices_app[-1]+1 ] )
                                            time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                            
                                            value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ all_indices_app[0]:all_indices_app[-1]+1 ] )
                                            value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                            
                                            new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))
                                            count_good += 1
                                #
                                ## LISTO
                                elif this_parameter in ['SpecifiedAnnualDemand'] and len(this_set_range_indices) != 0:
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
                                        #
                                        # this impacts normal variables
                                        new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))

                                        if 'National waste production' == X_Cat: # Perform additional adjustments:
                                            mult_new_value_list = [v/value_list[i] for i, v in enumerate(new_value_list)]
                                            adjust_var = 'TotalTechnologyAnnualActivityLowerLimit'
                                            # adjust_sets = [
                                            #     'INORG_RCY_COLL', 'INORG_RCY_OS', 'AD', 'COMPOST', 'OTH_ORG_TEC', 'LANDFILL_BG', 'LANDFILL', 'CONTR_OD',
                                            #     'NO_CONTR_OD', 'WWWOT', 'WWWT', 'WFIRU', 'OSS_INORG', 'OSS_ORG', 'NO_OSS_INORG', 'NO_OSS_ORG', 'NO_OSS_BLEND',
                                            #     'INORG_DCOLL', 'ORG_DCOLL', 'INORG_NO_DCOLL', 'ORG_NO_DCOLL', 'BLEND_NO_DCOLL', 'INORG_SS', 'ORG_SS', 'NO_SS',
                                            #     'SEWERWWWOT', 'SEWERWWWT', 'WWWTFIRU', 'TWWWOT', 'SEWERWW', 'STWW']
                                            
                                            if this_set == 'E5TSWTSW':
                                                adjust_sets = [
                                                    'INORG_RCY_OS','COMPOST','LANDFILL', 'NO_CONTR_OD','OPEN_BURN', 'SIT_CLAN', 'OSS_INORG', 'OSS_ORG', 'NO_OSS_BLEND', 'NO_OSS_NO_COLL',
                                                    'INORG_DCOLL', 'ORG_DCOLL',  'BLEND_NO_DCOLL','BLEND_NO_COLL',  'INORG_SS', 'ORG_SS', 'NO_SS']
                                            else: 
                                                adjust_sets = [
                                                      'AERO_PTAR' , 'AERO_PTAR_RU' , 'SEPT_SYST', 'LATR', 'EFLT_DISC', 'WWWT', 'WWWOT', 'SEWERWW', 'DIRECT_DISC','SEWER_NO_T']

                                            for adj_set in adjust_sets:
                                                this_adj_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][adjust_var]['t'] ) if x == str(adj_set)]

                                                adj_value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][adjust_var]['value'][this_adj_indices[0]:this_adj_indices[-1]+1])
                                                new_adj_value_list = [mult_new_value_list[i]*v for i, v in enumerate(adj_value_list)]
                                                
                                                # if adj_set == 'LANDFILL':
                                                #     print('ENTRA ACA: SAD')
                                                #     print(f,s)
                                                #     print(adj_value_list)
                                                #     print(new_adj_value_list)

                                                inherited_scenarios[scenario_list[s]][f][adjust_var]['value'][this_adj_indices[0]:this_adj_indices[-1]+1] = deepcopy(new_adj_value_list)
                                                
                                                if adj_set in ['LATR', 'EFLT_DISC','AERO_PTAR_RU','SEWER_NO_T']:
                                                    this_adj_indices2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['t'] ) if x == str(adj_set)]
                                                    inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_adj_indices2[0]:this_adj_indices2[-1]+1] = deepcopy(new_adj_value_list)
                                                    
                                            
                                            inherited_scenarios[scenario_list[s]][f][this_parameter]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list)

                                ## LISTO
                                elif X_Cat in ['Emisiones por aguas residuales industriales'] and len(this_set_range_indices) != 0:
                                    #print(this_set_range_indices )
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
                                        #
                                        # this impacts normal variables
                                        new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))
                                        adjust_var1 = 'TotalTechnologyAnnualActivityLowerLimit'
                                        adjust_var2 = 'TotalTechnologyAnnualActivityUpperLimit'

                                        inherited_scenarios[scenario_list[s]][f][adjust_var1]['value'][this_set_range_indices[0]:this_set_range_indices[-1]+1] = deepcopy(new_value_list)
                                        inherited_scenarios[scenario_list[s]][f][adjust_var2]['value'][this_set_range_indices2[0]:this_set_range_indices2[-1]+1] = deepcopy(new_value_list)

                                # ## LISTO
                                # elif this_parameter in ['TotalTechnologyAnnualActivityLowerLimit','TotalTechnologyAnnualActivityUpperLimit'] and len(this_set_range_indices) != 0:
                                #     sys.exit() #  NO SE ENTRA ACÁ
                                #     print('##############')
                                #     print('ENTRA 4')
                                #     print(this_parameter)
                                #     print('##############')
                                #     # for each index we extract the time and value in a list:
                                #     # extracting time:
                                #     time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #     time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                #     # extracting value:
                                #     value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #     value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #     #--------------------------------------------------------------------#
                                #     # now that the value is extracted, we must manipulate the result and assign back
                                #     if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios
                                #         #
                                #         # this impacts normal variables
                                #         new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))

                                #         #if 'National waste production' == X_Cat: # Perform additional adjustments:
                                #         if X_Cat in list_variation_waste:
                                #             mult_new_value_list = [v/value_list[i] for i, v in enumerate(new_value_list)]
                                #             adjust_var = 'TotalTechnologyAnnualActivityLowerLimit'
                                #             # adjust_sets = [
                                #             #     'INORG_RCY_COLL', 'INORG_RCY_OS', 'AD', 'COMPOST', 'OTH_ORG_TEC', 'LANDFILL_BG', 'LANDFILL', 'CONTR_OD',
                                #             #     'NO_CONTR_OD', 'WWWOT', 'WWWT', 'WFIRU', 'OSS_INORG', 'OSS_ORG', 'NO_OSS_INORG', 'NO_OSS_ORG', 'NO_OSS_BLEND',
                                #             #     'INORG_DCOLL', 'ORG_DCOLL', 'INORG_NO_DCOLL', 'ORG_NO_DCOLL', 'BLEND_NO_DCOLL', 'INORG_SS', 'ORG_SS', 'NO_SS',
                                #             #     'SEWERWWWOT', 'SEWERWWWT', 'WWWTFIRU', 'TWWWOT', 'SEWERWW', 'STWW']

                                #             adjust_sets = [
                                #                 'INORG_RCY_OS','COMPOST','LANDFILL', 'NO_CONTR_OD','OPEN_BURN', 'SIT_CLAN', 'OSS_INORG', 'OSS_ORG', 'NO_OSS_BLEND', 'NO_OSS_NO_COLL',
                                #                 'INORG_DCOLL', 'ORG_DCOLL',  'BLEND_NO_DCOLL','BLEND_NO_COLL',  'INORG_SS', 'ORG_SS', 'NO_SS', 
                                #                   'AERO_PTAR', 'SEPT_SYST', 'LATR', 'EFLT_DISC', 'WWWT', 'WWWOT', 'SEWERWW', 'DIRECT_DISC']

                                #             for adj_set in adjust_sets:
                                #                 this_adj_indices = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f][adjust_var]['t'] ) if x == str(adj_set)]

                                #                 adj_value_list = deepcopy(inherited_scenarios[scenario_list[s]][f][adjust_var]['value'][this_adj_indices[0]:this_adj_indices[-1]+1])
                                #                 new_adj_value_list = [mult_new_value_list[i]*v for i, v in enumerate(adj_value_list)]

                                #                 inherited_scenarios[scenario_list[s]][f][adjust_var]['value'][this_adj_indices[0]:this_adj_indices[-1]+1] = deepcopy(new_adj_value_list)
                                #                 #if adj_set == 'COMPOST':
                                #                 #    print(adj_value_list, new_adj_value_list)
                                #                 if adj_set in ['LATR', 'EFLT_DISC']:
                                #                     this_adj_indices2 = [i for i, x in enumerate(inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['t'] ) if x == str(adj_set)]
                                #                     inherited_scenarios[scenario_list[s]][f]['TotalTechnologyAnnualActivityUpperLimit']['value'][this_adj_indices2[0]:this_adj_indices2[-1]+1] = deepcopy(new_adj_value_list)
                                
                                # ## LISTO
                                # elif this_parameter in ['CapitalCost'] and len(this_set_range_indices) != 0:
                                #     print('##############')
                                #     print('ENTRA 5')
                                #     print(this_parameter)
                                #     print('##############')
                                #     # for each index we extract the time and value in a list:
                                #     # extracting time:
                                #     time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #     time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                #     # extracting value:
                                #     value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #     value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #     #print(value_list)
                                #     #--------------------------------------------------------------------#
                                #     # now that the value is extracted, we must manipulate the result and assign back
                                #     if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios
                                #         #
                                #         # this impacts normal variables
                                #         new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))
                                #     #
                                #     new_value_list_rounded = [ round(elem, 4) for elem in new_value_list ]
                                #     # plt.plot(value_list)
                                #     # plt.plot(new_value_list_rounded)
                                #     # plt.show()
                                #     #--------------------------------------------------------------------#
                                #     # Assign parameters back: for these subset of uncertainties
                                #     inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list_rounded)
                                    
                                # elif this_parameter in ['VariableCost'] and len(this_set_range_indices) != 0:
                                #     print('##############')
                                #     print('ENTRA 6')
                                #     print(this_parameter, this_set)
                                #     print('##############')
                                #     # for each index we extract the time and value in a list:
                                #     # extracting time:
                                #     if this_set not in ['INORG_RCY_OS', 'COMPOST']:
                                #         time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #         time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                #         # extracting value:
                                #         value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #         value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #         #--------------------------------------------------------------------#
                                #         # now that the value is extracted, we must manipulate the result and assign back
                                #         if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios
                                #             #
                                #             # this impacts normal variables
                                #             new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))
                                #             #
                                        
                                #         #--------------------------------------------------------------------#
                                #         # Assign parameters back: for these subset of uncertainties
                                #         inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                #     elif this_set in ['INORG_RCY_OS']:
                                #         time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #         time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                #         # extracting value:
                                #         value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #         value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #         #--------------------------------------------------------------------#
                                #         # now that the value is extracted, we must manipulate the result and assign back
                                #         if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios
                                #             #
                                #             # this impacts normal variables
                                #             new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))
                                #             #
                                        
                                #         #--------------------------------------------------------------------#
                                #         # Assign parameters back: for these subset of uncertainties
                                #         inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                        
                                #         # Asignar restriccion
                                #         activity=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'] )
                                #         technology=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['t'] )
                                #         anios=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['y'] )
                                #         region=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['r'] )
                                #         list_aux_activity=list()
                                #         list_aux_technology=list()
                                #         list_aux_anios=list()
                                #         list_aux_region=list()
                                #         for ite in range(len(technology)):
                                #             if technology[ite] == this_set:
                                #                 list_aux_region.append(region[ite])
                                #                 list_aux_anios.append(anios[ite])
                                #                 list_aux_technology.append(technology[ite])
                                #                 list_aux_activity.append(activity[ite])
                                #         for ite in range(len(list_aux_activity)):
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['r'].append(list_aux_region[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['y'].append(list_aux_anios[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['t'].append(list_aux_technology[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['value'].append(list_aux_activity[ite])
                                    
                                #     elif this_set in ['COMPOST']:
                                #         time_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['y'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #         time_list = [ int( time_list[j] ) for j in range( len( time_list ) ) ]
                                #         # extracting value:
                                #         value_list = deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] )
                                #         value_list = [ float( value_list[j] ) for j in range( len( value_list ) ) ]
                                #         #--------------------------------------------------------------------#
                                #         # now that the value is extracted, we must manipulate the result and assign back
                                #         if Explored_Parameter_of_X == 'Final_Value': # we must add a component to make occupancy rate be relative to BAU for the other 3 base scenarios
                                #             #
                                #             # this impacts normal variables
                                #             new_value_list = deepcopy( AUX.interpolation_non_linear_final( time_list, value_list, float(Values_per_Future[fut_id] ), 2050, Initial_Year_of_Uncertainty))
                                #             #
                                        
                                #         #--------------------------------------------------------------------#
                                #         # Assign parameters back: for these subset of uncertainties
                                #         inherited_scenarios[ scenario_list[s] ][ f ][ this_parameter ]['value'][ this_set_range_indices[0]:this_set_range_indices[-1]+1 ] = deepcopy(new_value_list)
                                        
                                #         # Asignar restriccion
                                #         activity=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'] )
                                #         technology=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['t'] )
                                #         anios=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['y'] )
                                #         region=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['r'] )
                                #         list_aux_activity=list()
                                #         list_aux_technology=list()
                                #         list_aux_anios=list()
                                #         list_aux_region=list()
                                #         for ite in range(len(technology)):
                                #             if technology[ite] == this_set:
                                #                 list_aux_region.append(region[ite])
                                #                 list_aux_anios.append(anios[ite])
                                #                 list_aux_technology.append(technology[ite])
                                #                 list_aux_activity.append(activity[ite])
                                #         for ite in range(len(list_aux_activity)):
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['r'].append(list_aux_region[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['y'].append(list_aux_anios[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['t'].append(list_aux_technology[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['value'].append(list_aux_activity[ite])
                                        
                                #         # Asignar restriccion a Letrinas
                                #         activity=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['value'] )
                                #         technology=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['t'] )
                                #         anios=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['y'] )
                                #         region=deepcopy( inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityLowerLimit' ]['r'] )
                                #         list_aux_activity=list()
                                #         list_aux_technology=list()
                                #         list_aux_anios=list()
                                #         list_aux_region=list()
                                #         for ite in range(len(technology)):
                                #             if technology[ite] == 'LATR' or technology[ite] == 'EFLT_DISC': #or technology[ite] == 'NO_CONTR_OD':
                                #                 list_aux_region.append(region[ite])
                                #                 list_aux_anios.append(anios[ite])
                                #                 list_aux_technology.append(technology[ite])
                                #                 list_aux_activity.append(activity[ite])
                                #         for ite in range(len(list_aux_activity)):
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['r'].append(list_aux_region[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['y'].append(list_aux_anios[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['t'].append(list_aux_technology[ite])
                                #             inherited_scenarios[ scenario_list[s] ][ f ][ 'TotalTechnologyAnnualActivityUpperLimit' ]['value'].append(list_aux_activity[ite])
                                            
                                        
                                    #
                                #--------------------------------------------------------------------#
                            #--------------------------------------------------------------------#
                    #--------------------------------------------------------------------#
                    #
                #
            #
            fut_id += 1
    #sys.exit()
    #
    print( '    We have finished the experiment and inheritance' )
    #
    time_list = []
    scenario_list_print = scenario_list

    # Before printing the experiment dictionary, be sure to add future 0:
    experiment_dictionary[1]['Futures'] = [0] + experiment_dictionary[1]['Futures']
    experiment_dictionary[1]['Values'] = [3] + experiment_dictionary[1]['Values']

    if generator_or_executor == 'Generator' or generator_or_executor == 'Both':
        #
        print('4: We will now print the input .txt files of diverse future scenarios.')
        #
        print_adress = './Experimental_Platform/Futures/'
        packaged_useful_elements = [scenario_list_print, S_DICT_sets_structure, S_DICT_params_structure,
                                    list_param_default_value_params, list_param_default_value_value,
                                    print_adress, all_futures, time_range_vector ]
        #
        if parallel_or_linear == 'Parallel':
            print('Entered Parallelization')
            #
            x = len(all_futures)*len(scenario_list_print)
            max_x_per_iter = int( setup_table.loc[ 0 ,'Parallel_Use'] ) # FLAG: This is an input
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
                    p = mp.Process(target=function_C_mathprog_parallel, args=(n2,inherited_scenarios,packaged_useful_elements,) )
                    processes.append(p)
                    p.start()
            
                for process in processes:
                    process.join()
                end_1 = time.time()
                time_elapsed_1 = -start1 + end_1
                print( str( time_elapsed_1 ) + ' seconds' )
                time_list.append( time_elapsed_1 )
                #
            print('   The total time producing the input .txt files has been:' + str( sum( time_list ) ) + ' seconds')
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
    #########################################################################################
    #
    if generator_or_executor == 'Executor' or generator_or_executor == 'Both':
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
            max_x_per_iter = int( setup_table.loc[ 0 ,'Parallel_Use'] ) # FLAG: This is an input.
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
                    p = mp.Process(target=main_executer, args=(n2,Executed_Scenario, time_range_vector, discount_year, discount_rate))
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