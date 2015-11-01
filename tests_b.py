from charon import views
from werkzeug import MultiDict
from flask import Request

f1 = {}
f2 = {'client_id': 'blabla:bla:bla'}
f3 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': 'AA:BB:CC:DD:EE:FF'} 
f4 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319'}
f5 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319'}

ok2 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319'}
ok3 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com'}

fixture = [f1, f2, f3, f4, f5, ok2, ok3]

def test(f, fixture):
    for fixt in fixture:
        try:
            fi = Request({})
            fi.values = MultiDict(mapping = fixt)
            result = f(fi)
            print "RESULT for ", f.__name__," is {", result, "}"
        except Exception as e:
            print "EXCEPTION for",f.__name__, str(e)

test(views.preauthGoodVars, fixture)


