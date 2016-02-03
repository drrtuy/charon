from charon import app
from flask import request, render_template, abort, session
from misc import *
from urllib2 import URLError, HTTPError
from ssl import SSLError
from time import sleep

UBIQUITY_VARS = ['id', 'ap','url']

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
@app.route("/ubiquity/", methods=['GET'])
def doUbiquityRedirect():
    getVarNames = UBIQUITY_VARS   

    result = None

    templateData = {}

    app.logger.debug( "preauth doUbiquityRedirect() GET params {0} ".format(request.args) )        
    
    templateData['client_id'] = request.args.get('id')
    templateData['hotspot_id'] = request.args.get('ap')
    templateData['entrypoint_id'] = templateData['hotspot_id']
    templateData['original_url'] = request.args.get('url')
    templateData['hotspot_login_url'] = templateData['original_url']
    templateData['url'] = 'https://charon.zerothree.su/preauth/' 
    
    session['hotspot_type'] = 'ubiquity'
    app.logger.debug("doUbiquityRedirect() session {0}".format( session.get('hotspot_type') ) )
    
    result = render_template('ubiquity.html', template_data = templateData)
    return result


"""
The func checks whether hotspot is Ubiquity. The hotspot is ubiquity if shopster sends us bunch of parameters: 
controller_address, controller_port, controller_user, controller_password
IN
    request: Flask.Request
OUT
    Bool
"""
def isUbiquity(request):

    result = False

    inputJSON = getJson(request)

    app.logger.debug( "postauth isUbiquity() request json '{0}'".format(json_dumps(inputJSON)) )
    controllerAddr = extractControllerAddr(request)
    controllerPort = extractControllerPort(request)
    controllerUser = extractControllerUser(request)
    controllerPass = extractControllerPass(request)    

    if None not in ( controllerAddr, controllerPort, controllerUser, controllerPass ):
        result = True

    app.logger.debug( "postauth isUbiquity() returns '{0}'".format(result) )

    return result

from unifi.controller import Controller, PYTHON_VERSION
  
class Ubnt(Controller):

    def _login(self, version):
        app.logger.debug('Ubnt _login() as %s', self.username)

        params = {'username': self.username, 'password': self.password}
        login_url = self.url

        if version is 'v4':
            login_url += 'api/login'
            params = json.dumps(params)
        else:
            login_url += 'login'
            params.update({'login': 'login'})
            if PYTHON_VERSION is 2:
                params = urllib.urlencode(params)
            elif PYTHON_VERSION is 3:
                params = urllib.parse.urlencode(params)

        if PYTHON_VERSION is 3:
            params = params.encode("UTF-8")

        self.opener.open( login_url, params, timeout = app.config.get('UBNT_CONN_TO') ).read()

    def _logout(self):
        app.logger.debug('Ubnt._logout()')
        self.opener.open( self.url + 'logout', timeout = app.config.get('UBNT_CONN_TO') ).read()


"""
The func allows user at Ubiquity hotspot using its API.
IN
    request: Flask.Request
OUT
    Bool
"""
def allowUbiquitySubs(request):
    result = False
    inputJSON = getJson(request)
    app.logger.debug( "postauth allowUbiquitySubs() request json '{0}'".format(json_dumps(inputJSON)) )

    userName = extractUserName(request)
    sessionTimeout = extractSessionLimit(request)
    traffLimit = extractTraffLimit(request)
    cPort = extractControllerPort(request)
    cAddr = extractControllerAddr(request)
    cUser = extractControllerUser(request)
    cPass = extractControllerPass(request)
    cVersion = extractControllerVersion(request)   

    if not userName or not sessionTimeout or not traffLimit or not cPort or not cAddr or not cUser or not cPass:
        app.logger.debug( "postauth allowUbiquitySubs() returns '{0}'".format(result) )
        return result        

    try:
        c = Ubnt(cAddr, cUser, cPass, port=cPort, version=cVersion)
        c.authorize_guest(userName, sessionTimeout, byte_quota = traffLimit)
        c._logout()
        result = True
    except ( URLError, HTTPError, SSLError ):
        result = False        

    app.logger.debug( "postauth allowUbiquitySubs() returns '{0}'".format(result) )

    return result

