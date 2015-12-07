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
        app.logger.error("postpostauth getFormData()" + str(e))

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
    #print "doPostPostauth", app.config.get('SHOPSTER_URL')
    if ppostauthGoodVars(request):
        formData = getFormData(request)
        #print "doPostPostauth", formData
        if formData is not None:            
            return render_template('postpostauth.html', formdata = formData)
    return render_template('error.html')
