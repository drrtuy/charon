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

from misc import formatOk, genPass

########################postauth

"""
The func checks whether HTTP Authorization is valid or not.
IN
    request: Flask.Request
OUT
    Bool
"""
#FIX add Basic
def authenticated(request):

    a = request.headers.get('Authorization', None)
    app.logger.debug( "postauth authenticated() Authorization HTTP header '{0}'".format(a)) 

    result = False
         
    if a is not None:
        secret = app.config.get('SHOPSTER_SECRET')
        today = str(date.today().day)
        expectedHash = sha256(secret.join(today)).hexdigest()
        if expectedHash == a:
            result = True

    app.logger.debug( "postauth authenticated() returns '{0}'".format(result))

    return result

def getJson(request): 
    j = request.get_json()

    #app.logger.debug("postauth getJson() json '{0}'".format(j))

    jsonAsDict = {}

    if isinstance(j, dict):
        jsonAsDict = j
    else:
        jsonAsDict = json_loads(j)

    #app.logger.debug("postauth getJson() returns '{0}'".format(jsonAsDict))

    return jsonAsDict

"""
The func returns client MAC as username.
IN
    request: Flask.Request
OUT
    str
"""
def extractUserName(request):
    return getJson(request).get('client_id', None)

def extractSessionLimit(request):    
    return getJson(request).get('session_timeout', None)

def extractTraffLimit(request):
    return getJson(request).get('traffic_limit', None)

def extractIdleTime(request):
    return getJson(request).get('next_conn_in', None)

def extractAuthType(request):
    return getJson(request).get('auth_type', None)

def extractHotspotID(request):
    return getJson(request).get('hotspot_id', None)

def extractClientID(request):
    return getJson(request).get('client_id', None)


"""
The func inserts/updates user session limits data in charon_limits database.
IN
    request: Flask.Request
OUT
    Bool
"""
#fix it change to UPSERT request
def updateSessionLimits(request):
    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')

    result = False
    inputJSON = getJson(request)
    app.logger.debug( "postauth updateSessionLimits() request json '{0}'".format(json_dumps(inputJSON)) )

    clientID = extractUserName(request)
    idleTime = extractIdleTime(request)
    authType = extractAuthType(request)
    hotspotID = extractHotspotID(request)
    sessionLimit = extractSessionLimit(request)
    traffLimit = extractTraffLimit(request)


    if not clientID or not idleTime or not authType or not hotspotID\
 or not sessionLimit or not traffLimit:
        app.logger.debug( "postauth updateSessionLimits() returns '{0}'".format(result) )
        return result

    try:
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()
        cursor.execute('UPDATE charon_limits\
                SET auth_type=%s,idle_time=%s,session_limit=%s,traffic_limit=%s\
                WHERE client_id=%s AND hotspot_id=%s;', 
                (authType, idleTime, sessionLimit, traffLimit, clientID, hotspotID)
            )
        cursor.execute('INSERT INTO charon_limits\
            (auth_type,idle_time,session_limit,traffic_limit,client_id,hotspot_id)\
            SELECT %s,%s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM charon_limits WHERE client_id=%s AND hotspot_id=%s);',
            (authType, idleTime, sessionLimit, traffLimit, clientID, hotspotID,
 clientID, hotspotID)
        )
        c.commit()
        c.close()
        result = True
    except pgError as e:
        app.logger.error("postauth updateSessionLimits()" + str(e))
        c.close()

    app.logger.debug( "postauth updateSessionLimits() returns '{0}'".format(result) )

    return result

