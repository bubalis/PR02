# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 17:05:23 2020

@author: benja
"""

from jarvis import bot, DATABASE
import os
import json
import sklearn
from sklearn.naive_bayes import MultinomialNB, GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import SGDClassifier  
import numpy as np
from sklearn.preprocessing import FunctionTransformer


directory=r'C:\Users\benja\Documents\UVM\DS1\PR01_bdube\external-data\data' #change this to data folder

bad_files=open("bad_files.txt").read().split('\n')    
#%%

def read_line(line):
    if '{' in line:
        dic=json.loads(line)
        x_val=dic['TXT']
        y_val=dic['ACTION']
        return x_val, y_val
    elif line:
        try:
            data=line.split(',')
            x_val=','.join(data[:-1])
            y_val=data[-1]
            return x_val.replace('"', '').replace("'", ""), y_val
        except:
            print(line)
    return None, None
        
            
def load_additional_data(directory, X,y):
    '''Load Training Data From Folder'''
    all_ys=[]
    old_dir=os.getcwd()
    os.chdir(directory)
    for filename in [f for f in os.listdir() if '.DS_Store' not in f 
                     and f not in bad_files
                     ]:
        with open(filename) as file:
            for line in file.read().split('\n'):
                x_val, y_val=read_line(line)
                all_ys.append(y_val)
                if str(y_val).upper() in actions and x_val not in X:
                    X.append(x_val)
                    y.append(str(y_val).upper())
    os.chdir(old_dir)
    return X,y, set(all_ys)

J=bot(database=DATABASE('jarvis.db'), 
      model=None)

X,y=[],[]

X,y=J.database.table2Lists()
print(X)

actions=['GREET',
 'JOKE',
 'PIZZA',
 'TIME',
 'WEATHER']

X,y, all_ys=load_additional_data(directory, X,y) 
print(all_ys)
#%%


methods=[
        MultinomialNB, 
        SGDClassifier,
        
             ]


results={method.__name__: [] for method in methods}

for n in range(5):
    X_train, X_test, y_train, y_test = sklearn.model_selection.train_test_split(
                                            X, y, test_size=0.2)
    
    for method in methods:
        print('\n\n\n')
        print(method.__name__)
        model=Pipeline([
        ('vect', CountVectorizer()),
      ('tfidf', TfidfTransformer()),
        ('clf', method())
            ])
        
        model.fit(X_train, y_train)
        predicted= model.predict(X_test)
        
        precision, recall, fbeta_score, _=sklearn.metrics.precision_recall_fscore_support(
                                                y_test, predicted, average='weighted')
        
        dic={'Precision': precision, 'Recall': recall, 'Fbeta': fbeta_score}
        
        results[method.__name__].append(dic)

print(results)
for key, value in results.items():
    print(key, np.mean([item['Fbeta'] for item in value]))  
    
print('\n\n')

for key, value in results.items():
    print(key, np.mean([item['Precision'] for item in value]))          
        