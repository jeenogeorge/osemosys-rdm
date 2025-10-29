import os
import re
import csv
import pandas as pd
#
def test1():
    print( 'hello world 2' )
############################################################################################################################
def execute_local_dataset_creator_f_outputs ():
    file_aboslute_address = os.path.abspath("local_dataset_creator_f.py")
    file_adress = os.path.join(file_aboslute_address.replace( 'local_dataset_creator_f.py', '' ),'Futures')
    #
    scenario_list_raw = os.listdir( file_adress )
    scenario_list = [e for e in scenario_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
    #
    li = []
    #
    for s in range( len( scenario_list ) ):
        #
        case_list_raw = os.listdir(os.path.join(file_adress, scenario_list[s]))
        case_list = [e for e in case_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
        #
        for n in range( len( case_list ) ):
            filename = os.path.join(file_adress, scenario_list[s], case_list[n], f'{case_list[n]}_Output.csv')
            #
            print('######################')
            print(case_list[n])
            print('######################')
            line_count = 0
            with open( filename ) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                for row in csv_reader:
                    line_count += 1
            if line_count > 1:
                df = pd.read_csv(filename, index_col=None, header=0, low_memory=False)
                #print(case_list[n].split('_'))
                df=df.assign(Strategy=case_list[n].split('_')[0])
                df=df.assign(FutureNum=case_list[n].split('_')[1])
                df.rename(columns={'FutureNum':'Future.ID','YEAR':'Year','TECHNOLOGY':'Technology','FUEL':'Fuel','EMISSION':'Emission'}, inplace=True)
                df=df.drop(['Unnamed: 0'], axis=1)
                print(list(df.columns))
                li.append(df)
            else:
                pass
    #
    frame = pd.concat(li, axis=0, ignore_index=True)
    export_csv = frame.to_csv ( os.path.join(file_adress, 'output_dataset_f.csv'), index = None, header=True)
############################################################################################################################
def execute_local_dataset_creator_f_inputs ():
    file_aboslute_address = os.path.abspath("local_dataset_creator_f.py")
    file_adress = os.path.join(file_aboslute_address.replace( 'local_dataset_creator_f.py', '' ),'Futures')
    #
    scenario_list_raw = os.listdir( file_adress )
    scenario_list = [e for e in scenario_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
    #
    li = []
    #
    for s in range( len( scenario_list ) ):
        #
        case_list_raw = os.listdir(os.path.join(file_adress, scenario_list[s]))
        case_list = [e for e in case_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
        #
        for n in range( len( case_list ) ):
            filename = os.path.join(file_adress, scenario_list[s], case_list[n], f'{case_list[n]}_Input.csv')
            #
            line_count = 0
            with open( filename ) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                for row in csv_reader:
                    line_count += 1
            if line_count > 1:
                df = pd.read_csv(filename, index_col=None, header=0, low_memory=False)
                li.append(df)
            else:
                pass
    #
    frame = pd.concat(li, axis=0, ignore_index=True)
    export_csv = frame.to_csv ( os.path.join(file_adress, 'input_dataset_f.csv'), index = None, header=True)
############################################################################################################################
def execute_local_dataset_creator_f_prices ():
    file_aboslute_address = os.path.abspath("local_dataset_creator_f.py")
    file_adress = os.path.join(file_aboslute_address.replace( 'local_dataset_creator_f.py', '' ),'Futures')
    #
    scenario_list_raw = os.listdir( file_adress )
    scenario_list = [e for e in scenario_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
    #
    li = []
    #
    for s in range( len( scenario_list ) ):
        #
        case_list_raw = os.listdir(os.path.join(file_adress, scenario_list[s]))
        case_list = [e for e in case_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
        #
        for n in range( len( case_list ) ):
            #
            x = os.listdir( os.path.join(file_adress, scenario_list[s], case_list[n])  )
            #
            if len(x) == 5:
                #
                filename = os.path.join(file_adress, scenario_list[s], case_list[n], f'{case_list[n]}_Prices.csv')
                #
                line_count = 0
                with open( filename ) as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    for row in csv_reader:
                        line_count += 1
                if line_count > 1:
                    df = pd.read_csv(filename, index_col=None, header=0)
                    li.append(df)
                else:
                    pass
            #
            else:
                print(case_list[n])
    print('###')
    #
    frame = pd.concat(li, axis=0, ignore_index=True)
    export_csv = frame.to_csv ( os.path.join(file_adress, 'price_dataset_f.csv'), index = None, header=True)
############################################################################################################################
def execute_local_dataset_creator_f_distribution ():
    file_aboslute_address = os.path.abspath("local_dataset_creator_f.py")
    file_adress = os.path.join(file_aboslute_address.replace( 'local_dataset_creator_f.py', '' ),'Futures')
    #
    scenario_list_raw = os.listdir( file_adress )
    scenario_list = [e for e in scenario_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
    #
    li = []
    #
    for s in range( len( scenario_list ) ):
        #
        case_list_raw = os.listdir(os.path.join(file_adress, scenario_list[s]))
        case_list = [e for e in case_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
        #
        for n in range( len( case_list ) ):
            #
            x = os.listdir( os.path.join(file_adress, scenario_list[s], case_list[n])  )
            #
            if len(x) == 5:
                #
                filename = os.path.join(file_adress, scenario_list[s], case_list[n], f'{case_list[n]}_Distribution.csv')
                #
                line_count = 0
                with open( filename ) as csv_file:
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    for row in csv_reader:
                        line_count += 1
                if line_count > 1:
                    df = pd.read_csv(filename, index_col=None, header=0)
                    li.append(df)
                else:
                    pass
            #
            else:
                print(case_list[n])
    print('###')
    #
    frame = pd.concat(li, axis=0, ignore_index=True)
    export_csv = frame.to_csv ( os.path.join(file_adress, 'distribution_dataset_f.csv'), index = None, header=True)
############################################################################################################################