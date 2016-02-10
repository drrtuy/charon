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
LEGACY should be removed
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

        if formData != None and idleCheck(request) == 0:
            if hotspotType == 'mikrotik':            
                return render_template('postpostauth.html', formdata = formData)
            if hotspotType == 'aruba':
                return render_template('postpostauth_aruba.html', formdata = formData)

            if hotspotType == 'openwrt':
                url = 'http://{0}:{1}/logon?username={2}&password={3}'.format( 
                    formData.get('hotspot_login_url'), model.get('uamport'),
                    formData.get('username'), formData.get('password')
                )
                return render_template('postpostauth_openwrt.html', url = url ) 

            if hotspotType == 'ubiquity':
                return render_template('postpostauth_ubiquity.html', url = formData.get('origin_url') )           

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
