# -*- coding: utf-8 -*-
"""
Created on Fri Feb 21 13:20:00 2020

@author: benja
"""

import sqlite3
from sqlite3 import Error
import requests
import json
import websocket
import pickle
import sklearn
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer


try:
    import thread
except ImportError:
    import _thread as thread


class DATABASE:
    def __init__(self, filename):
        # create the database
        self.filename=filename

    def connector(function):
        '''decorator to automatically open connection, create cursor, commit changes and close connection.'''
        def wrapper(self, *args):
            self.conn=sqlite3.connect(self.filename)
            self.c=self.conn.cursor()  # create a cursor object
            result=function(self, *args)
            self.conn.commit() #save changes, if any
            self.conn.close()
            return result
        return wrapper
    
    @connector   
    def createTable(self, table_name, columns):
        try:
            # create a table
            print (f"CREATE TABLE {table_name} {tuple([c for c in columns])}")
            self.c.execute(f"CREATE TABLE {table_name} {tuple([c for c in columns])}")
            return True
        
        except Error as e:
            # catch the error if the table already exists
            print(e)
            return False
    
    @connector
    def writeMsg(self, msg):
        self.c.execute("INSERT INTO training_data (txt, action) VALUES (?, ?)", (msg["text"], msg["action"],))
    
    @connector    
    def showTable(self):
        self.c.execute("SELECT * FROM training_data")
        return self.printQuery("Showing all the data in training_data table")
        
    @connector    
    def readAction(self, action):
        self.c.execute("SELECT * FROM training_data WHERE action=?", (action,))
        return self.printQuery(message=f"Showing all the rows with action={action}")
    
    @connector
    def table2Lists(self):
        self.c.execute("SELECT * FROM training_data")
        rows = self.c.fetchall()
        texts=[row[0] for row in rows]
        actions=[row[1] for row in rows]
        return texts, actions
        
    @connector
    def deleteRecord(self, record):
        self.c.execute("DELETE from training_data where action=?", (record,))
        return self.printQuery("Deleted a record from training_data table")
        
    def printQuery(self, message):
        '''Print a message and the currently selected Rows'''
        rows = self.c.fetchall()
        print (message)
        
        for row in rows:
            print(row) 
        return rows
        
class bot(object):
    
    def __init__(self, database=None, ws=None, model=None):
        self.database=database #What is the database that Jarvis is logging to?
        self.training=False #Is jarvis currently training?
        self.testing=False #Is jarvis currently testing?
        self.current_action=None #Is there a current action type? 
        self.database.createTable('training_data', ['txt', 'action'])
        self.ws=ws
        self.model=model
        
    def startTrain(self):
        self.training=True
        self.testing=False
        self.current_action=None
        self.sendReply( "Ok, I'm ready for training. What NAME should this ACTION be?")
    
    def startTest(self):
        self.testing=True
        self.training=False
        self.current_action=None
        self.sendReply("I'm Training my brain with the data you've already given me...")
        self.trainBrain()
        self.sendReply("I'm ready for testing. Write me something and I'll try to figure it out.")
        
    def stopTest(self):
        self.testing=True
        self.current_action=None
        self.sendReply( "Ok I'm Finished Testing")
    
    def stopTrain(self):
        self.training=False
        self.current_action=None
        J.database.showTable()
        self.sendReply( "Ok, I'm finished training. See you next time!")
        
    def respond(self, message):
         self.current_channel=message['channel']
         if message['text'].lower()=='training time':
             self.startTrain()
         elif message['text'].lower()=='testing time':
             self.startTest()
         elif self.training:   
             if message['text'].lower()=='done':
                self.stopTrain()
             else:
                self.trainingSeq(message)
         elif self.testing:
             if message['text'].lower()=='done':
                 self.stopTest()
             else:
                 self.testing_seq(message)
         else:
            return None
             #Otherwise don't reply
    
    def sendReply(self, reply):
        if reply:
            if self.ws:
                reply_dict=self.reply_formatter(reply)
                self.ws.send(json.dumps(reply_dict))
            else:
                print (reply)
        
    def reply_formatter(self, reply):
        reply_dict= {
                       "id": 1,
                       "type": "message",
                       "channel": self.current_channel,
                       "text": reply,
                       }
        
        if self.current_action and str(self.current_action) in reply: #If we need to change formatting of ACTION
            reply_dict['blocks']=[{'type': 'rich_text', 
                                     'elements': [
                                      {'type': 'rich_text_section',
                                       'elements': [
                                      {'type': 'text', 
                                       'text': reply.split(self.current_action)[0]}, 
                                      {'type': 'text',
                                       'text': self.current_action, 
                                       'style': {'code':True}}, #format name of action as code block
                                      {'type': 'text', 
                                         'text': reply.split(self.current_action)[1]}
                                              ]}
                                       ]
                                       }
                                       ]
        return reply_dict
    
    def trainingSeq(self, message):
        if self.current_action: #if action is currently defined
            message['action']=self.current_action #assign  action to message dictionary
            self.logData(message) #log data
        else:
            self.current_action=message['text'].upper() #if action is not defined, define action as current message text.
            self.sendReply( f"Ok, lets call this action `{self.current_action}`. Now give me some training text!")

    def logData(self, message):
        '''Log Data to self.database. Message is a dictionary, 'action' and 'text' and 'time' are all keys.'''
        self.database.writeMsg(message)
        self.sendReply("Ok, I've got it! What else do you want to teach me?")
         
    
    def trainBrain(self):
        '''Use the data in the database to train Jarvis's Brain'''
        texts, actions=self.database.table2Lists()
        self.model.fit(texts, actions)
   
    
    def classify(self, text):
        '''Use Jarvis's brain to classify a string of text.'''
        return self.model.predict([text])[0]
        
    
    def testing_seq(self, message):
        self.current_action=self.classify(message['text'])
        self.sendReply(f"Ok I think the action you mean is {self.current_action}...")
        self.sendReply(  "Write me something else and I'll try to figure it out." )
    
    def run_offline(self):
        self.ws=None
        while True:
            text=input()
            message={'text': text, 'channel': None}
            if text.lower()=='quit':
                return
            self.respond(message)

def load_token(filename):
    with open(filename) as f:
        return f.read()

def on_message(ws, message):
    message=json.loads(message)
    if message:
        if message.get('type',None)=='message': #if the data type is a message
           print(message)
           J.respond(message)  #do jarvis's on mesage stuff
            #send reply 
               
def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    def run(*args):
       pass
    thread.start_new_thread(run, ())


def testDB():
    '''Test of database functions'''
    J=bot(database=DATABASE('tester.db')) 
    J.logData({'action':'time', 'text': 'what time is it'})
    J.logData({'action': 'test', 'text': 'this is a test'})
    J.database.readAction('time')
    J.database.showTable()






#%%
if __name__ == "__main__":
    token=load_token('token.txt') #load token 
    websocket.enableTrace(True)
    
    model=Pipeline([
     ('vect', CountVectorizer()),
     ('tfidf', TfidfTransformer()),
     ('clf', MultinomialNB())
     ])
    response=requests.get(f'https://slack.com/api/rtm.connect?token={token}&pretty=1').json() #get url from auth token
    url=response['url'].replace('\/', '/') #clean url
    ws = websocket.WebSocketApp(url=url,
                             on_open= on_open,
                             on_message = on_message,
                             on_error = on_error,
                             on_close = on_close)
    J=bot(database=DATABASE('jarvis.db'), ws=ws, model=model) #create jarvis
    ws.on_open = on_open
    ws.run_forever()