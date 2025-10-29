# import pickle

# x=pickle.load('all_comp_pfd.pickle')

import pickle

# open a file, where you stored the pickled data
file = open('./t3b_sdiscovery/subtbl_ana_1_exp_Integrated.pickle', 'rb')

# dump information to that file
data = pickle.load(file)

# close the file
file.close()