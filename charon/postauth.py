from charon import app
from flask import request, render_template, abort, json
from re import search as regex_search
from requests import post
from hashlib import sha256
from datetime import datetime
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps
from base64 import b64encode
from misc import *
from ubiquity import isUbiquity, allowUbiquitySubs

POST_MAIN_VARS = ['client_id', 'hotspot_id', 'entrypoint_id']
POST_POSTAUTH_VARS = POST_MAIN_VARS + ['session_hash', 'session_timeout', 'traffic_limit', 'next_conn_in']
FREERAD_ADD_OP = r'+='
DEB_PREFIX = 'postauth'

########################postauth

"""
The func checks whether HTTP Authorization is valid or not.
IN
    request: Flask.Request
OUT
    Bool
"""
def authenticated(request):

    a = request.headers.get('Authorization', None)
    logIt( app.logger.debug, DEB_PREFIX, 'Authorization HTTP header', a )

    result = False
         
    if a is not None:
        try:
            u, recvdHash = a.split()
        except ValueError:
            logIt( app.logger.warning, DEB_PREFIX, 'wrong header format' )
            result = False            
            return result
        secret = app.config.get('SHOPSTER_SECRET')
        day = datetime.now().strftime('%d')
        salt = '{0}:{1}'.format(secret, day)
        expectedHash = b64encode( sha256(salt).hexdigest() )
        logIt( app.logger.debug, DEB_PREFIX, 'received hash "{0}" expected hash "{1}"'.format( recvdHash, expectedHash ) )
        if expectedHash == recvdHash:
            result = True

    logIt( app.logger.debug, DEB_PREFIX, ' returns ', result )

    return result

"""
The func inserts/updates user session limits data in charon_limits database.
IN
    request: Flask.Request
OUT
    Bool
"""
def updateSessionLimits(request):
    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')

    result = False
    inputJSON = getJson(request)
    logIt( app.logger.debug, DEB_PREFIX, 'request json', json_dumps(inputJSON) )

    clientID = extractUserName(request)
    idleTime = extractIdleTime(request)
    authType = extractAuthType(request)
    hotspotID = extractHotspotID(request)
    sessionLimit = extractSessionLimit(request)
    traffLimit = extractTraffLimit(request)

    if None in ( clientID, idleTime, authType, hotspotID, sessionLimit, traffLimit):
        logIt( app.logger.error, DEB_PREFIX, 'Not enough data. client {0}, idle {1}, authtype {2}, hotspot {3} TO {4} traff {5}'.format(\
            clientID, idleTime, authType, hotspotID, sessionLimit, traffLimit )
        )
        logIt( app.logger.debug, DEB_PREFIX, 'returns', result )
        return result


    try:
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()
        cursor.execute('UPDATE charon_limits\
                SET session_hash=%s,idle_time=%s,session_limit=%s,traffic_limit=%s\
                WHERE client_id=%s AND hotspot_id=%s;', 
                (authType, idleTime, sessionLimit, traffLimit, clientID, hotspotID)
            )
        cursor.execute('INSERT INTO charon_limits\
            (session_hash,idle_time,session_limit,traffic_limit,client_id,hotspot_id)\
            SELECT %s,%s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM charon_limits WHERE client_id=%s AND hotspot_id=%s);',
            (authType, idleTime, sessionLimit, traffLimit, clientID, hotspotID,
 clientID, hotspotID)
        )
        c.commit()
        result = True
    except pgError as e:
        logIt( app.logger.error, DEB_PREFIX, 'database exception', str(e) )
    finally:
        c.close()

    logIt( app.logger.debug, DEB_PREFIX, 'returns', result )

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
    logIt( app.logger.debug, DEB_PREFIX, 'request json', json_dumps(inputJSON) )

    userMAC = userName = extractUserName(request)
    passWord = genPass()
    sessionTimeout = extractSessionLimit(request)
    traffLimit = extractTraffLimit(request)

    if None in (userName, passWord, sessionTimeout, traffLimit):
        logIt( app.logger.error, DEB_PREFIX, 'Not enough data. userName {0}, pass {1}, TO {2}, traff {3}'.format( userName, passWord, sessionTimeout, traffLimit)
        )
        logIt( app.logger.debug, DEB_PREFIX, 'returns', result )
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
        cursor.execute('INSERT INTO radreply \
            (username,attribute,op,value) \
            SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username=%s AND attribute=%s AND op=%s);',
            (userName, 'Mikrotik-Total-Limit', FREERAD_ADD_OP, traffLimit, userName, 'Mikrotik-Total-Limit', FREERAD_ADD_OP)
        )

        c.commit()
        result = True
    except pgError as e:
        logIt( app.logger.error, DEB_PREFIX, 'database exception', str(e) )
    finally:
        c.close()

    logIt( app.logger.debug, DEB_PREFIX, 'returns', result )

    return result

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

    logIt( app.logger.debug, DEB_PREFIX, 'request json', json_dumps(inputJSON) )

    for POSTVarName in POSTVarsNames:
        POSTVarValue = inputJSON.get(POSTVarName, None)
        if POSTVarValue == None:
            logIt( app.logger.error, DEB_PREFIX, 'input var {0} check failed'.format(POSTVarName) )
            result = False
            break

    logIt( app.logger.debug, DEB_PREFIX, 'returns', result )

    return result

"""
Func validates its input POST vars and inserts data for RADIUS subsystem in a database.
Shopster calls this API func in postauth phase to allow a particular authenticated subscriber.
IN
    client_id: str (as a MAC)
    hotspot_id: str (as a MAC)
    entrypoint_id: str (as a MAC)
    session_hash: str
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

    if isJson(request) and postauthGoodVars(request):
        if isUbiquity(request) and allowUbiquitySubs(request) and updateSessionLimits(request):
            return json.jsonify(auth = 'ok', result = 'ok')
        elif allowRadiusSubs(request) and updateSessionLimits(request):        
            return json.jsonify(auth = 'ok', result = 'ok')
        
    return json.jsonify(auth = 'ok', result = 'fail')
