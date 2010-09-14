from cupcakes import settings
from flask import g
from pymongo import DESCENDING
from pymongo.objectid import ObjectId
import re

RECENT_SORT = [('timestamp', DESCENDING), ('date_aired', DESCENDING)]

# station stuff

def submission_lookup(sid):
    return g.db.submissions.find_one({u'_id': ObjectId(sid)})

def tv_lookup(zip_or_id):

    if zip_or_id:
        
        if re.match('\d{5}', zip_or_id):
    
            location = g.geo.zipcode_lookup(zip_or_id)

            if location:

                center = [location['latitude'], location['longitude']]
                radius = getattr(settings, "TV_LOOKUP_RADIUS", 1.25)
                res = g.db.tvstations.find({
                    "power": "high",
                    "location" : {"$within" : {"$center" : [center, radius]}}
                }).sort('channel').limit(20)
        
                return res or []
                
        else:
            
            return g.db.tvstations.find_one({u'_id': ObjectId(zip_or_id)})
        
    return []