from os import environ

POSTPOSTAUTH_URL = 'http://backup-2.getshopster.com:8875/redirect/'#environ.get('CHARON_PPAUTH_URL'),#'http://charon.zerothree.su:8081/postpostauth/'
SHOPSTER_URL = 'http://backup-2.getshopster.com:8875/v1/charon_api/login_start/'  #environ.get('SHOPSTER_AUTH_URL')#'http://shopster.zerothree.su:8082/', #shopster container
SHOPSTER_SECRET = 'ech5haisho8Ohri'
#change to ENV var
DB_HOST = environ.get('DB_HOST')
DB_USER = environ.get('DB_USER')
DB_PASS = environ.get('DB_PASS')
DB_NAME = environ.get('DB_NAME')
#from logging import DEBUG as LOG_LEV_DEBUG
APP_LOG_LEVEL = environ.get('APP_LOG_LEV')
