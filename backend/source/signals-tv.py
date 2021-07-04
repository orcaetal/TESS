import requests
import json


webhook_url = 'http://127.0.0.1:80/webhook'

'''
SIGNALS:

[BULL-TC, BULL-ADD, BULL-TP]
[BEAR-TC, BEAR-ADD, BEAR-TP]

When theres a TC table, we want to deactivate_tables['ALLTABLES']

'''
BULL_TC={
    'Buy' : 
    {

        'activate_tables' : ['bull_small'], 

        'deactivate_tables' : ['ALLTABLES'], 

        'closePos' : 'False',

    },

    'Sell' : 
    {

        'activate_tables' : ['bull_positioning'],

        'deactivate_tables' : ['ALLTABLES'],

        'closePos' : 'False',

    },

    'None' : 
    {

        'activate_tables' : ['bull_small'],

        'deactivate_tables' : ['ALLTABLES'],
        
        'closePos' : 'False',
        

    },
    'key' : 'zekKey'
}


BULL_ADD={

    'Buy' : 
    {

        'activate_tables' : ['bull_positioning'], 
        
        'deactivate_tables' : ['NONE'], 

        'closePos' : 'False',

    },

    'Sell' : 
    {

        'activate_tables' : ['bull_aggressive'],

        'deactivate_tables' : ['NONE'],

        'closePos' : 'False',



    },

    'None' : 
    {
 
        'activate_tables' : ['bull_positioning'],

        'deactivate_tables' : ['NONE'],
        
        'closePos' : 'False',
        

    },
    'key' : 'zekKey'
}


BULL_TP={

    'Buy' : 
    {

        'activate_tables' : ['bull_small'], 

        'deactivate_tables' : ['ALLTABLES'], 

        'closePos' : 'True',


    },

    'Sell' : 
    {
        'activate_tables' : ['bull_small'],

        'deactivate_tables' : ['ALLTABLES'],

        'closePos' : 'True',


    },

    'None' : 
    { 
        'activate_tables' : ['bull_small'],

        'deactivate_tables' : ['ALLTABLES'],
        
        'closePos' : 'True',
        

    },
    'key' : 'zekKey'
}


BEAR_TC ={

    'Buy' : 
    {

        'activate_tables' : ['bear_positioning'], 

        'deactivate_tables' : ['ALLTABLES'], 

        'closePos' : 'False',

    },
    
    'Sell' : 
    {
        
        'activate_tables' : ['bear_small'],

        'deactivate_tables' : ['ALLTABLES'],

        'closePos' : 'False',


    },
    
    'None' : 
    {

        'activate_tables' : ['sideways'],

        'deactivate_tables' : ['ALLTABLES'],
        
        'closePos' : 'False',
        

    },
    'key' : 'zekKey'
}


BEAR_ADD={
    
    'Buy' : 
    {

        'activate_tables' : ['bear_aggressive'], 

        'deactivate_tables' : ['NONE'], 

        'closePos' : 'False',

    },
    
    'Sell' : 
    {
        
        'activate_tables' : ['bear_positioning'],

        'deactivate_tables' : ['NONE'],

        'closePos' : 'False',

    },
    
    'None' : 
    {
        
        'activate_tables' : ['bear_aggressive'],

        'deactivate_tables' : ['NONE'],
        
        'closePos' : 'False',
        
    },
    'key' : 'zekKey'
}


BEAR_TP ={
    
    'Buy' : 
    {

        'activate_tables' : ['bear_small'], 

        'deactivate_tables' : ['ALLTABLES'], 

        'closePos' : 'True',


    },
    
    'Sell' : 
    {
        'activate_tables' : ['bear_small'],

        'deactivate_tables' : ['ALLTABLES'],

        'closePos' : 'True',

        
    },
    
    'None' : 
    { 
        'activate_tables' : ['bear_small'],

        'deactivate_tables' : ['ALLTABLES'],
        
        'closePos' : 'True',
       

    },
    'key' : 'zekKey'
}


print("sending webhook. .")
r = requests.post(webhook_url, data=json.dumps(BULL_ADD))
