from charon import app

@app.route("api.charon.shopster.ru/v1/radius/subs/")
def doAllowUser():
    return str(method) + str(request.headers) + str(values)

@app.route("charon.shopster.ru/postauth/")
def doPostauth():
    return str(method) + str(request.headers) + str(values)

if __name__ == "__main__":
    app.run()
