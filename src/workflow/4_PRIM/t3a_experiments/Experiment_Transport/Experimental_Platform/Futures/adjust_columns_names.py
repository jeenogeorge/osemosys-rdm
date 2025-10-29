import os
import re
import csv
import pandas as pd

############################################################################################################################
def adjust_columns_names():
    file_aboslute_address = os.path.abspath("local_dataset_creator_f.py")
    file_adress = re.escape( file_aboslute_address.replace( 'local_dataset_creator_f.py', '' ) ).replace( '\:', ':' )
    #file_adress += '\\Futures\\'
    #
    scenario_list_raw = os.listdir( file_adress )
    scenario_list = [e for e in scenario_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
    #
    #li = []
    #
    for s in range( len( scenario_list ) ):
        #
        case_list_raw = os.listdir( file_adress + '\\' + scenario_list[s] )
        case_list = [e for e in case_list_raw if ('.py' not in e ) and ('.csv' not in e ) and ('__pycache__' not in e) ]
        #
        for n in range( len( case_list ) ):
            filename = file_adress + '\\' + scenario_list[s] + '\\' + case_list[n] + '\\' + case_list[n] + '_Output.csv'
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
                print(type(df))
                #print(case_list[n].split('_'))
                #df=df.assign(Strategy=case_list[n].split('_')[0])
                #df=df.assign(FutureNum=case_list[n].split('_')[1])
                df.insert(0,'FutureNum', case_list[n].split('_')[1])
                df.insert(0,'Strategy', case_list[n].split('_')[0])
                df.rename(columns={'FutureNum':'Future.ID','YEAR':'Year','TECHNOLOGY':'Technology','FUEL':'Fuel','EMISSION':'Emission'}, inplace=True)
                df=df.drop(['Unnamed: 0'], axis=1)
                #li.append(df)
                #df.sort_values(by=['Strategy','Future.ID','Year','Technology','Fuel','Emission'], inplace=True)

                print(list(df.columns))
                #frame = pd.concat(df, axis=0, ignore_index=True)
                print(df)
                export_csv = df.to_csv ( filename, index = None, header=True)
            else:
                pass

if __name__ == '__main__':    
    adjust_columns_names()