from charon import app
from flask import request, render_template, abort, json, session, make_response
from re import search as regex_search
from requests import post
from hashlib import sha256
from datetime import date
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps
from inspect import stack
from model import *

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
DEB_PREFIX='postPostAuth'

from misc import formatOk, idleCheck

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
    
    #clientID = request.values.get('client_id', None)
    #hotspotID = request.values.get('hotspot_id', None)

    #if not clientID or not hotspotID:
    model = session.get('model')
    clientID = model.get('client_id')
    hotspotID = model.get('hotspot_id')

    result = None

    (unused, unused, unused, currFuncName, unused, unused) = stack()[0]
    app.logger.debug( '{0} {1}() request args {2}'.format(DEB_PREFIX, currFuncName, request.values.to_dict(flat = False) ) )

    if not clientID or not hotspotID:
        app.logger.debug( "postpostauth getFormData() returns {0}".format(result) )
        return result

    try:
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()
        cursor.execute( 'SELECT DISTINCT a.username, a.password, u.origin_url, u.hotspot_login_url, l.session_hash\
             FROM charon_authentication a, charon_urls u, charon_limits l \
             WHERE a.client_id = u.client_id \
             AND l.client_id = u.client_id \
             AND u.client_id = %s \
             AND a.hotspot_id = u.hotspot_id \
             AND u.hotspot_id = %s; ', 
            (clientID, hotspotID),
        )
        row = cursor.fetchone()
        if not row:
            c.close()
            return None
        result = {}
        #FIX takes values from a row using table structure
        (result['username'], result['password'],\
        result['origin_url'], result['hotspot_login_url'], result['session_hash']) \
        = row 
        c.close()
               
        st =  '{0}?session_hash={1}&origin_url={2}'.format(\
            app.config.get('POSTPOSTAUTH_URL'), result['session_hash'], result['origin_url']\
        )
    
        result['origin_url'] = st
        app.logger.debug( "postpostauth getFormData() FAST HACK origin URL {0}".format(result['origin_url']) )

    except pgError as e:
        app.logger.error("postpostauth getFormData()" + str(e))

    app.logger.debug( "postpostauth getFormData() returns {0}".format(json_dumps(result)) )

    return result

"""
Method checks POST variable list for completness and correctness.
IN
    request: Flask.Request
OUT
    Bool
"""
def ppostauthGoodVars(request):
    result = True
    return result
    """
    app.logger.debug( "postpostauth ppostauthGoodVars() request POST data {0}".format(json_dumps(request.form)) )

    POSTVarsNames = POST_PPOSTAUTH_VARS
    for POSTVarName in POSTVarsNames:
            POSTVarValue = request.values.get(POSTVarName, None)            
            if not POSTVarValue: #or not formatOk('ppostauthGoodVars', POSTVarName, POSTVarValue):
                app.logger.warning( "postpostauth ppostauthGoodVars() input var '{0}' check failed".format(POSTVarName) )
                result = False
                break

    app.logger.debug( "postpostauth ppostauthGoodVars() returns {0}".format(result) )
    return result
    """

"""
Method checks variable for correctness in a particular function.
IN
    client_id: str (as a MAC)
    hotspot_id: str
    entrypoint_id: str
OUT
    str
"""
@app.route("/postpostauth/", methods=['POST', 'GET'])
def doPostPostauth():

    (u, u, u, currFuncName, u, u) = stack()[0]
    app.logger.debug( '{0} {1}() request args {2}'.format(DEB_PREFIX, currFuncName, request.values.to_dict(flat = False) ) )    

    hotspotType = session.get('hotspotType')
    
    if ppostauthGoodVars(request):        
        waitTime = idleCheck(request)
        
        if waitTime != False and waitTime:
            extradata = {'wait_time': waitTime}
            return render_template('postpostauth_idle.html', extradata = extradata)            
        
        formData = getFormData(request)
        model = session.get('model')
        #print "zone director flag value", session['zone_director_passed']

        if formData != None and idleCheck(request) == 0:
            if hotspotType == 'mikrotik':            
                return render_template('postpostauth.html', formdata = formData)
            if hotspotType == 'aruba':
                return render_template('postpostauth_aruba.html', formdata = formData)

            if hotspotType == 'ruckus' and not session.get('zone_director_passed'):
                    r = make_response( 
                        render_template('postpostauth_ruckus.html',\
                           url = 'http://{0}:9997/login?username={1}&password={2}'.format( formData.get('hotspot_login_url'), 
                            formData.get('username'), formData.get('password') )
                        ) 
                    )
                    r.headers['Strict-Transport-Security'] = 'max-age=0'
                    session['zone_director_passed'] = True
                    return r                
            elif hotspotType == 'ruckus':
                    print "return call", formData
                    session['zone_director_passed'] = False                   
                    r = make_response( 
                            render_template( 'postpostauth_ruckus.html', url = formData.get('origin_url') ) 
                    )
                    r.headers['Strict-Transport-Security'] = 'max-age=0'
                    return r                
     
            return render_template('error.html')
            
    return render_template('error.html')

"""
@app.route("/buckus/", methods=['POST', 'GET'])
def buckus():
    #xml = '<ruckus> <req-password>myPassword</req-password> <version>1.0</version> <command cmd="user-authenticate" ipaddr="172.16.17.101" macaddr="00:22:FB:18:8B:26" name="test" password="test"/> </ruckus>'
    xml = '<ruckus> <version>1.0</version> <command cmd="user-authenticate" ipaddr="172.16.17.101" macaddr="00:22:FB:18:8B:26" name="test" password="test"/> </ruckus>'
    hotspot = session.get('model')
    r = make_response( render_template('postpostauth_ruckus.html',\
    url = 'https://{0}/443/admin/_portalintf.jsp'.format(hotspot.get('hotspot_login_url'),\
    data = xml) 
    ) )
    r.headers['Strict-Transport-Security'] = 'max-age=0'
    return r
@app.route("/buckusa/", methods=['POST', 'GET', 'OPTIONS'])
def buckusa():
    if request.method == 'OPTIONS':
        r = make_response( " ", 200 )
        r.headers['Strict-Transport-Security'] = 'max-age=0'
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return r
    r = make_response( "xml answer", 200 )
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Strict-Transport-Security'] = 'max-age=0'
    return r
"""
