# -*- coding: utf-8 -*-
"""
Created on Tue Mar 31 09:38:22 2020

@author: benja
"""
import os 

'''Change the directory to where your external data folder is.'''


directory=r'C:\Users\benja\Documents\UVM\DS1\PR01_bdube\external-data\data'
os.chdir(r'C:\Users\benja\Documents\UVM\DS1\PR01_bdube\external-data\data')


files_w_corruptedData=[]


for filename in [f for f in os.listdir() if '.DS_Store' not in f]:
    with open(filename) as file:
        print(file.read())
        is_wrong=input('Is this data wrong (Y/N)').upper()
        if is_wrong=='Y':
            files_w_corruptedData.append(filename)
            
print(files_w_corruptedData)           
#%%
with open(r"C:\Users\benja\Documents\UVM\DS1\PR02\bad_files.txt", 'w') as file:
    for f in files_w_corruptedData:
        print(f, file=file)