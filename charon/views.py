from charon import app
from flask import request

@app.route("/v1/radius/subs/")
def doAllowUser():
    return str(flask.request.method) + str(flask.request.headers) + str(flask.request.values)

@app.route("/postauth/")
def doPostauth():
    return str(flask.request.method) + str(flask.request.headers) + str(flask.request.values)

if __name__ == "__main__":
    app.run()
