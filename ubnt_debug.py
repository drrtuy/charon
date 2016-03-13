from __future__ import print_function
import json
#192.168.88.237 ruckus
#192.168.88.244 aruba

a =  {"auth_type": "splash", "hotspot_id": "44:d9:e7:48:81:63", "controller_address": "95.213.200.85", "client_id": "24:0a:64:94:a3:a1", "traffic_limit": "77", "controller_password": "lobster", "entrypoint_id": "44:d9:e7:48:81:63", "session_timeout": "600", "next_conn_in": "120", "controller_user": "admin", "session_hash": "qweqweqweqwe", "controller_port": "8443"}

from unifi.controller import Controller, PYTHON_VERSION
TO = 2  


class Ubnt(Controller):

    def _login(self, version):
        print('Ubnt _login() as {0}'.format(self.username) )

        params = {'username': self.username, 'password': self.password}
        login_url = self.url

        if version is 'v4':
            login_url += 'api/login'
            params = json.dumps(params)
        else:
            login_url += 'login'
            params.update({'login': 'login'})
            if PYTHON_VERSION is 2:
                params = urllib.urlencode(params)
            elif PYTHON_VERSION is 3:
                params = urllib.parse.urlencode(params)

        if PYTHON_VERSION is 3:
            params = params.encode("UTF-8")

        self.opener.open( login_url, params, timeout = TO ).read()

    def _logout(self):
        print('Ubnt._logout()')
        self.opener.open( self.url + 'logout', timeout = TO ).read()



cAddr = '95.213.200.85'
cUser = 'admin'
cPass = 'lobster'
cPort = 8443
cVersion = 'v4'
userName = '24:0a:64:94:a3:a1'
sessionTimeout = '600'
traffLimit = '77'



c = Ubnt(cAddr, cUser, cPass, port=cPort, version=cVersion)
print (c.authorize_guest(userName, sessionTimeout, byte_quota = traffLimit))
#c._logout()



