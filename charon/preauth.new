from charon import app
from flask import request, render_template, abort, json, session, g, make_response
from hashlib import sha256
from datetime import date
from psycopg2 import connect, Error as pgError
from json import loads as json_loads, dumps as json_dumps
from inspect import stack
from misc import formatOk, genPass, idleCheck, getPreauthTemplateData, getPreauthModel, logIt 

POST_MAIN_VARS = ['client_id', 'hotspot_id', 'entrypoint_id']
MT_PREAUTH_VARS = POST_MAIN_VARS + ['hotspot_login_url']
UNI_PREAUTH_VARS = ['id', 'ap', 'url' ]
ARUBA_PREAUTH_VARS = ['mac', 'apname', 'url' ]
RUCKUS_PREAUTH_VARS = ['mac', 'client_mac', 'url']
OPENWRT_PREAUTH_VARS = ['userurl', 'uamip', 'uamport', 'mac']
DEB_PREFIX = 'preauth'

"""
Method get a HotSpot id via Shopster API.
IN
    request: Flask.Request
OUT
    None || one of the hotspot types as a string
"""
def getHotspotType(request):

    result = None
    h_id = None

    logIt( app.logger.debug, DEB_PREFIX, ' request args ', request.values.to_dict(flat = False) )

    if request.method == 'POST':
        h_id = request.values.get('hotspot_id', None)
    elif request.method == 'GET':
        idNames = [ 'ap', 'apname', 'called', 'mac' ]
        for idName in idNames:
            try:
                h_id = request.args[idName]
                break
            except KeyError:
                continue
        
    #test cases    
    if h_id == 'outage':
        logIt( app.logger.debug, DEB_PREFIX, 'TEST CASE shopster is down' )
        result = 'outage'
    elif h_id == '44:d9:e7:48:81:63' or h_id == '44:d9:e7:48:84:74':
        result = 'ubiquity'
    elif h_id == 'ac:a3:1e:c5:8c:7c':
        result = 'aruba'
    elif h_id == '6caab339afe0':
        result = 'ruckus'
    elif h_id == '90-F6-52-5B-73-F4':
        result = 'openwrt'
    elif h_id != None and request.method == 'POST':
        result = 'mikrotik'

    logIt( app.logger.debug, DEB_PREFIX, ' returns ', result )

    return result 

getHotspotId = getHotspotType

"""
Method checks POST variable list for completness and correctness.
IN
    request: Flask.Request
OUT
    Bool
"""
def preauthGoodVars(request):

    result = False

    logIt ( app.logger.debug, DEB_PREFIX, ' request args ', request.values.to_dict(flat = False) ) 

    POSTVarsNames = session.get( 'POSTVarsNames', None )
    for POSTVarName in POSTVarsNames:
            POSTVarValue = request.values.get(POSTVarName, None)            
            if POSTVarValue == None:
                logIt( app.logger.warning, DEB_PREFIX, ' input var {0} check failed'.format( POSTVarName) )
                return result
    if len( POSTVarsNames ):
        result = True        

    logIt( app.logger.debug, DEB_PREFIX, ' returns ', result )

    return result

"""
Method add/updates User model for later usage in postpostauth stage.
IN
    request: Flask.Request
OUT
    Bool
"""
#change userMAC to userID
def doSaveSessionData(request):

    result = False

    h = app.config.get('DB_HOST')
    d = app.config.get('DB_NAME')
    u = app.config.get('DB_USER') 
    p = app.config.get('DB_PASS')

#   model = getPreauthModel(request)
    model = session.get( 'model' )
    logIt ( app.logger.debug, DEB_PREFIX, 'normalized args from model', model ) 

    if model == None:
        logIt( app.logger.error, DEB_PREFIX, 'model is empty')
        logIt( app.logger.debug, DEB_PREFIX, 'result', result )
        return result

    userMAC = userName = model.get('client_id', None)
    hotspotID = model.get('hotspot_id', None)
    entrypointID = model.get('entrypoint_id', None)
    originalURL = model.get('original_url', None)
    hotspotLoginURL = model.get('hotspot_login_url', None) 
    passWord = genPass()
    
    if None in ( userName, passWord, hotspotID, entrypointID, originalURL, hotspotLoginURL ):
        logIt( app.logger.error, DEB_PREFIX, 'not enough data in the model')
        logIt( app.logger.debug, DEB_PREFIX, 'result', result )
        return result

    # Future db upserts depend on data we upsert now. So we commit after the first chunk.    
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
        
        c.commit()
    except pgError as e:
        logIt( app.logger.error, DEB_PREFIX, 'database exception', str(e) )
        c.close()
        return result
        
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
        result = True
    except pgError as e:
        logIt( app.logger.error, DEB_PREFIX, 'database exception', str(e) )
    finally:
        c.close()

    logIt( app.logger.debug, DEB_PREFIX, 'result', result )

    return result


"""
Client enters the systems at this point. His POST request contains
IN
    Flask.Request
OUT 
    html doc as str
"""
@app.route("/preauth/", methods=['POST', 'GET'])
def doPreauth():

    result = None
    POSTVarsNames = [ ]

    hotspotType = getHotspotType(request)

    if hotspotType == 'mikrotik':
        POSTVarsNames = MT_PREAUTH_VARS
    elif hotspotType == 'ubiquity':    
        POSTVarsNames = UNI_PREAUTH_VARS         
    elif hotspotType == 'aruba':    
        POSTVarsNames = ARUBA_PREAUTH_VARS  
    elif hotspotType == 'ruckus':    
        POSTVarsNames = RUCKUS_PREAUTH_VARS 
    elif hotspotType == 'openwrt':    
        POSTVarsNames = OPENWRT_PREAUTH_VARS 
    elif hotspotType == 'outage': #test case
        hotspotType = None
        POSTVarsNames = MT_PREAUTH_VARS

    session['hotspotType'] = hotspotType    
    session['POSTVarsNames'] = POSTVarsNames    

    varsOk = preauthGoodVars(request) 
    session['model'] = getPreauthModel(request)        #getPreauthModel

    if hotspotType is not None:        
        waitTime = idleCheck(request)
        
        if waitTime != False and waitTime:
            extradata = {'wait_time': waitTime}
            logIt( app.logger.debug, DEB_PREFIX, 'render idle template' )
            return render_template('preauth_idle.html', extradata = extradata)

        if doSaveSessionData(request) != True:
            logIt( app.logger.debug, DEB_PREFIX, 'Can\'t save session. Render error template' )    
            return render_template('error.html') 

        extradata = session['model']
        logIt( app.logger.debug, DEB_PREFIX, 'OK. Render preauth template' )
        return render_template('preauth.html', extradata = extradata, url = app.config.get('SHOPSTER_URL'))

    elif varsOk:                                #didnt get hotspot type and vars are ok then shopster system is down
        logIt( app.logger.debug, DEB_PREFIX, 'Auth service is down. Render outage template' )
        result = render_template('shopster_outage.html')
        return result

    logIt( app.logger.debug, DEB_PREFIX, 'Default exit. Render error template' )    
    return render_template('error.html')
