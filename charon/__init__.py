from flask import Flask
app = Flask(__name__)
app.config.from_object('charon.settings')
from charon import views

@app.before_first_request
def setup_logging():
    if not app.testing:
        import logging
        Handler = logging.StreamHandler()
        Handler.setFormatter( logging.Formatter('%(asctime)s:pid %(process)d:thread %(thread)d: %(message)s') )
        app.logger.addHandler(Handler)
        logLevel = int(app.config.get('APP_LOG_LEVEL'))
        app.logger.setLevel( logLevel ) #set logg level using external config
