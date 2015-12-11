from charon import app
from flask import request, render_template, abort, json
from re import search as regex_search
from requests import post
from hashlib import sha256
from datetime import date
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps

from misc import formatOk, genPass

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
Method get a HotSpot id via Shopster API.
IN
    request: Flask.Request
OUT
    None || one of the hotspot types as a string
"""
def getHotspotId(request):
    result = None
    if request.form:
        app.logger.debug( "preauth getHotspotId() request POST data {0}".format(json_dumps(request.form)) )

    h_id = request.values.get('hotspot_id', None)    
    if h_id == 'outage':
        app.logger.error("preauth getHotspotId() shopster is down")
        return result
    result = 'mikrotik'

    if request.form:
        app.logger.debug( "preauth getHotspotId() returns {}".format(result) )

    return result 

"""
Method checks whether client must wait for the idle timeout
IN
    request: Flask.Request
OUT
    int || False (in case of failure)
"""
def idleCheck(request):

    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')
   
    if request.form:
        app.logger.debug( "preauth idleCheck() request POST data {0}".format(json_dumps(request.form)) )

    clientID = request.values.get('client_id', None)
    hotspotID = request.values.get('hotspot_id', None)
    entrypointID = request.values.get('entrypoint_id', None)

    result = False   
 
    if not clientID or not hotspotID:
        app.logger.debug( "preauth idleCheck() returns {0}".format(result) )
        return result 

    try:        
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()

        cursor.execute('SELECT\
            (SELECT idle_time from charon_limits WHERE client_id=%s AND hotspot_id=%s)\
             - \
            round(extract(mins from now()-acctstoptime)*60 + extract(secs from now()-acctstoptime)) AS t\
            FROM radacct\
            WHERE acctstoptime > now() - \
            make_interval(secs:=(SELECT idle_time from charon_limits WHERE client_id=%s AND hotspot_id=%s))\
          ORDER BY t DESC LIMIT 1;',
            (clientID, hotspotID, clientID, hotspotID)
        )  
        row = cursor.fetchone()
        if not row:
            waitTime = 0
        else:
            (waitTime,) = row

        #app.logger.debug( "preauth idleCheck() returns {0}".format(waitTime) )    

        result = waitTime
    except pgError as e:
        app.logger.error("preauth idleCheck() " + str(e))
    finally:
        c.close()

    app.logger.debug( "preauth idleCheck() returns {0}".format(result) )

    return result

"""
Method checks POST variable list for completness and correctness.
IN
    request: Flask.Request
OUT
    Bool
"""
def preauthGoodVars(request):

    result = True

    if request.form:
        app.logger.debug( "preauth preauthGoodVars() request POST data {0}".format(json_dumps(request.form)) )
    POSTVarsNames = POST_PREAUTH_VARS
    for POSTVarName in POSTVarsNames:
            POSTVarValue = request.values.get(POSTVarName, None)            
            if not POSTVarValue or not formatOk('preauthGoodVars', POSTVarName, POSTVarValue):
                app.logger.warning( "preauth preauthGoodVars() input var '{0}' check failed".format(POSTVarName) )
                result = False
                return result

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
    
    app.logger.debug( "preauth doSaveSessionData() request POST data {0}".format(json_dumps(request.form)) )
    
    result = False

    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')
    userMAC = userName = request.values.get('client_id', None)
    hotspotID = request.values.get('hotspot_id', None)
    entrypointID = request.values.get('entrypoint_id', None)
    originalURL = request.values.get('original_url', None)
    hotspotLoginURL = request.values.get('hotspot_login_url', None) 
    passWord = genPass()
    
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
@app.route("/preauth/", methods=['POST'])
def doPreauth():
    POSTVarsNames = POST_PREAUTH_VARS    

    result = None

    hotspotType = getHotspotId(request)
    varsOk = preauthGoodVars(request)    
    if hotspotType is not None and varsOk:        
        waitTime = idleCheck(request)
        
        if waitTime != False and waitTime:
            extradata = {'wait_time': waitTime}
            result = render_template('preauth_idle.html', extradata = extradata)
            return result
        if not doSaveSessionData(request):    
            result = render_template('error.html') 
            return result
        extradata = {}
        for POSTVarsName in POSTVarsNames:
            extradata[POSTVarsName] = request.values.get(POSTVarsName)        
        result = render_template('preauth.html', extradata = extradata, url = app.config.get('SHOPSTER_URL'))
        return result
    elif varsOk:                                #shopster system is down
        result = render_template('shopster_outage.html')
        return result
    
    result = render_template('error.html')
    return result

