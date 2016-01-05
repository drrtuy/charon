#!/usr/bin/python

from werkzeug.contrib.profiler import ProfilerMiddleware

from charon import app

app.config['PROFILE'] = True
app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])

app.config.from_object('charon.settings')
app.run(host='0.0.0.0',port=8080,debug = True)


