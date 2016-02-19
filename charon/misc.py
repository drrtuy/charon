from charon import app
from flask import request, render_template, abort, json, session
from re import search as regex_search
from requests import post
from hashlib import sha256
from datetime import date
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps
from inspect import stack
from itertools import cycle
#from model import *

MAC_REGEXP = r'^([0-9a-fA-F][0-9a-fA-F][:-]){5}([0-9a-fA-F][0-9a-fA-F])$'
SN_REGEXP = r'([0-9a-fA-F]){12}'
POSINT_REGEXP = r'^\d*$'
EMPTY_REGEXP = r'^$'
ANY_REGEXP = r'^.*$'
POST_MAIN_VARS = ['client_id', 'hotspot_id', 'entrypoint_id']
POST_PREAUTH_VARS = POST_MAIN_VARS + ['hotspot_login_url']
POST_POSTAUTH_VARS = POST_MAIN_VARS + ['session_hash', 'session_timeout', 'traffic_limit', 'next_conn_in']
POST_PPOSTAUTH_VARS = POST_MAIN_VARS
FREERAD_ADD_OP = r'+='
MB=1048576
DEB_PREFIX = 'misc'

def xorString(message, key):
    cyphered = ''.join( chr (ord(c) ^ ord(k) ) for c,k in zip(message, cycle(key) ) )
    return cyphered

"""
Project logger wrapper.
IN
    logger: logger with a paritucular level.
    prefix: str
    second: str
    third: str
OUT
    void
"""
def logIt(logger, prefix, second = None, third = None):

    debugString = ''

    ( u, u, u, prevFuncName, u, u ) = stack()[1]

    if third == None:
        debugString = '{0} {1} {2}'.format( prefix, prevFuncName, second )
    else:
        debugString = '{0} {1} {2} {3}'.format( prefix, prevFuncName, second, third )
               
    if logger:
        logger(debugString)

#def logArgs(prefix, args):
#    return logIt( app.logger.debug, prefix, ' request args ', args )

#def logResult(prefix, result):
#    return logIt( app.logger.debug, prefix, ' returns ', result )


"""
The func generates a password. Static is enough 
OUT
    str
"""
def genPass():
    return 'aeChei3A'

"""
LEGACY. SHOULD BE REMOVED
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
        'session_hash': r'.*'
    }
    ppostauthGoodVars = {
        'client_id': MAC_REGEXP,
        'hotspot_id': SN_REGEXP,
        'entrypoint_id': SN_REGEXP,
    }

    if fname == 'preauthGoodVars':
        if name == 'hotspot_id' and value == 'outage': return True    #for unit tests
        try:
            if regex_search( preauthRegexps.get(name, EMPTY_REGEXP), value ):    
                pass
                #return True
        except TypeError as e:
                print "name '{0}' value '{1}' type '{2}'".format(name, value, type(value) )
        return True        
    elif fname == 'postauthGoodVars':
        try:
            if regex_search( postauthRegexps.get(name, EMPTY_REGEXP), str(value) ):
                pass
                #return True
        except TypeError as e:
            print "name '{0}' value '{1}' type '{2}'".format(name, value, type(value) )
        return True #doesn't check variable format 
    elif fname == 'ppostauthGoodVars':
        try:
            if regex_search( ppostauthGoodVars.get(name, EMPTY_REGEXP), value ):    
                return True        
        except TypeError as e:
            print "name '{0}' value '{1}' type '{2}'".format(name, value, type(value) )

    return False


def getJson(request): 
    j = request.get_json()

    #app.logger.debug("misc getJson() json '{0}'".format(j))

    jsonAsDict = {}

    if isinstance(j, dict):
        jsonAsDict = j
    else:
        jsonAsDict = json_loads(j)

    #app.logger.debug("misc getJson() returns '{0}'".format(jsonAsDict))

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

def extractEntryPointID(request):    
    return getJson(request).get('entrypoint_id', None)

def extractTraffLimit(request):    
    try: 
        tL = getJson(request).get('traffic_limit', None)
        return int(tL) * MB
    except TypeError, ValueError:
        return 0

def extractIdleTime(request):
    return getJson(request).get('next_conn_in', None)

def extractAuthType(request):
    return getJson(request).get('session_hash', None)

def extractHotspotID(request):
    return getJson(request).get('hotspot_id', None)

def extractClientID(request):
    return getJson(request).get('client_id', None)

def extractControllerPort(request):
    return getJson(request).get('controller_port', None)

def extractControllerAddr(request):
    return getJson(request).get('controller_address', None)

def extractControllerUser(request):
    return getJson(request).get('controller_user', None)

def extractControllerPass(request):
    return getJson(request).get('controller_password', None)
    
def extractControllerVersion(request):
    r = getJson(request).get('controller_version', None)
    if r == None:
        r = 'v4'
    return r

"""
Model is a dict with fields: client_id, hotspot_id, entrypoint_id, original_url.
Method tear down the request and returns dict with values for the model.
IN
    request: Flask.Request
