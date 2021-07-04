'''
SIGNALS:

[BULL-TC, BULL-ADD, BULL-TP]
[BEAR-TC, BEAR-ADD, BEAR-TP]

When theres a TC table, we want to deactivate_tables['ALLTABLES']

'''
# Trend change BULL alert has been sent
BULL-TC ={
    # If we have a long position open,
    'Buy' : 
    {
        # Add to our long position
        'activate_tables' : ['bull_small'], 
        # Deactivate all bear tables that may be open
        'deactivate_tables' : ['ALLTABLES'], 

        'closePos' : 'False',

    },
    # If we have a short position open,
    'Sell' : 
    {
        # Run bull positioning because we're currently in a short
        'activate_tables' : ['bull_positioning'],

        'deactivate_tables' : ['ALLTABLES'],

        'closePos' : 'False',

    },
    # If theres no position open,
    'None' : 
    {
        # Run bull small because theres no position open
        'activate_tables' : ['bull_small'],

        'deactivate_tables' : ['ALLTABLES'],
        
        'closePos' : 'False',
        

    },
    'key' : 'zekKey'
}

# Bull-add signal has been sent
BULL-ADD ={
    # If we have a long position open,
    'Buy' : 
    {
        # Add to our long position
        'activate_tables' : ['bull_positioning'], 
        
        'deactivate_tables' : ['NONE'], 

        'closePos' : 'False',

    },
    # If we have a short position open,
    'Sell' : 
    {
        # We shouldn't have a short open...
        'activate_tables' : ['bull_aggressive'],

        'deactivate_tables' : ['NONE'],

        'closePos' : 'False',



    },
    # If theres no position open,
    'None' : 
    {
        # Still run bull 
        'activate_tables' : ['bull_positioning'],

        'deactivate_tables' : ['NONE'],
        
        'closePos' : 'False',
        

    },
    'key' : 'zekKey'
}

# Take profit bull signal has been sent
BULL-TP ={
    # If we have a long position open,
    'Buy' : 
    {
        # Just close our current position
        'activate_tables' : ['NONE'], 

        'deactivate_tables' : ['NONE'], 

        'closePos' : 'True',


    },
    # If we have a short position open,
    'Sell' : 
    {
        'activate_tables' : ['NONE'],

        'deactivate_tables' : ['NONE'],

        'closePos' : 'True',


    },
    # If theres no position open,
    'None' : 
    { 
        'activate_tables' : ['NONE'],

        'deactivate_tables' : ['NONE'],
        
        'closePos' : 'True',
        

    },
    'key' : 'zekKey'
}

# Trend change BEAR alert has been sent
BEAR-TC ={
    # If we have a long position open,
    'Buy' : 
    {
        # Adjust with bear_positioning
        'activate_tables' : ['bear_positioning'], 
        # Deactivate all other bull tables that may be open
        'deactivate_tables' : ['ALLTABLES'], 

        'closePos' : 'False',

    },
    # If we have a short position open,
    'Sell' : 
    {
        # Add to our bear position
        'activate_tables' : ['bear_small'],

        'deactivate_tables' : ['ALLTABLES'],

        'closePos' : 'False',


    },
    # If theres no position open,
    'None' : 
    {
        # Run sideways
        'activate_tables' : ['sideways'],

        'deactivate_tables' : ['ALLTABLES'],
        
        'closePos' : 'False',
        

    },
    'key' : 'zekKey'
}

# Bear-add signal has been sent
BEAR-ADD ={
    # If we have a long position open,
    'Buy' : 
    {
        # We shouldn't have a long position..
        'activate_tables' : ['bear_aggressive'], 

        'deactivate_tables' : ['NONE'], 

        'closePos' : 'False',

    },
    # If we have a short position open,
    'Sell' : 
    {
        # Add to our short position
        'activate_tables' : ['bear_positioning'],

        'deactivate_tables' : ['NONE'],

        'closePos' : 'False',

    },
    # If theres no position open,
    'None' : 
    {
        # Still run bear 
        'activate_tables' : ['bear_aggressive'],

        'deactivate_tables' : ['NONE'],
        
        'closePos' : 'False',
        
    },
    'key' : 'zekKey'
}

# Take profit bear signal has been sent
BEAR-TP ={
    # If we have a long position open,
    'Buy' : 
    {
        # Just close our current position
        'activate_tables' : ['NONE'], 

        'deactivate_tables' : ['NONE'], 

        'closePos' : 'True',


    },
    # If we have a short position open,
    'Sell' : 
    {
        'activate_tables' : ['NONE'],

        'deactivate_tables' : ['NONE'],

        'closePos' : 'True',

        
    },
    # If theres no position open,
    'None' : 
    { 
        'activate_tables' : ['NONE'],

        'deactivate_tables' : ['NONE'],
        
        'closePos' : 'True',
       

    },
    'key' : 'zekKey'
}