"""
The func inserts user data into RADIUS database.
IN
    request: Flask.Request
OUT
    Bool
"""
#passWord must be taken from db
def allowRadiusSubs(request):
    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')

    result = False
    inputJSON = getJson(request)
    app.logger.debug( "postauth allowRadiusSubs() request json '{0}'".format(json_dumps(inputJSON)) )

    userMAC = userName = extractUserName(request)
    passWord = genPass()
    sessionTimeout = extractSessionLimit(request)
    traffLimit = extractTraffLimit(request)

    if not userName or not passWord or not sessionTimeout or not traffLimit:
        app.logger.debug( "postauth postauthGoodVars() returns '{0}'".format(result) )
        return result

    try:        
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()

        cursor.execute('UPDATE radcheck\
            SET value=%s\
            WHERE username=%s AND attribute=%s AND op=%s;', 
            (passWord, userName, 'Cleartext-Password', FREERAD_ADD_OP)
        )        
        cursor.execute('INSERT INTO radcheck\
            (username,attribute,op,value)\
            SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM radcheck WHERE username=%s AND attribute=%s AND op=%s);',
            (userName, 'Cleartext-Password', FREERAD_ADD_OP, passWord, userName, 'Cleartext-Password', FREERAD_ADD_OP)
        )

        cursor.execute('UPDATE radreply\
            SET value=%s\
            WHERE username=%s AND attribute=%s AND op=%s;', 
            (sessionTimeout, userName, 'Session-Timeout', FREERAD_ADD_OP)
        )        
        cursor.execute('INSERT INTO radreply\
            (username,attribute,op,value)\
            SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username=%s AND attribute=%s AND op=%s);',
            (userName, 'Session-Timeout', FREERAD_ADD_OP, sessionTimeout, userName, 'Session-Timeout', FREERAD_ADD_OP)
        )

        cursor.execute('UPDATE radreply\
            SET value=%s\
            WHERE username=%s AND attribute=%s AND op=%s;', 
            (traffLimit, userName, 'Mikrotik-Total-Limit', FREERAD_ADD_OP)
        )        
        cursor.execute('INSERT INTO radreply\
            (username,attribute,op,value)\
            SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username=%s AND attribute=%s AND op=%s);',
            (userName, 'Mikrotik-Total-Limit', FREERAD_ADD_OP, traffLimit, userName, 'Mikrotik-Total-Limit', FREERAD_ADD_OP)
        )

        c.commit()
        c.close()

        result = True
    except pgError as e:
        app.logger.error("postauth nallowRadiusSubs()" + str(e))
        c.close()

    app.logger.debug( "postauth allowRadiusSubs() returns '{0}'".format(result) )
    return result

"""
Method checks request content type.
IN
    request: Flask.Request
OUT
    Bool
"""
def postauthContentType(request):
    app.logger.debug("postauth postauthContentType() returns '{0}'".format(request.content_type))
    return request.content_type == 'application/json'
    

"""
Method checks POST variable list for completness and correctness.
IN
    request: Flask.Request
OUT
    Bool
"""
def postauthGoodVars(request):
    POSTVarsNames = POST_POSTAUTH_VARS
    result = True

    inputJSON = getJson(request)

    app.logger.debug( "postauth postauthGoodVars() request json '{0}'".format(json_dumps(inputJSON)) )

    for POSTVarName in POSTVarsNames:
        POSTVarValue = inputJSON.get(POSTVarName, None)
        if not POSTVarValue or not formatOk('postauthGoodVars', POSTVarName, POSTVarValue):
            result = False
            break

    app.logger.debug( "postauth postauthGoodVars() returns '{0}'".format(result) )

    return result

"""
Func validates its input POST vars and inserts data for RADIUS subsystem in a database.
Shopster calls this API func in postauth phase to allow a particular authenticated subscriber.
IN
    client_id: str (as a MAC)
    hotspot_id: str (as a MAC)
    entrypoint_id: str (as a MAC)
    auth_type: str
    session_timeout: pos int (in secs)
    traffic_limit: pos float (in MB)
    next_conn_in: pos int (in secs)
OUT 
    str
"""
@app.route("/v1/radius/subs/", methods=['POST'])
def doPostauth():

    if not authenticated(request):
        return json.jsonify(auth = 'fail', result = 'fail')

    if postauthContentType(request) and postauthGoodVars(request)\
     and allowRadiusSubs(request) and updateSessionLimits(request): 
        return json.jsonify(auth = 'ok', result = 'ok')
        
    return json.jsonify(auth = 'ok', result = 'fail')

