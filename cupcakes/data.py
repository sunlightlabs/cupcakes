from cupcakes import settings
from flask import g
from pymongo import DESCENDING
import re

RECENT_SORT = [('timestamp', DESCENDING), ('date_aired', DESCENDING)]

# station stuff

def tv_lookup(zipcode):

    if zipcode and re.match('\d{5}', zipcode):
    
        location = g.geo.zipcode_lookup(zipcode)

        if location:

            center = [location['latitude'], location['longitude']]
            radius = getattr(settings, "TV_LOOKUP_RADIUS", 1.25)
            res = g.db.tvstations.find({
                "power": "high",
                "location" : {"$within" : {"$center" : [center, radius]}}
            }).sort('channel').limit(20)
        
            return res or []
        
    return []