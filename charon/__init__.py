from flask import Flask
app = Flask(__name__)
app.config.update(
    #PREAUTH_URL = preAuthUrl,
    #POSTAUTH_URL = postAuthUrl,
    POSTPOSTAUTH_URL = 'http://charon.zerothree.su:8081/postpostauth/',
    SHOPSTER_URL = 'http://shopster.zerothree.su:8082/', #shopster container
    SHOPSTER_SECRET = 'ech5haisho8Ohri', 
    DB_HOST = 'z3_postgres_1',
    DB_USER = 'charon',
    DB_PASS = 'ne9lahngahXah8n',
    DB_NAME = 'radius'
)
from charon import views
