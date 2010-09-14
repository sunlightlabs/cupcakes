from flask import g
import urllib
import urllib2
try:
    import json
except ImportError:
    import simplejson as json

GEO_PARAMS = ['street','city','state','zip','location','output','postal','q']

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
        print rs
        
        if 'Results' in rs:
            
            for loc in rs['Results']:
                
                if loc['country'] == 'United States':
                    
                    loc['latitude'] = float(loc['latitude'])
                    loc['longitude'] = float(loc['longitude'])
        
                    return loc

    def zipcode_lookup(zipcode):
        lookup = g.db.geo.find_one({'zipcode': zipcode})
        if lookup:
            location = lookup['geo']
        else:
            location = self.lookup(q=zipcode)
            if location:
                g.db.geo.save({
                    'zipcode': zipcode,
                    'geo': location,
                })
        return location