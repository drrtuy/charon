
class Hotspot(dict):
    def __init__(self, *arg, **kw):
        super(Hotspot, self).__init__(*arg, **kw)
        self['client_id'] = ''
        self['hotspot_id'] = ''
        self['original_url'] = ''
        self['hotspot_login_url'] = ''
        self.type = None
        
    def update_model(self, request):
        pass

    def get_model(self):
        pass
        """
        return {
            'client_id': self.client_id, 
            'hotspot_id': self.hotspot_id,
            'original_url': self.original_url,
            'hotspot_login_url': self.hotspot_login_url
        }
        """

class Ruckus(Hotspot):
    def __init__(self):
        Hotspot.__init__(self)
        self._zone_director_passed = False        

    def isRuckusAuthReq(self):
        return self._zone_director_passed 

    def zoneDirectorPassed(self):
        self._zone_director_passed = True
