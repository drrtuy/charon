from charon import app
from flask import request, render_template, abort, json, session, g, make_response
#from re import search as regex_search
#from requests import post
from hashlib import sha256
from datetime import date
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps
from inspect import stack
from misc import formatOk, genPass, idleCheck, getPreauthTemplateData, getPreauthModel
from ubiquity import doUbiquityRedirect
from model import *

MAC_REGEXP = r'^([0-9a-fA-F][0-9a-fA-F][:-]){5}([0-9a-fA-F][0-9a-fA-F])$'
SN_REGEXP = r'([0-9a-fA-F]){12}'
POSINT_REGEXP = r'^\d*$'
EMPTY_REGEXP = r'^$'
ANY_REGEXP = r'^.*$'
POST_MAIN_VARS = ['client_id', 'hotspot_id', 'entrypoint_id']
MT_PREAUTH_VARS = POST_MAIN_VARS + ['hotspot_login_url']
UNI_PREAUTH_VARS = ['id', 'ap', 'url' ]
ARUBA_PREAUTH_VARS = ['mac', 'apname', 'url' ]
RUCKUS_PREAUTH_VARS = ['mac', 'client_mac', 'url']
POST_POSTAUTH_VARS = POST_MAIN_VARS + ['session_hash', 'session_timeout', 'traffic_limit', 'next_conn_in']
POST_PPOSTAUTH_VARS = POST_MAIN_VARS
FREERAD_ADD_OP = r'+='
DEB_PREFIX = 'preauth'

"""
def getDebugStr(prefix, request = None, result = None):

    debugString = ''

    prevFuncName = (u, u, u, prevFuncName, u, u) = stack()[1]

    if request != None:        
        debugString = "{0} {1} request {2}".format(prefix, prevFuncName, request.values.to_dict(flat = False) )
   
    #if result != None:
    #    debugString = "{0} {1} {2}".format(prefix, prevFuncName, result )
            
    return debugString
"""

"""
Method get a HotSpot id via Shopster API.
IN
    request: Flask.Request
OUT
    None || one of the hotspot types as a string
"""
def getHotspotId(request):

    result = None
    h_id = None

    (u, u, u, currFuncName, u, u) = stack()[0]
    app.logger.debug( '{0} {1}() request args {2}'.format(DEB_PREFIX, currFuncName, request.values.to_dict(flat = False) ) )

    if request.method == 'POST':
        h_id = request.values.get('hotspot_id', None)
    elif request.method == 'GET':
        idNames = [ 'ap', 'apname', 'mac' ]
        for idName in idNames:
            try:
                h_id = request.args[idName]
                break
            except KeyError:
                continue
        
    #test cases    
    if h_id == 'outage':
        app.logger.error("preauth TEST CASE getHotspotId() shopster is down")
        result = 'outage'
    elif h_id == '44:d9:e7:48:81:63' or h_id == '44:d9:e7:48:84:74':
        result = 'ubiquity'
    elif h_id == 'ac:a3:1e:c5:8c:7c':
        result = 'aruba'
    elif h_id == '6caab339afe0':
        result = 'ruckus'
    elif h_id != None and request.method == 'POST':
        result = 'mikrotik'
#    else:
        
    app.logger.debug( "preauth getHotspotId() returns {0}".format(result) )

    return result 

"""
Method checks POST variable list for completness and correctness.
IN
    request: Flask.Request
OUT
    Bool
"""
def preauthGoodVars(request):

    result = False

    (u, u, u, currFuncName, u, u) = stack()[0]
    app.logger.debug( '{0} {1}() request args {2}'.format(DEB_PREFIX, currFuncName, request.values.to_dict(flat = False) ) )

    POSTVarsNames = session.get( 'POSTVarsNames', None )
    for POSTVarName in POSTVarsNames:
            POSTVarValue = request.values.get(POSTVarName, None)            
            if not POSTVarValue: #or not formatOk('preauthGoodVars', POSTVarName, POSTVarValue):
                app.logger.warning( "preauth preauthGoodVars() input var '{0}' check failed".format(POSTVarName) )
                #result = False
                return result
    if len( POSTVarsNames ):
        result = True        

    app.logger.debug( "preauth preauthGoodVars() returns {0}".format(result) )
    return result

