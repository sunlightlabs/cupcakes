from lxml import etree
import urllib
import urllib2

"""
<ResultSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xmlns="urn:yahoo:maps"
           xsi:schemaLocation="urn:yahoo:maps http://api.local.yahoo.com/MapsService/V1/GeocodeResponse.xsd">
    <Result precision="zip">
        <Latitude>39.142994</Latitude>
        <Longitude>-77.184848</Longitude>
        <Address></Address>
        <City>Gaithersburg</City>
        <State>MD</State>
        <Zip>20877</Zip>
        <Country>US</Country>
    </Result>
</ResultSet>
"""

GEO_PARAMS = ['street','city','state','zip','location','output']

class YahooGeocoder(object):
        
    def __init__(self, appid):
        self.appid = appid
        
    def lookup(self, **params):
        
        for key in params.iterkeys():
            if key not in GEO_PARAMS:
                raise ValueError('%s is not a valid lookup parameter' % key)
                
        params['appid'] = self.appid
        
        qs = urllib.urlencode(params)
        url = "http://local.yahooapis.com/MapsService/V1/geocode?%s" % qs
        
        tree = etree.parse(urllib2.urlopen(url))
        root = tree.getroot()
        
        loc = dict((c.tag.split('}')[1].lower(), c.text) for c in root[0])
        loc['latitude'] = float(loc['latitude'])
        loc['longitude'] = float(loc['longitude'])
        
        return loc
        
        # results = root.text
        # 
        # print "-----", results
        # 
        # if results:
        # 
        #     loc = {}
        #     
        #     print results[0]