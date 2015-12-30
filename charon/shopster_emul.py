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
POST_POSTAUTH_VARS = POST_MAIN_VARS + ['session_hash', 'session_timeout', 'traffic_limit', 'next_conn_in']
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
    #print "doAllowUser"
    clientID = request.values.get('client_id')
    hotspotID = request.values.get('hotspot_id')
    formData = {
    'client_id': clientID,
    'hotspot_id': hotspotID,
    'entrypoint_id': hotspotID,
    'traffic_limit':  '60',
    'session_timeout':  '3100',
    'next_conn_in':   '3600',
    'session_hash': 'splash'
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

