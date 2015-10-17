from charon import app
from flask import request

@app.route("/v1/radius/subs/")
def doAllowUser():
    return str(request.method) + str(request.headers) + str(request.values)

@app.route("/postauth/")
def doPostauth():
    return str(request.method) + str(request.headers) + str(request.values)

if __name__ == "__main__":
    app.run()
