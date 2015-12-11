from os import environ

POSTPOSTAUTH_URL = environ.get('CHARON_PPAUTH_URL'),#'http://charon.zerothree.su:8081/postpostauth/'
SHOPSTER_URL = environ.get('SHOPSTER_AUTH_URL')#'http://shopster.zerothree.su:8082/', #shopster container
SHOPSTER_SECRET = 'ech5haisho8Ohri'
#change to ENV var
DB_HOST = 'z3_postgres_1'
DB_USER = 'charon'
DB_PASS = 'ne9lahngahXah8n'
DB_NAME = 'radius'
from logging import DEBUG as LOG_LEV_DEBUG
APP_LOG_LEVEL = LOG_LEV_DEBUG
