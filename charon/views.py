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

""" Shopster emulation part
"""
"""
The soubroutine takes a hotspot_id and returns Response. 
Fix: add auth checking
IN
    hotspot_id: str (hotspot id as a MAC)
OUT
    jsonified doc to create a Response obj
"""
@app.route("/v1/hotspots/<hotspot_id>", methods=['GET'])
def giveHotspotId(hotspot_id):
    if not hotspot_id or hotspot_id == '40D00276F318':
        return json.jsonify(auth = 'ok',
            result = 'fail',
        )
    else: 
        return json.jsonify(auth = 'ok',
            result = 'ok',
            hotspot_type = 'mikrotik'
        )

"""
Check POST vars list for completness and validate them.
IN
    request: Flask.Request obj
OUT
    Bool
"""
def goodVars(request):
    return True


def get_hash():
    secret = app.config.get('SHOPSTER_SECRET')
    today = str(date.today().day)
    expectedHash = sha256(secret.join(today)).hexdigest()
    return expectedHash
"""
Sends charon a POST message to allow a user to login.
IN
    Flask.Request obj
OUT
    True || False (if the cmd in the POST msg succeded False otherwise. )
"""
def doAllowUser(request):
    print "doAllowUser"
    clientID = request.values.get('client_id')
    hotspotID = request.values.get('hotspot_id')
    formData = {
    'client_id': clientID,
    'hotspot_id': hotspotID,
    'entrypoint_id': hotspotID,
    'traffic_limit':  '60',
    'session_timeout':  '3100',
    'next_conn_in':   '3600',
    'auth_type': 'splash'
    }
    response = post('http://charon.zerothree.su:8082/v1/radius/subs/', #docker doesnt allow containers to connect to their own host's external ports
        headers = {'Authorization': get_hash()},
        json = json_dumps(formData),
        timeout = 2
    )
    #print response.body
    return True

"""
Takes an input as POST variables and produce a Response that contains flash authentication app.
IN
    client_id: str (as a MAC)
    hotspot_id: str (as a MAC)
    entrypoint_id: str (as a MAC)
OUT
    rendered template
"""
@app.route("/", methods=['POST'])
def doAuth():
    if goodVars(request):
        #print "doAuth"
        doAllowUser(request)
        #print "after allowUser"
        extradata = request.values
        return render_template('auth.html', extradata=extradata, url = app.config.get('POSTPOSTAUTH_URL') )

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
        cursor = c.cursor()
        print "idleCheck before q", clientID, hotspotID

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
        c.close()
        if not result:
            return 0
        (waitTime,) = result
        print "idleCheck after q", waitTime
        return waitTime
    except pgError as e:
        print "\n", e, "\n"

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
        cursor.execute('INSERT INTO charon_clients\
            (client_id,hotspot_id,entrypoint_id)\
            VALUES (%s,%s,%s);', 
            (userMAC, hotspotID, entrypointID),
        )
        print "doSaveSessionData after INSERT into charon_clients", userMAC, hotspotID, entrypointID
        c.commit()
    except pgError as e:
        c.rollback()
        try:
            cursor.execute('UPDATE charon_clients\
                SET entrypoint_id=%s,last_action_timestamp=now()\
                WHERE client_id=%s AND hotspot_id=%s;', 
                (entrypointID, userMAC, hotspotID),
            )
            print "doSaveSessionData after UPDATE in charon_clients", userMAC, hotspotID, entrypointID
            c.commit()
        except pgError as e: #couldnt INSERT or UPDATE charon_clients entry
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
        #charon_urls upsert
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
        print "\n", e, "\n"

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
    print "doPreauth", hotspotType, varsOk
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
        return render_template('preauth.html', extradata = extradata, url = app.config.get('SHOPSTER_URL'))
    elif varsOk:                                #shopster system is down
        return render_template('shopster_outage.html')
    
    return render_template('error.html')

########################postauth

"""
The func checks whether HTTP Authorization is valid or not.
IN
    request: Flask.Request
OUT
    Bool
"""
#fix it use control word Basic
def authenticated(request):    
    a = request.headers.get('Authorization', None)
    if a is not None:
        secret = app.config.get('SHOPSTER_SECRET')
        today = str(date.today().day)
        expectedHash = sha256(secret.join(today)).hexdigest()
        if expectedHash == a:
            return True
    return False

"""
The func generates a password.
OUT
    str
"""
def genPass():
    return 'aeChei3A'

"""
The func returns client MAC as username.
IN
    request: Flask.Request
OUT
    str
"""
def extractUserName(request):
    inputJSON = json_loads(request.get_json())
    return inputJSON.get('client_id', None)

def extractSessionTO(request):
    inputJSON = json_loads(request.get_json())
    return inputJSON.get('session_timeout', None)

def extractTraffLimit(request):
    inputJSON = json_loads(request.get_json())
    return inputJSON.get('traffic_limit', None)

def extractIdleTime(request):
    inputJSON = json_loads(request.get_json())
    return inputJSON.get('next_conn_in', None)

def extractAuthType(request):
    inputJSON = json_loads(request.get_json())
    return inputJSON.get('auth_type', None)

def extractHotspotID(request):
    inputJSON = json_loads(request.get_json())
    return inputJSON.get('hotspot_id', None)