OUT
    dict
"""
def getPreauthModel(request):

    logIt ( app.logger.debug, DEB_PREFIX, ' request args ', request.values.to_dict(flat = False) ) 
    result = {}

    POSTVarsNames = session.get('POSTVarsNames', [] )
    hotspotType = session.get('hotspotType', None )

    if request.method == 'POST' and hotspotType == 'mikrotik':
        for POSTVarsName in POSTVarsNames:
            result[POSTVarsName] = request.values.get(POSTVarsName)
        result['original_url'] = request.values.get('original_url')
    elif hotspotType == 'ubiquity':
        result['client_id'] = request.args.get('id')
        result['hotspot_id'] = request.args.get('ap')
        result['entrypoint_id'] = result['hotspot_id']
        result['original_url'] = request.args.get('url')
        result['hotspot_login_url'] = result['original_url']
    elif hotspotType == 'aruba':
        result['client_id'] = request.args.get('mac')
        result['hotspot_id'] = request.args.get('apname')
        result['entrypoint_id'] = result['hotspot_id']
        result['original_url'] = request.args.get('url')
        result['hotspot_login_url'] = 'http://{0}/cgi-bin/login'.format( request.args.get('switchip') )
    elif hotspotType == 'ruckus':
        #result = Ruckus()
        result['client_id'] = request.args.get('client_mac')
        result['hotspot_id'] = request.args.get('mac')
        result['entrypoint_id'] = result['hotspot_id']
        result['original_url'] = request.args.get('url')
        result['hotspot_login_url'] = request.args.get('sip')
        result['uip'] = request.args.get('uip')
    elif hotspotType == 'openwrt':
        #result = Ruckus()
        result['client_id'] = request.args.get('mac')
        result['hotspot_id'] = request.args.get('called')
        result['entrypoint_id'] = result['hotspot_id']
        result['original_url'] = request.args.get('userurl')
        result['hotspot_login_url'] = request.args.get('uamip')
        result['uamport'] = request.args.get('uamport')        

    logIt( app.logger.error, DEB_PREFIX, 'result', result )    
    return result 

getPreauthTemplateData = getPreauthModel

"""
Method checks request content type.
IN
    request: Flask.Request
OUT
    Bool
"""
def isJson(request):
    result = request.content_type == 'application/json'
    app.logger.debug("misc isJson() returns '{0}'".format(result))
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

    if isJson(request):        
        logIt ( app.logger.debug, DEB_PREFIX, 'json request args ', request.values.to_dict(flat = False) )   
        clientID = extractClientID(request)
        hotspotID = extractHotspotID(request)
        entrypointID = extractEntryPointID(request)
    else:
        model = session.get( 'model' )
        logIt ( app.logger.debug, DEB_PREFIX, 'normalized args from model', model )   
        clientID = model.get('client_id', None)
        hotspotID = model.get('hotspot_id', None)
        entrypointID = model.get('entrypoint_id', None)

    result = False   
    
    if None in ( clientID, hotspotID, entrypointID ):
        logIt ( app.logger.error, DEB_PREFIX, 'bad args' )   
        logIt( app.logger.debug, DEB_PREFIX, 'result', result )    
        return result

    try:        
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()

        cursor.execute('SELECT\
            (SELECT idle_time from charon_limits WHERE client_id=%s AND hotspot_id=%s)\
             - \
            round(extract(mins from now()-acctstoptime)*60 + extract(secs from now()-acctstoptime)) AS t\
            FROM radacct\
            WHERE \
            username=%s AND\
            acctstoptime > now() - \
            make_interval(secs:=(SELECT idle_time from charon_limits WHERE client_id=%s AND hotspot_id=%s))\
          ORDER BY t DESC LIMIT 1;',
            (clientID, hotspotID,clientID, clientID, hotspotID)
        )
        """
        print cursor.mogrify('SELECT\
            (SELECT idle_time from charon_limits WHERE client_id=%s AND hotspot_id=%s)\
             - \
            round(extract(mins from now()-acctstoptime)*60 + extract(secs from now()-acctstoptime)) AS t\
            FROM radacct\
            WHERE \
            username=%s AND\
            acctstoptime > now() - \
            make_interval(secs:=(SELECT idle_time from charon_limits WHERE client_id=%s AND hotspot_id=%s))\
          ORDER BY t DESC LIMIT 1;',
            (clientID, hotspotID,clientID, clientID, hotspotID)
        ) 
        """
        row = cursor.fetchone()
        if not row:
            waitTime = 0
        else:
            (waitTime,) = row
        result = waitTime
    except pgError as e:
        logIt( app.logger.error, DEB_PREFIX, 'database exception', str(e) )
    finally:
        c.close()

    logIt( app.logger.debug, DEB_PREFIX, 'result', result )

    return result
