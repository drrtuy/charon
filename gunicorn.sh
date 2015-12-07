#!/bin/bash

log_level=`printenv WSGI_LOG_LEV` 
workers=`printenv WSGI_WORKERS`
echo "starting gunicorn with $workers threads"
gunicorn --log-level $log_level --error-logfile - --access-logfile - -w $workers -b 0.0.0.0:8080 charon:app
echo "gunicorn has stopped"
