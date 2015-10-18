from charon import app
from flask import request, render_template, abort

@app.route("/v1/radius/subs/", methods=['POST','GET'])
def doAllowUser():
    r = ""
    for i in request.headers:
        r += str(i)
        r += "\n"
    print request.values
    extradata = {'linkorig': 'www.ya.ru',\
        
    }
    return render_template('subs.html', extradata=extradata)

def doCheckPostpostauthVals(request):
    return True

@app.route("/postauth/", methods=['POST','GET'])
def doPostpostauth():
    if request.method == 'POST' and doCheckPostpostauthVals(request):
        print request.values
        extradata = {'mac': request.values.get('mac', 'empty'),\
            'ip': request.values.get('ip', 'empty'),\
            'username': request.values.get('username', 'empty'),\
            'linkorig': request.values.get('link-orig', 'empty'),\
            'linklogin': request.values.get('link-login', 'empty'),\
            'error': request.values.get('error', 'empty')
        }
        return render_template('postpostauth.html', extradata=extradata)
    elif request.method == 'GET':
        print request.values
        extradata = {'linkorig': 'www.ya.ru',\
        }
        return render_template('subs.html', extradata=extradata)
    else:
        abort(501)

if __name__ == "__main__":
    app.run()
