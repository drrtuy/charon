#!/bin/bash

log_level=`printenv WSGI_LOG_LEV` 
workers=`printenv WSGI_WORKERS`
#cert=`printenv TLS_CERT`
#key=`printenv TLS_KEY`
echo "starting gunicorn with $workers threads"
#gunicorn --log-level $log_level --error-logfile - --access-logfile - -w $workers -b 0.0.0.0:8080 --keyfile $key --certfile $cert charon:app
gunicorn --log-level $log_level --error-logfile charon.log --access-logfile charon.log -w $workers -b 0.0.0.0:8080 charon:app
#gunicorn --log-level $log_level --error-logfile - --access-logfile - -w $workers -b 0.0.0.0:8080 charon:app
echo "gunicorn has stopped"
