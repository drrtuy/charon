from flask import Flask
app = Flask(__name__)
app.config.from_object('charon.settings')
from charon import views
from os import environ

@app.before_first_request
def setup_logging():
    #FIX. These data structures must be taken from a DB
    app.config['PREAUTH_TYPE_DS'] = [
        { 'type': 'mikrotik', 'method': 'POST', 'attrs':[ 'hotspot_id' ] },
        { 'type': 'openwrt', 'method': 'GET', 'attrs':[ 'challenge', 'uamip' ] },
        { 'type': 'ubiquity', 'method': 'GET', 'attrs':[ 'id', 't'  ] },
        { 'type': 'aruba', 'method': 'GET', 'attrs':[ 'switchip', 'cmd', 'vcname' ] },
        { 'type': 'ruckus', 'method': 'GET', 'attrs':[ 'sip', 'client_mac' ] }
    ]
    
    if not app.testing:
        import logging
        if environ.get('LOG_TO_FILE') != None:
            Handler = logging.FileHandler('charon.log')
        else:
            Handler = logging.StreamHandler()
        Handler.setFormatter( logging.Formatter('%(asctime)s:pid %(process)d:thread %(thread)d: %(message)s') )
        app.logger.addHandler(Handler)
        logLevel = int(app.config.get('APP_LOG_LEVEL'))
        app.logger.setLevel( logLevel ) #set logg level using external config
