#!/usr/bin/python
import charon
import unittest
from datetime import date
from hashlib import sha256
from flask import Request
from flask import request
from werkzeug import MultiDict, EnvironHeaders
import psycopg2 as pg
import json
from os import environ
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
        charon.app.config.update(
            SHOPSTER_URL = environ.get('SHOPSTER_AUTH_URL'),
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

    #craft a proper environment to make a proper json Request
    def test_postauth_allow_subs(self):
        clientMac = userName = 'AA:BB:CC:DD:EE:FF'
        inputData = {'client_id': clientMac, 'hotspot_id': '40D00276F319', 'hotspot_id': '40D00276F319', 'traffic_limit':  '60', 'session_timeout':  '600', 'next_conn_in':   '3600', 'auth_type': 'splash'}
        #r = Request({})
        r = charon.app.test_request_context('/v1/radius/subs/', method='POST')
        r.headers = EnvironHeaders({'Content-Type': 'application/json'})
        #r.values = MultiDict(inputData)
        r.data = json.dumps(inputData)
        print r
        #result = charon.views.allowRadiusSubs(r)
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

if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(CharonTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
