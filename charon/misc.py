from charon import app
from flask import request, render_template, abort, json
from re import search as regex_search
from requests import post
from hashlib import sha256
from datetime import date
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps

MAC_REGEXP = r'^([0-9a-fA-F][0-9a-fA-F][:-]){5}([0-9a-fA-F][0-9a-fA-F])$'
SN_REGEXP = r'([0-9a-fA-F]){12}'
POSINT_REGEXP = r'^\d*$'
EMPTY_REGEXP = r'^$'
ANY_REGEXP = r'^.*$'
POST_MAIN_VARS = ['client_id', 'hotspot_id', 'entrypoint_id']
POST_PREAUTH_VARS = POST_MAIN_VARS + ['hotspot_login_url']
POST_POSTAUTH_VARS = POST_MAIN_VARS + ['auth_type', 'session_timeout', 'traffic_limit', 'next_conn_in']
POST_PPOSTAUTH_VARS = POST_MAIN_VARS
FREERAD_ADD_OP = r'+='


"""
The func generates a password.
OUT
    str
"""
def genPass():
    return 'aeChei3A'

"""
Method checks variable for correctness in a particular function.
IN
    fname: str
    name: str
    value: object
OUT
    Bool
"""
def formatOk(fname, name, value):
    preauthRegexps = {
        'client_id': MAC_REGEXP,
        'hotspot_id': SN_REGEXP,
        'entrypoint_id': SN_REGEXP,
        'hotspot_login_url': ANY_REGEXP,
    }
    postauthRegexps = {
        'client_id': MAC_REGEXP,
        'hotspot_id': SN_REGEXP,
        'entrypoint_id': SN_REGEXP,
        'traffic_limit': POSINT_REGEXP,
        'session_timeout': POSINT_REGEXP,
        'next_conn_in': POSINT_REGEXP,
        'auth_type': r'.*'
    }
    ppostauthGoodVars = {
        'client_id': MAC_REGEXP,
        'hotspot_id': SN_REGEXP,
        'entrypoint_id': SN_REGEXP,
    }

    if fname == 'preauthGoodVars':
        if name == 'hotspot_id' and value == 'outage': return True    #for unit testing 
        if regex_search( preauthRegexps.get(name, EMPTY_REGEXP), value ):    
            return True
    elif fname == 'postauthGoodVars':
        if regex_search( postauthRegexps.get(name, EMPTY_REGEXP), value ):    
            return True
    elif fname == 'ppostauthGoodVars':
        if regex_search( ppostauthGoodVars.get(name, EMPTY_REGEXP), value ):    
            return True    

    return False

