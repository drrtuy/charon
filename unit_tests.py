#!/usr/bin/python
import charon
import unittest
from datetime import date, datetime
from hashlib import sha256
from flask import Request
from flask import request
from werkzeug import MultiDict, EnvironHeaders
import psycopg2 as pg
import json
from os import environ
from base64 import b64encode
#from charon import *
#from postauth import *
#from ppauth import *

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
        """
        charon.app.config.update(
            SHOPSTER_URL = environ.get('SHOPSTER_AUTH_URL'),
            SHOPSTER_SECRET = 'ech5haisho8Ohri',
            DB_HOST = 'z3_postgres_1',
            DB_USER = 'charon',
            DB_PASS = 'ne9lahngahXah8n',
            DB_NAME = 'radius',
        )
        """
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
    """
    def test_postauth_goodvarsets(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
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
    """

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

    def test_postauth_formatOk(self):
        clientMac = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
        for k,v in inputData.iteritems():
            self.assertTrue(charon.views.formatOk('postauthGoodVars', k, v))
        
    def test_postauth_goodvarsets(self):
        clientMac = 'AA:BB:CC:DD:EE:EE'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
        fixtures = json.dumps(inputData)      
        secret = 'Basic {0}'.format(self.get_hash())
        h = {'Authorization': secret}  
        #h = {'Authorization': self.get_hash()}
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
    def test_postauth_failidle(self):
        clientMac = 'AA:BB:CC:DD:EE:ED'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'session_hash': 'splash'}
        fixtures = json.dumps(inputData)        
        h = {'Authorization': self.get_hash()}
        preauth_fixtures = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'entrypoint_id': '40D00276F319', 'original_url': 'www.sex.com', 'hotspot_login_url': 'http://hotspot.zerothree.su/login'}
        
        with self.dbConn.cursor() as cursor:         
            with self.app as c:
                c.post(path='/preauth/', data = preauth_fixtures)
                cursor = self.dbConn.cursor()                

                cursor.execute("DELETE FROM radacct WHERE acctuniqueid='79e685ac1041c847cb31bfe81390beeq';")
                self.dbConn.commit()

                cursor.execute("INSERT INTO radacct(\
                            acctsessionid, acctuniqueid, username, groupname, \
                            realm, nasipaddress, nasportid, nasporttype, acctstarttime, acctupdatetime, \
                            acctstoptime, acctinterval, acctsessiontime, acctauthentic, connectinfo_start, \
                            connectinfo_stop, acctinputoctets, acctoutputoctets, calledstationid, \
                            callingstationid, acctterminatecause, servicetype, framedprotocol, \
                            framedipaddress) VALUES\
                    ('8090000f','79e685ac1041c847cb31bfe81390beeq','AA:BB:CC:DD:EE:ED',\
                    ' ',' ','83.219.159.140','wlan1','Wireless-802.11','2015-12-11 12:53:14+00','2015-12-11 12:54:14+00',\
                    now(),'0',60,' ',' ',' ',16009,20093,'40D00276F319','AA:BB:CC:DD:EE:ED',\
                    'Session-Timeout',' ',' ','10.128.15.8');"\
                )
                self.dbConn.commit()
                rv = c.post(path='/v1/radius/subs/', data = fixtures, headers = h,
    content_type = 'application/json')

                from time import sleep                
                sleep(300)
                cursor.execute("DELETE FROM charon_clients WHERE client_id ='AA:BB:CC:DD:EE:ED'  AND hotspot_id='40D00276F319';")
                cursor.execute("DELETE FROM radacct WHERE acctuniqueid='79e685ac1041c847cb31bfe81390beeq';")
                self.dbConn.commit()

                self.assertEqual(rv.status_code, 200)
                self.assertIn('"auth": "ok"', rv.data)
                self.assertIn('"result": "fail"', rv.data)            
    """
  

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

if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(CharonTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
