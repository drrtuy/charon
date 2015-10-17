from charon import app

@app.route("/v1/radius/subs/")
def doAllowUser():
    return str(method) + str(request.headers) + str(values)

@app.route("/postauth/")
def doPostauth():
    return str(method) + str(request.headers) + str(values)

if __name__ == "__main__":
    app.run()
