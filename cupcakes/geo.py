import json
import urllib
import urllib2

GEO_PARAMS = ['street','city','state','zip','location','output','postal']

class YahooGeocoder(object):
        
    def __init__(self, appid):
        self.appid = appid
        
    def lookup(self, **params):
        
        for key in params.iterkeys():
            if key not in GEO_PARAMS:
                raise ValueError('%s is not a valid lookup parameter' % key)
                
        params['appid'] = self.appid
        params['flags'] = 'JT'
        
        qs = urllib.urlencode(params)
        url = "http://where.yahooapis.com/geocode?%s" % qs
        
        js = json.load(urllib2.urlopen(url))
        
        rs = js['ResultSet']
        
        if 'Results' in rs:
            
            loc = rs['Results'][0]
            loc['latitude'] = float(loc['latitude'])
            loc['longitude'] = float(loc['longitude'])
        
            return loc