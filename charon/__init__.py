from flask import Flask
app = Flask(__name__)
app.config.from_object('charon.settings')
from charon import views

@app.before_first_request
def setup_logging():
    if not app.debug:
        import logging
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.DEBUG) #set logg level using external config
