#!/usr/bin/python
import charon
import unittest
from datetime import date
from hashlib import sha256
from flask import Request
from werkzeug import MultiDict, EnvironHeaders
import psycopg2 as pg
import json

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
            SHOPSTER_URL = 'http://shopster.zerothree.su:8081/',
            SHOPSTER_SECRET = 'ech5haisho8Ohri',
            DB_HOST = 'z3_postgres_1',
            DB_USER = 'charon',
            DB_PASS = 'ne9lahngahXah8n',
            DB_NAME = 'radius'
        )
        charon.app.testing = True
        self.app = charon.app.test_client()
        self.dbConn = self.db_conn()

    def tearDown(self):
        if self.dbConn:
            self.dbConn.close()

    def test_preauth_wrongmethod(self):
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com'}
        meth = ['GET', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'TRACE']
        for m in meth:
            with self.app as c:
                rv = c.open(path='/preauth/', data = f, method = m)
                self.assertEqual(rv.status_code, 405)

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
        f9 = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '60', 'next_conn_in':   '3600', 'auth_type': '-1'}

        fixture = [f1, f2, f3, f4, f5,f6,f7,f8,f9]
        for f in fixture:
            rv = self.app.post(path='/v1/radius/subs/', data = f)
            #print "code", repr(rv.status_code)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('"result": "fail"', rv.data)
        return

    def get_hash(self):
        secret = charon.app.config.get('SHOPSTER_SECRET')
        today = str(date.today().day)
        expectedHash = sha256(secret.join(today)).hexdigest()
        return expectedHash

    def test_authenticated(self):
        h = {'Authorization': self.get_hash()}
        r = Request({})
        r.headers = MultiDict(h)
        self.assertTrue(charon.views.authenticated(r))

    #craft a proper environment to make a proper json Request
    def test_postauth_allow_subs(self):
        clientMac = userName = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'auth_type': 'splash'}
        r = Request({})
        #r.headers = EnvironHeaders({'Content-Type': 'application/json'})
        #r.values = MultiDict(inputData)
        r.data = json.dumps(inputData)
        result = charon.views.allowRadiusSubs(r)
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

    def test_postauth_badauth(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'auth_type': 'splash'}
        f = json.dumps(inputData)
        fixture = [f]
        h = {'Authorization': self.get_hash().join('123')}
        for f in fixture:
            rv = self.app.post(path='/v1/radius/subs/', data = f, headers = h,\
content_type = 'application/json')
            self.assertEqual(rv.status_code, 200)
            self.assertIn('"auth": "fail"', rv.data)
            self.assertIn('"result": "fail"', rv.data)
        return

    def test_postauth_noauth(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'auth_type': 'splash'}
        f = json.dumps(inputData)
        fixture = [f]
        for fi in fixture:
            rv = self.app.post(path='/v1/radius/subs/', data = fi,\
content_type = 'application/json')
            self.assertEqual(rv.status_code, 200)
            self.assertIn('"auth": "fail"', rv.data)
            self.assertIn('"result": "fail"', rv.data)
        return

    def test_postauth_formatOk(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'auth_type': 'splash'}
        for k,v in inputData.iteritems():
            self.assertTrue(charon.views.formatOk('postauthGoodVars', k, v))
    
#craft a proper environment to make a proper json Request
    def test_postauth_goodvarsets(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'auth_type': 'splash'}
        f = json.dumps(inputData)
        fixture = [f]
        h = {'Authorization': self.get_hash()}
        #print h
        for f in fixture:
            rv = self.app.post(path='/v1/radius/subs/', data = f, headers = h, \
content_type = 'application/json')
            self.assertEqual(rv.status_code, 200)
            self.assertIn('"auth": "ok"', rv.data)
            self.assertIn('"result": "ok"', rv.data)
        return

    #postpostauth

    def test_postpostauth_wrongmethod(self):
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319'}
        meth = ['GET', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'TRACE']
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
        f = {'client_id': 'AA:BB:CC:DD:EE:FF', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319'}
        with self.app as c:
            rv = c.post(path='/postpostauth/', data = f)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('document.redirect.submit()', rv.data)


if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(CharonTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
