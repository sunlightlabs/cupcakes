#!/usr/bin/env python
from cupcakes import settings
from cupcakes.geo import YahooGeocoder
from pymongo import GEO2D
from pymongo.connection import Connection
from saucebrush import run_recipe
from saucebrush.emitters import DebugEmitter, CSVEmitter, MongoDBEmitter
from saucebrush.filters import FieldAdder, FieldMerger, FieldModifier, FieldRemover, FieldRenamer, Filter
from saucebrush.sources import CSVSource
from saucebrush.utils import Files
import json
import os

OUTFIELDS = ('power','callsign','network','channel','city','state','latitude','longitude')

# geocoder

class Geocoder(Filter):
    
    def __init__(self):
        super(Geocoder, self).__init__()
        self.cache = {}
        self.geocoder = YahooGeocoder(settings.YAHOO_APPID)
    
    def load_cache(self, path):
        f = open(os.path.abspath(path), 'r')
        self.cache = json.load(f)
        f.close()
    
    def write_cache(self, path):
        f = open(os.path.abspath(path), 'w')
        json.dump(self.cache, f)
        f.close()
    
    def process_record(self, record):
        
        key = "%s, %s" % (record['city'], record['state'])
        
        loc = self.cache.get(key, None)
        
        if loc is None:
            loc = self.geocoder.lookup(city=record['city'], state=record['state'])
            print "--- %s (%s, %s)" % (key, loc['latitude'], loc['longitude'])
            self.cache[key] = loc
        
        if loc:
            record['location'] = [float(loc['latitude']), float(loc['longitude'])]
        
        return record
    
geocoder = Geocoder()
geocoder.load_cache('data/geo_citystate.json')

# emitters

csv_out = CSVEmitter(open('data/broadcasttv.csv', 'w'), fieldnames=OUTFIELDS)

mongo_host = settings.MONGODB_HOST if hasattr(settings, 'MONGODB_HOST') else 'localhost'
mongo_port = settings.MONGODB_PORT if hasattr(settings, 'MONGODB_PORT') else 27017
mongo_conn = Connection(mongo_host, mongo_port)
mongo_out = MongoDBEmitter('cupcakes', 'tvstations', conn=mongo_conn, drop_collection=True)

# parse full power csv

run_recipe(
    CSVSource(open('data/fullpower.csv')),
    FieldAdder('power', 'high'),
    FieldRemover((
        'DMA',
        'NL',
        'FACIL\nID NO',
        '\nDIGITAL CHAN',
        'HRDSHP WVR',
        'LICENSEE',
        'SIGNAL & CONSTRUCTION ISSUES',
        'ANALOG TERMINATION DATE',
    )),
    FieldRenamer({
        'callsign': 'CALLSIGN',
        'network': 'NETWORK',
        'channel': 'VIRTUAL CHAN',
        'city': 'CITY',
        'state': 'ST',
    }),
    FieldModifier('channel', lambda s: int(s)),
    geocoder,
    #csv_out,
    mongo_out,
)

# parse low power csv

run_recipe(
    CSVSource(open('data/lowpower.csv')),
    FieldAdder('power', 'low'),
    FieldAdder('network', ''),
    FieldRemover((
        'DIGITAL APPL STATUS',
        'LP-ONLY COMMUNITY',
        "DMA Rank '08-'09",
        'FACILITY ID',
        'LICENSEE NAME',
        'ZIP CODES',
        'FACILITY TYPE',
        'DIGITAL APPL TYPE',
        "AFF'L",
    )),
    FieldRenamer({
        'callsign': 'CALL SIGN',
        'channel': 'CH',
        'state': 'ST',
    }),
    FieldMerger({'city': ('DMA Name (Nielsen)', 'COMMUNITY OF LICENSE')},
                lambda city, comm: city or comm),
    FieldModifier('city', lambda s: s.upper()),
    FieldModifier('channel', lambda s: int(s)),
    geocoder,
    #csv_out,
    mongo_out,
)

# write geocode cache back to disk

geocoder.write_cache('data/geo_citystate.json')

# ensure geo index

mongo_conn.cupcakes.tvstations.ensure_index([("location", GEO2D)])