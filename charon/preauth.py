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
    None || one of the hotspot types
"""
def getHotspotId(request):
    h_id = request.values.get('hotspot_id', None)    
    if h_id == 'outage': return None
    return 'mikrotik'

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
    
    clientID = request.values.get('client_id', None)
    hotspotID = request.values.get('hotspot_id', None)
    entrypointID = request.values.get('entrypoint_id', None)
    
    if not clientID or not hotspotID:
        return False

    try:        
        c = connect(host = h, user = u, password = p, database = d)
        #print "idleCheck", c
        cursor = c.cursor()
        #print "idleCheck before q", clientID, hotspotID

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
        result = cursor.fetchone()
        #c.close()
        if not result:
            return 0
        (waitTime,) = result
        #print "idleCheck after q", waitTime
        return waitTime
    except pgError as e:
        app.logger.error("preauth idleCheck() " + str(e))
    finally:
        c.close()

    return False

"""
Method checks POST variable list for completness and correctness.
IN
    request: Flask.Request
OUT
    Bool
"""
def preauthGoodVars(request):
    POSTVarsNames = POST_PREAUTH_VARS
    for POSTVarName in POSTVarsNames:
            POSTVarValue = request.values.get(POSTVarName, None)            
            if not POSTVarValue or not formatOk('preauthGoodVars', POSTVarName, POSTVarValue):
                return False
    return True

"""
Method add/updates User model for later usage in postpostauth stage.
IN
    request: Flask.Request
OUT
    Bool
"""
#change userMAC to userID
#change to UPSERT request
def doSaveSessionData(request):
    
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
        return False

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

        #print "doSaveSessionData after INSERT into charon_clients", userMAC, hotspotID, entrypointID
        c.commit()
    except pgError as e:
        app.logger.error("preauth doSaveSessionData()" + str(e))
        c.close()
        return False
        
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
        c.close()
        return True
    except pgError as e:
        app.logger.error("preauth doSaveSessionData()" + str(e))
        c.close()

    return False


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
    
    hotspotType = getHotspotId(request)
    varsOk = preauthGoodVars(request)    
    if hotspotType is not None and varsOk:        
        waitTime = idleCheck(request)
        
        if waitTime != False and waitTime:
            extradata = {'wait_time': waitTime}
            return render_template('preauth_idle.html', extradata = extradata)
        if not doSaveSessionData(request):
            return render_template('error.html')
        extradata = {}
        for POSTVarsName in POSTVarsNames:
            extradata[POSTVarsName] = request.values.get(POSTVarsName)        
        a = render_template('preauth.html', extradata = extradata, url = app.config.get('SHOPSTER_URL'))
        return a
    elif varsOk:                                #shopster system is down
        return render_template('shopster_outage.html')
    
    return render_template('error.html')

