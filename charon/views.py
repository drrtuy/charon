from charon import app
from flask import request, render_template

@app.route("/v1/radius/subs/", methods=['POST','GET'])
def doAllowUser():
    r = ""
    for i in request.headers:
        r += str(i)
        r += "\n"
    print request.values
    return render_template('subs.html')

@app.route("/postauth/")
def doPostauth():
    return str(request.method) + str(request.headers) + str(request.values)

if __name__ == "__main__":
    app.run()
