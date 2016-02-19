from charon import app
from flask import request, render_template, abort, session
from misc import *
from urllib2 import URLError, HTTPError
from ssl import SSLError
from time import sleep
import urllib

UBIQUITY_VARS = ['id', 'ap','url']
DEB_PREFIX = 'ubiquity'

"""
The func checks whether hotspot is Ubiquity or not at a postauth stage. The hotspot is ubiquity if shopster sends us a bunch of parameters: 
controller_address, controller_port, controller_user, controller_password
IN
    request: Flask.Request
OUT
    Bool
"""
def isUbiquity(request):

    result = False

    inputJSON = getJson(request)

    logIt( app.logger.debug, DEB_PREFIX, 'request json', json_dumps(inputJSON) )

    controllerAddr = extractControllerAddr(request)
    controllerPort = extractControllerPort(request)
    controllerUser = extractControllerUser(request)
    controllerPass = extractControllerPass(request)    

    if None not in ( controllerAddr, controllerPort, controllerUser, controllerPass ):
        result = True

    logIt( app.logger.debug, DEB_PREFIX, 'returns', result )

    return result

"""
Slightly modified unify API main class. It supports API request timeout.
"""
from unifi.controller import Controller, PYTHON_VERSION

class Ubnt(Controller):
    def _login(self, version):
        params = {'username': self.username, 'password': self.password}
    #        params = {'username': 'admin', 'password': 'lobster'}
        login_url = self.url

        logIt( app.logger.debug, DEB_PREFIX, 'unify login {0} {1}'.format( params, self.url ) )

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
        self.opener.open( self.url + 'logout', timeout = app.config.get('UBNT_CONN_TO') ).read()

"""
The func authorizes a user at Ubiquity hotspot by API.
IN
    request: Flask.Request
OUT
    Bool
"""
def allowUbiquitySubs(request):
    result = False
    inputJSON = getJson(request)

    logIt( app.logger.debug, DEB_PREFIX, 'request json', json_dumps(inputJSON) )

    userName = extractUserName(request)
    sessionTimeout = extractSessionLimit(request)
    traffLimit = extractTraffLimit(request)
    cPort = extractControllerPort(request)
    cAddr = extractControllerAddr(request)
    cUser = extractControllerUser(request)
    cPass = extractControllerPass(request)
    cVersion = extractControllerVersion(request)   

    if None in ( userName, sessionTimeout, traffLimit, cPort, cAddr, cUser, cPass ):
        logIt( app.logger.error, DEB_PREFIX, 'returns', result )
        return result        

    try:
        logIt( app.logger.debug, DEB_PREFIX, '{0} {1} {2} {3} {4}'.format ( cAddr, cUser, cPass, cPort, cVersion ) )
        c = Ubnt(cAddr, cUser, cPass, port=cPort, version=cVersion)
        logIt( app.logger.error, DEB_PREFIX, 'after init' )
        c.authorize_guest(userName, sessionTimeout, byte_quota = traffLimit)
        c._logout()
        result = True
    except ( URLError, HTTPError, SSLError ) as e:
        logIt( app.logger.debug, DEB_PREFIX, str( e ) )
        result = False        

    logIt( app.logger.debug, DEB_PREFIX, 'returns', result )

    return result