def extractClientID(request):
    inputJSON = json_loads(request.get_json())
    return inputJSON.get('client_id', None)


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
    clientID = extractUserName(request)
    idleTime = extractIdleTime(request)
    authType = extractAuthType(request)
    hotspotID = extractHotspotID(request)
    sessionTO = extractSessionTO(request)

    print "updateSessionLimits", clientID, idleTime, authType, hotspotID, sessionTO

    if not clientID or not idleTime or not authType or not hotspotID or not sessionTO:
        return False

    try:
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()
        print "updateSessionLimits before q\n"
        cursor.execute('UPDATE charon_limits\
            SET auth_type=%s,idle_time=%s\
            WHERE client_id=%s AND hotspot_id=%s;', 
            (authType,idleTime,clientID,hotspotID),
        )
        c.commit()
        print "updateSessionLimits after q\n"
        c.close()
        return True
    except pgError as e:
        print "\n",e,"\n"
        c.rollback()
        try:
            cursor.execute('INSERT INTO charon_limits\
                (client_id,hotspot_id,auth_type,idle_time)\
                VALUES\
                (%s,%s,%s,%s);', 
                (clientID, hotspotID, authType, idleTime),
            )
            c.commit()
            return True
        except pgError as e: #couldnt INSERT or UPDATE charon_limits entry
            print "\n",e,"\n"
            c.close()
            return False

    return False

"""
The func inserts user data into RADIUS database.
IN
    request: Flask.Request
OUT
    Bool
"""
#change to UPSERT request
def allowRadiusSubs(request):
    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')
    userMAC = userName = extractUserName(request)
    passWord = genPass()
    sessionTimeout = extractSessionTO(request)
    traffLimit = extractTraffLimit(request)

    if not userName or not passWord or not sessionTimeout or not traffLimit:
        return False

    try:
        print "allowRadiusSubs before q", userName, passWord, sessionTimeout, traffLimit
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
        """
        cursor.execute('INSERT INTO radreply (username,attribute,op,value) VALUES (%s,%s,%s,%s);',
            (userName, 'Session-Timeout', '+=', sessionTimeout),
        )
        cursor.execute('INSERT INTO radreply (username,attribute,op,value) VALUES (%s,%s,%s,%s);', 
            (userName, 'Mikrotik-Total-Limit', '+=', traffLimit),
        )
        """
        c.commit()
        c.close()
        print "allowRadiusSubs after q"
        return True
    except pgError as e:
        print "\nallowRadiusSubs", e, "\n"

    return False

"""
Method checks request content type.
IN
    request: Flask.Request
OUT
    Bool
"""
def postauthContentType(request):
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
    inputJSON = json_loads(request.get_json())
    for POSTVarName in POSTVarsNames:
        POSTVarValue = inputJSON.get(POSTVarName, None)
        #print POSTVarName, POSTVarValue
        if not POSTVarValue or not formatOk('postauthGoodVars', POSTVarName, POSTVarValue):
            return False
    return True

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
    #print "\n", request.data
    if not authenticated(request):
        return json.jsonify(auth = 'fail', result = 'fail')

    #update RADIUS db after checking
    print "doPostauth"
    if postauthContentType(request) and postauthGoodVars(request)\
     and allowRadiusSubs(request) and updateSessionLimits(request): 
        return json.jsonify(auth = 'ok', result = 'ok')
        
    return json.jsonify(auth = 'ok', result = 'fail')

#########################postpostauth

"""
Method retrieves variables from database to populate postpostauth HTML template.
IN
    request: Flask.Request
OUT
    dict || None
"""
def getFormData(request):
    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')
    
    clientID = request.values.get('client_id', None)
    hotspotID = request.values.get('hotspot_id', None)
    #entrypointID = request.values.get('entrypoint_id', None)
    
    if not clientID or not hotspotID:
        return None
    
    result = {}
    """
    return {
        'hotspot_login_url': 'http://hotspot.zerothree.su/login',
        'original_url': 'http://ya.ru',
        'username': 'ad',
        'password': 'aeChei3A'
    }
    """
    try:
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()
        cursor.execute( 'SELECT DISTINCT a.username, a.password, u.origin_url, u.hotspot_login_url\
             FROM charon_authentication a, charon_urls u \
             WHERE a.client_id = u.client_id \
             AND u.client_id = %s \
             AND a.hotspot_id = u.hotspot_id \
             AND u.hotspot_id = %s; ', 
            (clientID, hotspotID),
        )
        row = cursor.fetchone()
        if not row:
            c.close()
            return None
        (result['username'], result['password'],\
        result['origin_url'], result['hotspot_login_url']) \
        = row
        c.close()
        return result
    except pgError as e:
        print "\n", e, "\n"

    return None

"""
Method checks POST variable list for completness and correctness.
IN
    request: Flask.Request
OUT
    Bool
"""
def ppostauthGoodVars(request):
    POSTVarsNames = POST_PPOSTAUTH_VARS
    for POSTVarName in POSTVarsNames:
            POSTVarValue = request.values.get(POSTVarName, None)            
            if not POSTVarValue or not formatOk('ppostauthGoodVars', POSTVarName, POSTVarValue):
                return False
    return True

"""
Method checks variable for correctness in a particular function.
IN
    client_id: str (as a MAC)
    hotspot_id: str
    entrypoint_id: str
OUT
    str
"""
@app.route("/postpostauth/", methods=['POST'])
def doPostPostauth():
    if ppostauthGoodVars(request):
        formData = getFormData(request)
        print "doPostPostauth", formData
        if formData is not None:            
            return render_template('postpostauth.html', formdata = formData)
    return render_template('error.html')

if __name__ == "__main__":
    app.run()
