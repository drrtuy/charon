from charon import app
from flask import request, render_template, abort, json, session, make_response
from re import search as regex_search
from requests import post
from hashlib import sha256
from datetime import date
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps
#from inspect import stack
from urllib import pathname2url as percentEncode
from binascii import hexlify, unhexlify
from hashlib import md5

DEB_PREFIX='postpostauth'
HASH_LEN=16

from misc import formatOk, idleCheck, logIt, xorString

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

    result = None
      
    model = session.get('model')
    logIt ( app.logger.debug, DEB_PREFIX, 'normalized args from model', model )

    clientID = model.get('client_id')
    hotspotID = model.get('hotspot_id')

    if None in ( clientID, hotspotID):
        logIt( app.logger.debug, DEB_PREFIX, 'returns', result )
        return result

    try:
        c = connect(host = h, user = u, password = p, database = d)
        cursor = c.cursor()
      
        cursor.execute( 'SELECT * FROM charon_postauth_getformdata(%s,%s) as (a varchar,b varchar,c varchar,d varchar,e varchar);',\
            (clientID, hotspotID),
        )

        row = cursor.fetchone()
        if not row:
            c.close()
            result = None
            logIt( app.logger.error, DEB_PREFIX, 'session data not found', result )
            logIt( app.logger.debug, DEB_PREFIX, 'returns', result )
            return result

        result = {}
        (result['username'], result['password'],\
        result['origin_url'], result['hotspot_login_url'], result['session_hash']) \
        = row 
        c.close()
        
        #redirect URL crafting
        st =  '{0}?session_hash={1}&origin_url={2}'.format(\
            app.config.get('POSTPOSTAUTH_URL'), result['session_hash'], result['origin_url']\
        ) 
    
        result['origin_url'] = st

    except pgError as e:
        logIt( app.logger.error, DEB_PREFIX, 'db exception', str(e) )       

    logIt( app.logger.debug, DEB_PREFIX, 'returns', result )

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

    logIt( app.logger.debug, DEB_PREFIX, 'request args', request.values.to_dict(flat = False) )

    hotspotType = session.get('hotspotType')

    logIt( app.logger.debug, DEB_PREFIX, 'hotspot type is', hotspotType )
    

    waitTime = idleCheck(request)
    
    if waitTime != False and waitTime:
        extradata = {'wait_time': waitTime}
        return render_template('postpostauth_idle.html', extradata = extradata)            

    model = session.get('model', None)
    
    #if model != None
    formData = getFormData(request)

    if None not in ( formData, model ) and idleCheck(request) == 0:
        if hotspotType == 'mikrotik':
            logIt( app.logger.debug, DEB_PREFIX, 'OK. Render mikrotik template' )            
            return render_template('postpostauth_mikrotik.html', formdata = formData)

        if hotspotType == 'aruba':
            logIt( app.logger.debug, DEB_PREFIX, 'OK. Render aruba template' )
            return render_template('postpostauth_aruba.html', formdata = formData)

        if hotspotType == 'openwrt':
            openwrtSecret = app.config.get('OPENWRT_SECRET_KEY')
            #md5 digest of a concatenated challenge sent by chilli and chilli uamsecret setting.              
            challWithSecret =  md5( '{}{}'.format( model.get('challenge'), openwrtSecret ) ).digest()
            passLen = len( formData.get('password') )
            #16 bytes aligned password
            alignedPass = formData.get('password').join( '\x00' * ( HASH_LEN - passLen ) )
            xoredPass = xorString( alignedPass, challWithSecret )
            url = 'http://{0}:{1}/logon?username={2}&password={3}'.format( 
                formData.get('hotspot_login_url'), model.get('uamport'),
                formData.get('username'), hexlify( xoredPass )
            )
            logIt( app.logger.debug, DEB_PREFIX, 'xored pass is {0}'.format( repr( xoredPass ) ) )
            logIt( app.logger.debug, DEB_PREFIX, 'OK. Render openwrt template' )
            return render_template('postpostauth_openwrt.html', url = url ) 

        if hotspotType == 'ubiquity':
            logIt( app.logger.debug, DEB_PREFIX, 'OK. Render ubiquity template' )
            return render_template('postpostauth_ubiquity.html', url = formData.get('origin_url') )           

        if hotspotType == 'cisco':
            logIt( app.logger.debug, DEB_PREFIX, 'OK. Render cisco template' )
            return render_template('postpostauth_cisco.html', formdata = formData )

        if hotspotType == 'ruckus' and not session.get('zone_director_passed'):
            logIt( app.logger.debug, DEB_PREFIX, 'OK. Render ruckus intermediate template' )
            return render_template('postpostauth_ruckus.html',\
               url = 'http://{0}:9997/login?username={1}&password={2}'.format( formData.get('hotspot_login_url'), 
                formData.get('username'), formData.get('password') )
            )
               
        elif hotspotType == 'ruckus':
            session['zone_director_passed'] = False                   
            r = make_response( 
                    render_template( 'postpostauth_ruckus.html', url = formData.get('origin_url') ) 
            )
            logIt( app.logger.debug, DEB_PREFIX, 'OK. Render ruckus intermediate template' )
            return r                
    logIt( app.logger.debug, DEB_PREFIX, 'Default exit. Render error template' )    
 
    return render_template('error.html')