"""
Method add/updates User model for later usage in postpostauth stage.
IN
    request: Flask.Request
OUT
    Bool
"""
#change userMAC to userID
def doSaveSessionData(request):

    (u, u, u, currFuncName, u, u) = stack()[0]
    app.logger.debug( '{0} {1}() request args {2}'.format(DEB_PREFIX, currFuncName, request.values.to_dict(flat = False) ) )
    
    result = False

    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')

    model = getPreauthModel(request)

    userMAC = userName = model.get('client_id', None)
    hotspotID = model.get('hotspot_id', None)
    entrypointID = model.get('entrypoint_id', None)
    originalURL = model.get('original_url', None)
    hotspotLoginURL = model.get('hotspot_login_url', None) 
    passWord = genPass()
    
    #print model

    if not userName or not passWord or not hotspotID or not entrypointID\
 or not originalURL or not hotspotLoginURL:
        return result

    try:
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()
        cursor.execute('UPDATE charon_clients\
                SET last_action_timestamp=now()\
                WHERE client_id=%s AND hotspot_id=%s;', 
                (userMAC, hotspotID)
            )
        cursor.execute('INSERT INTO charon_clients\
            (client_id,hotspot_id,entrypoint_id)\
            SELECT %s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM charon_clients WHERE client_id=%s AND hotspot_id=%s);',
            (userMAC, hotspotID, entrypointID, userMAC, hotspotID)
        )
        
        c.commit()
    except pgError as e:
        app.logger.error("preauth doSaveSessionData()" + str(e))
        c.close()
        return result
        
    try:
        cursor.execute('UPDATE charon_authentication\
            SET username=%s, password=%s\
            WHERE client_id=%s AND hotspot_id=%s;',
            (userName, passWord, userMAC, hotspotID)
        )
        cursor.execute('INSERT INTO charon_authentication\
            (username,password,client_id,hotspot_id)\
            SELECT %s,%s,%s,%s WHERE NOT EXISTS\
                (SELECT 1 FROM charon_authentication\
                WHERE client_id = %s and hotspot_id = %s);', 
            (userName, passWord, userMAC, hotspotID, userMAC, hotspotID)
        )
        cursor.execute('UPDATE charon_urls\
            SET origin_url=%s,hotspot_login_url=%s\
            WHERE client_id=%s AND hotspot_id=%s;',
            (originalURL, hotspotLoginURL, userMAC, hotspotID)
        )
        cursor.execute('INSERT INTO charon_urls\
            (origin_url,hotspot_login_url,client_id,hotspot_id)\
            SELECT %s,%s,%s,%s WHERE NOT EXISTS\
                (SELECT 1 FROM charon_urls\
                WHERE client_id = %s and hotspot_id = %s);', 
            (originalURL, hotspotLoginURL, userMAC, hotspotID, userMAC, hotspotID)
        )
        c.commit()
        result = True
    except pgError as e:
        app.logger.error("preauth doSaveSessionData()" + str(e))
    finally:
        c.close()

    app.logger.debug( "preauth doSaveSessionData() returns '{0}'".format(result) )

    return result


"""
Client enters the systems at this point. His POST request contains
IN
    client_id: str (as a MAC)
    hotspot_id: str (as a MAC)
    entrypoint_id: str (as a MAC)
    original_url: str
    hotspot_login_url: str
OUT 
    str
"""
@app.route("/preauth/", methods=['POST', 'GET'])
def doPreauth():

    result = None
    POSTVarsNames = [ ]

    hotspotType = getHotspotId(request)

    if hotspotType == 'mikrotik':
        POSTVarsNames = MT_PREAUTH_VARS
    elif hotspotType == 'ubiquity':    
        POSTVarsNames = UNI_PREAUTH_VARS         
    elif hotspotType == 'aruba':    
        POSTVarsNames = ARUBA_PREAUTH_VARS  
    elif hotspotType == 'ruckus':    
        POSTVarsNames = RUCKUS_PREAUTH_VARS                
    elif hotspotType == 'outage': #test case
        hotspotType = None
        POSTVarsNames = MT_PREAUTH_VARS

    session['hotspotType'] = hotspotType    
    session['POSTVarsNames'] = POSTVarsNames    

    varsOk = preauthGoodVars(request) 

    if hotspotType is not None:        
        waitTime = idleCheck(request)
        
        if waitTime != False and waitTime:
            extradata = {'wait_time': waitTime}
            result = render_template('preauth_idle.html', extradata = extradata)
            r = make_response( result )
            r.headers['Strict-Transport-Security'] = 'max-age=0'
            return r

        if not doSaveSessionData(request):    
            result = render_template('error.html') 
            return result

        session['model'] = getPreauthTemplateData(request)        
        extradata = session['model']

        result = render_template('preauth.html', extradata = extradata, url = app.config.get('SHOPSTER_URL'))
        r = make_response( result )
        r.headers['Strict-Transport-Security'] = 'max-age=0'
        return r

    elif varsOk:                                #didnt get hotspot type and vars are ok then shopster system is down
        result = render_template('shopster_outage.html')
        return result
    
    result = render_template('error.html')
    return result

