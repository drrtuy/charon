#!/usr/bin/python
import charon
import unittest
from datetime import date, datetime
from time import time
from hashlib import sha256
from flask import Request, request, session
#from flask import request
from werkzeug import MultiDict, EnvironHeaders
from werkzeug.test import EnvironBuilder
import psycopg2 as pg
import json
from os import environ
from base64 import b64encode

class CharonTestCase(unittest.TestCase):

    def db_conn(self):
        h = charon.app.config.get('DB_HOST')
        d = charon.app.config.get('DB_NAME')
        u = charon.app.config.get('DB_USER') 
        p = charon.app.config.get('DB_PASS')
        try:
            return pg.connect(host = h, user = u, password = p, database = d)            
        except pg.Error as e:
            print "\n",e,"\n"

    def setUp(self):
        #charon.app.config['TESTING'] = True
        
        charon.app.config.update(
            SHOPSTER_URL = environ.get('SHOPSTER_AUTH_URL'),
            SHOPSTER_SECRET = 'ech5haisho8Ohri',
            DB_HOST = 'z3_postgres_1',
            DB_USER = 'charon',
            DB_PASS = 'ne9lahngahXah8n',
            DB_NAME = 'radius',
        )
        
        charon.app.config.from_object('charon.settings')
        charon.app.testing = True
        self.app = charon.app.test_client()
        self.dbConn = self.db_conn()

    def tearDown(self):
        if self.dbConn:
            self.dbConn.close()
    
    #craft a proper environment to make a proper json Request
    def test_postauth_allow_subs(self):
        clientMac = userName = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in': '3600', 'session_hash': 'splash'}
        r = charon.app.test_request_context('/v1/radius/subs/', method='POST',\
         content_type = 'application/json', data = json.dumps(inputData))
        result = charon.views.allowRadiusSubs(r.request)
        self.assertTrue(result)

        cur = self.dbConn.cursor()
        goodResSet = (userName, 'Cleartext-Password', '+=', 'aeChei3A')
        cur.execute('SELECT * from radcheck where username = %s;', (userName,) )
        result = cur.fetchall()
        self.assertTrue(result)
        self.assertIn(goodResSet, [row[1:] for row in result])
        
        goodResSet = (userName, 'Session-Timeout', '+=', '600')
        cur.execute('SELECT * from radreply where username = %s', (userName,) )
        result = cur.fetchall()
        self.assertTrue(result)
        self.assertIn(goodResSet, [row[1:] for row in result])

        cur.execute('DELETE FROM radreply WHERE username = %s;', (userName,))
        cur.execute('DELETE FROM radcheck WHERE username = %s;', (userName,))
        self.dbConn.commit()
        cur.close()

    def test_preauth_wrongmethod(self):
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com'}
        meth = [ 'PUT', 'DELETE', 'PATCH', 'TRACE']
        for m in meth:
            with self.app as c:
                rv = c.open(path='/preauth/', data = f, method = m)
                self.assertEqual(rv.status_code, 405)
    """
    def test_preauth_wrongvarsets(self):
        f1 = {}
        f2 = {'client_id': 'blabla:bla:bla'}
        f3 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': 'AA:BB:CC:DD:EE:FF'} 
        f4 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319'}
        f5 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319'}

        fixture = [f1, f2, f3, f4, f5]
        for f in fixture:
            rv = self.app.post(path='/preauth/', data = f)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('Error', rv.data)
        return 

    def test_preauth_shopster_outage(self):
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': 'outage', 'entrypoint_id': '40D00276F319', 'hotspot_login_url': 'http://hotspot.zerothree.su/login'}
        with self.app as c:
            rv = c.post(path='/preauth/', data = f)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('Shopster', rv.data)

    def test_preauth_goodvarset(self):
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com', 'hotspot_login_url': 'http://hotspot.zerothree.su/login'}
        with self.app as c:
            rv = c.post(path='/preauth/', data = f)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('document.redirect.submit()', rv.data)
            cursor = self.dbConn.cursor()

            cursor.execute("DELETE FROM charon_clients WHERE client_id ='AA:BB:CC:DD:EE:FF'  AND hotspot_id='40D00276F319';")

            self.dbConn.commit()
            cursor.close()
    
    def test_postauth_wrongmethod(self):
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com'}
        meth = ['GET', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'TRACE']
        for m in meth:
            with self.app as c:
                rv = c.open(path='/v1/radius/subs/', data = f, method = m)
                #print rv.status_code
                self.assertEqual(rv.status_code, 405)

    def test_postauth_wrongvarsets(self):
        f1 = {}        
        f2 = {'client_id': 'blabla:bla:bla'}
        f3 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': 'AA:BB:CC:DD:EE:FF'} 
        f4 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319'}
        f5 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit': '-1'}
        f6 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit': '-1', 'session_timeout': '60' }
        f7 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit': '60', 'session_timeout': '-1' }
        f8 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '60', 'next_conn_in': '-1'}
        f9 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '60', 'next_conn_in':   '3600', 'session_hash': '-1'}

        fixture = [f1, f2, f3, f4, f5,f6,f7,f8,f9]
        for f in fixture:
            rv = self.app.post(path='/v1/radius/subs/', data = f)
            #print "code", repr(rv.status_code)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('"result": "fail"', rv.data)
        return
    """        
    def get_hash(self):
        secret = charon.app.config.get('SHOPSTER_SECRET')
        day = datetime.now().strftime('%d')
        salt = '{0}:{1}'.format(secret, day)
        #today = str(date.today().day)
        expectedHash = b64encode( sha256(salt).hexdigest() )
        return expectedHash

    def test_authenticated(self):
        secret = 'Basic {0}'.format(self.get_hash())
        h = {'Authorization': secret}
        r = Request({})
        r.headers = MultiDict(h)
        self.assertTrue(charon.views.authenticated(r))
    
    def test_postauth_badauth(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
        f = json.dumps(inputData)
        fixture = [f]
        h = {'Authorization': '123 {0}1'.format(self.get_hash())}
        for f in fixture:
            rv = self.app.post(path='/v1/radius/subs/', data = f, headers = h,\
content_type = 'application/json')
            self.assertEqual(rv.status_code, 200)
            self.assertIn('"auth": "fail"', rv.data)
            self.assertIn('"result": "fail"', rv.data)
        return

    def test_postauth_noauth(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
        f = json.dumps(inputData)
        fixture = [f]
        for fi in fixture:
            rv = self.app.post(path='/v1/radius/subs/', data = fi,\
content_type = 'application/json')
            self.assertEqual(rv.status_code, 200)
            self.assertIn('"auth": "fail"', rv.data)
            self.assertIn('"result": "fail"', rv.data)
        return
    """        
    def test_postauth_formatOk(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
        for k,v in inputData.iteritems():
            self.assertTrue(charon.views.formatOk('postauthGoodVars', k, v))
        
    
    def test_postauth_goodvarsets(self):
        clientMac = 'AA:BB:CC:DD:EE:EE'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in': '3600', 'session_hash': 'splash'}
        fixtures = json.dumps(inputData)      
        secret = 'Basic {0}'.format(self.get_hash())
        h = {'Authorization': secret}  
        preauth_fixtures = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com', 'hotspot_login_url': 'http://hotspot.zerothree.su/login'}

        with self.dbConn.cursor() as cursor:            
            with self.app as c:
                c.post(path='/preauth/', data = preauth_fixtures)
                rv = c.post(path='/v1/radius/subs/', data = fixtures, headers = h,
    content_type = 'application/json')
                self.assertEqual(rv.status_code, 200)
                self.assertIn('"auth": "ok"', rv.data)
                self.assertIn('"result": "ok"', rv.data)
                        
            #cursor.execute("DELETE FROM radacct WHERE acctuniqueid='79e685ac1041c847cb31bfe81390beee';")         
            cursor.execute("DELETE FROM charon_clients WHERE client_id ='AA:BB:CC:DD:EE:EE'  AND hotspot_id='40D00276F319';")
            self.dbConn.commit()    
    """        
    #postpostauth
    """        
    def test_postpostauth_wrongmethod(self):
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319'}
        meth = ['PUT', 'DELETE', 'PATCH', 'HEAD', 'TRACE']
        for m in meth:
            with self.app as c:
                rv = c.open(path='/postpostauth/', data = f, method = m)
                self.assertEqual(rv.status_code, 405)

    def test_postpostauth_wrongvarsets(self):
        f1 = {}
        f2 = {'client_id': 'blabla:bla:bla'}
        f3 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': 'AA:BB:CC:DD:EE:FF'} 
        f4 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319'}
        f5 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319'}

        fixture = [f1, f2, f3, f4, f5]
        for f in fixture:
            rv = self.app.post(path='/postpostauth/', data = f)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('Error', rv.data)
        return 

    def test_postpostauth_goodvarset(self):        
        clientMac = 'AA:BB:CC:DD:EE:CE'                
        fixtures = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319'}
        preauth_fixtures = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com', 'hotspot_login_url': 'http://hotspot.zerothree.su/login'}
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
        postauth_fixtures = json.dumps(inputData)
        secret = 'Basic {0}'.format(self.get_hash())
        postauth_h = {'Authorization': secret}
        #postauth_h = {'Authorization': self.get_hash()}
        with self.app as c:
            c.post(path='/preauth/', data = preauth_fixtures)
            c.post(path='/v1/radius/subs/', data = postauth_fixtures,
 headers = postauth_h, content_type = 'application/json')
            rv = c.post(path='/postpostauth/', data = fixtures)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('document.login.submit()', rv.data)


        cursor = self.dbConn.cursor()
        cursor.execute("DELETE FROM charon_clients WHERE client_id ='AA:BB:CC:DD:EE:CE'  AND hotspot_id='40D00276F319';")
        self.dbConn.commit()
        cursor.close()
    """        
    #ubiquity
    """
    def test_preauth_ubiquity(self):
        client_id = 'AA:BB:CC:DD:EE:FF'
        hotspot_id = '44:d9:e7:48:81:63'
        q = "DELETE FROM charon_clients WHERE client_id ='{0}'  AND hotspot_id='{1}';".format(client_id, hotspot_id)
        fixt = [ ]
        fixt.append( 'id={0}&ap={0}&t{0}=&url=http://habr.ru/&ssid=lobster'.format( client_id, hotspot_id, time() ) )

        for f, e in zip( fixt, range( len(fixt) ) ):
            rv = self.app.get(path = '/preauth/', query_string = f )
            if e:
                self.assertNotEqual(rv.status_code, 200)
            else:
                self.assertEqual(rv.status_code, 200)
                self.assertIn('document.redirect.submit()', rv.data)
                self.assertNotIn('value="None"', rv.data)

                self.sql_call_and_commit( q )
    """
    def sql_call_and_commit(self, query):
            cursor = self.dbConn.cursor()
            cursor.execute(query)
            self.dbConn.commit()
            cursor.close()     

        
    def test_ubiquity_isubiquity(self):
        fixt = []
        fixt.append( {"auth_type": "splash", "hotspot_id": "44:d9:e7:48:81:63", "controller_address": "charon.zerothree.su", "client_id": "24:0a:64:94:a3:a1", "traffic_limit": "77", "controller_password": "lobster", "entrypoint_id": "44:d9:e7:48:81:63", "session_timeout": "600", "next_conn_in": "120", "controller_user": "admin", "session_hash": "qweqweqweqwe", "controller_port": "8443"}
        )
        fixt.append( {"auth_type": "splash", "hotspot_id": "44:d9:e7:48:81:63", "client_id": "24:0a:64:94:a3:a1", "traffic_limit": "77", "controller_password": "lobster", "entrypoint_id": "44:d9:e7:48:81:63", "session_timeout": "600", "next_conn_in": "120", "controller_user": "admin", "session_hash": "qweqweqweqwe", "controller_port": "8443"}
        )
        fixt.append( {"auth_type": "splash", "hotspot_id": "44:d9:e7:48:81:63", "controller_address": "charon.zerothree.su", "client_id": "24:0a:64:94:a3:a1", "traffic_limit": "77", "controller_password": "lobster", "entrypoint_id": "44:d9:e7:48:81:63", "session_timeout": "600", "next_conn_in": "120", "controller_user": "admin", "session_hash": "qweqweqweqwe"}
        )
        fixt.append( {} )
        for f, e in zip( fixt, range( len(fixt) ) ):
            r = charon.app.test_request_context('/v1/radius/subs/', method='POST',\
             content_type = 'application/json', data = json.dumps(f))
            if e:
                self.assertFalse( charon.views.isUbiquity(r.request) )
            else:
                self.assertTrue( charon.views.isUbiquity(r.request) )         

    def test_allow_ubiquity_subs(self):
        fixt = []
        fixt.append( {"auth_type": "splash", "hotspot_id": "44:d9:e7:48:81:63", "controller_address": "95.213.200.85", "client_id": "	d0:53:49:de:8b:03", "traffic_limit": "77", "controller_password": "lobster", "entrypoint_id": "44:d9:e7:48:81:63", "session_timeout": "600", "next_conn_in": "120", "controller_user": "admin", "session_hash": "qweqweqweqwe", "controller_port": "8443"}
        )
        fixt.append( {"auth_type": "splash", "hotspot_id": "44:d9:e7:48:81:63", "client_id": "24:0a:64:94:a3:a1", "traffic_limit": "77", "controller_password": "lobster", "entrypoint_id": "44:d9:e7:48:81:63", "session_timeout": "600", "next_conn_in": "120", "controller_user": "admin", "session_hash": "qweqweqweqwe", "controller_port": "8443"}
        )
        fixt.append( {"auth_type": "splash", "hotspot_id": "44:d9:e7:48:81:63", "controller_address": "95.213.200.85", "client_id": "24:0a:64:94:a3:a1", "traffic_limit": "77", "controller_password": "lobster", "entrypoint_id": "44:d9:e7:48:81:63", "session_timeout": "600", "next_conn_in": "120", "controller_user": "admin", "session_hash": "qweqweqweqwe"}
        )
        fixt.append( {} )
        for f, e in zip( fixt, range( len(fixt) ) ):
            r = charon.app.test_request_context('/v1/radius/subs/', method='POST',\
             content_type = 'application/json', data = json.dumps(f))
            if e:
                self.assertFalse( charon.views.allowUbiquitySubs(r.request) )
            else:
                self.assertTrue( charon.views.allowUbiquitySubs(r.request) )

    def test_preauth_gethotspotid(self):
        # fixt format ( data, method, result )
        fixt = []
        fixt.append( ( {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com', 'hotspot_login_url': 'http://hotspot.zerothree.su/login'}, 'POST', 'mikrotik'  ) )
        fixt.append( ( 'ap=44:d9:e7:48:81:63', 'GET', 'ubiquity' ) )
        fixt.append( ( '/preauth/?cmd=login&mac=24:0a:64:94:a3:a1&essid=shopster&ip=172.31.99.216&apname=ac%3Aa3%3A1e%3Ac5%3A8c%3A7c&vcname=instantC5%3A8C%3A7C&switchip=securelogin.arubanetworks.com&url=http%3A%2F%2Fyandex.ru%2F', 'GET', 'aruba' ) )
        fixt.append( ('ap=outage', 'GET', 'outage' ) )
        fixt.append( ( {}, 'POST', None ) )
        fixt.append( ( '', 'GET', None ) )            
        def make_test(f):
            ( data, method, result ) = f
            #print "make_test", f
            if method == 'POST':
                r = charon.app.test_request_context('/preauth/', method = method,\
                    data =  data
                )
            else:
                r = charon.app.test_request_context('/preauth/', method = method,\
                    query_string =  data
                )
            #print "make_test result", charon.views.getHotspotId(r.request)
            if isinstance( result, str ):
                self.assertIn( result, charon.views.getHotspotId(r.request) )
            elif result == None:
                self.assertEqual( None, charon.views.getHotspotId(r.request) )

        for f, e in zip( fixt, range( len(fixt) ) ):
            make_test(f)

    "Add Ruckus, Aruba, OpenWRT"

    def test_getPreauthTemplateData(self):
    
        # fixt format ( data, method, result )
        mt_id = '40D00276F319'
        uni_id = u'44:d9:e7:48:81:63'
        fixt = []
        d = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': mt_id, 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com', 'hotspot_login_url': 'http://hotspot.zerothree.su/login'}
        r = {'hotspot_login_url': u'http://hotspot.zerothree.su/login', 'hotspot_id': u'40D00276F319', 'entrypoint_id': u'40D00276F319', 'client_id': u'AA:BB:CC:DD:EE:FF'}
        fixt.append( ( d, 'POST', d ) )
        s = 'id={0}&ap={1}&t={2}&url=http://habr.ru/&ssid=lobster'.format('24:0a:64:94:a3:a1', uni_id, time() )
        r =  {'hotspot_login_url': u'http://habr.ru/', 'hotspot_id': u'44:d9:e7:48:81:63', 'entrypoint_id': u'44:d9:e7:48:81:63', 'client_id': u'24:0a:64:94:a3:a1', 'original_url': u'http://habr.ru/'}
        fixt.append( ( s, 'GET', r ) ) 
        fixt.append( ('ap=outage', 'GET', {} ) )
        fixt.append( ( {}, 'POST', {} ) )
        fixt.append( ( '', 'GET', {} ) )            

        def make_test(f):
            ( data, method, result ) = f

            if isinstance(data, dict) and data.get('hotspot_id', None) == mt_id:
                session['hotspotType'] = 'mikrotik'
            elif isinstance(data, str) and uni_id in data:
                session['hotspotType'] = 'ubiquity'                
            else:
                session['hotspotType'] = 'mikrotik'

            #print charon.views.getPreauthTemplateData(request)
            
            for k, v in charon.views.getPreauthTemplateData(request).items():
                if v == None and result == {}:
                    pass
                else:
                    self.assertEqual( str(v), result.get(k, None) )              

        for f, e in zip( fixt, range( len(fixt) ) ):
           ( data, method, result ) = f
           with charon.app.test_client() as c:            
               if method == 'POST':     
                  c.post( path='/preauth/', data = data )
                  make_test(f)
               elif method == 'GET':
                  c.get( path='/preauth/', query_string = data )
                  make_test(f)
              

if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(CharonTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
