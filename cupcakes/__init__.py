from cStringIO import StringIO
from cupcakes import settings
from cupcakes.forms import ContactForm, FilterForm, SubmissionForm, US_STATES
from cupcakes.geo import YahooGeocoder
from flask import Flask, Response, g, render_template, redirect, request, session, url_for, json
from pymongo import Connection, DESCENDING, GEO2D
from pymongo.objectid import ObjectId
from urlparse import urlparse
import csv
import datetime
import flask
import math
import pytz
import re
import urllib

app = Flask(__name__)

# jinja2 loading

@app.template_filter('datetimeformat')
def datetimeformat_filter(value, format='%b %d %I:%M %p'):
    return value.strftime(format)

@app.template_filter('airedon')
def datetimeformat_filter(s):
    mt = s.get('mediatype', None)
    if mt == 'radio':
        return s.get('radio_callsign')
    elif mt == 'television':
        return u"%s (%s)" % (s.get('tv_channel', ''), s.get('tv_provider', ''))
    elif mt == 'internet':
        return 'Internet'
    return u"unknown"
    
# geo stuff

geo = YahooGeocoder(settings.YAHOO_APPID)

def zipcode_lookup(zipcode):
    app.logger.debug('[GEO] looking up zipcode %s' % zipcode)
    lookup = g.db.geo.find_one({'zipcode': zipcode})
    if lookup:
        app.logger.debug('[GEO] %s found in mongo cache' % zipcode)
        location = lookup['geo']
    else:
        app.logger.debug('[GEO] %s mongo cache miss' % zipcode)
        location = geo.lookup(q=zipcode)
        if location:
            app.logger.debug('[GEO] %s found in Yahoo API' % zipcode)
            g.db.geo.save({
                'zipcode': zipcode,
                'geo': location,
            })
        else:
            app.logger.debug('[GEO] %s Yahoo API miss' % zipcode)
    return location

# station stuff

def tv_lookup(zipcode):
    
    if zipcode and re.match('\d{5}', zipcode):
        
        location = zipcode_lookup(zipcode)
    
        if location:
    
            center = [location['latitude'], location['longitude']]
            radius = 1.25
            res = g.db.tvstations.find({
                "power": "high",
                "location" : {"$within" : {"$center" : [center, radius]}}
            }).sort('channel').limit(20)
            
            return res or []
            
    return []

# request lifecycle

conn = Connection(settings.MONGODB_HOST or 'localhost', settings.MONGODB_PORT or 27017)
conn.cupcakes.tvstations.ensure_index([("location", GEO2D)])

@app.before_request
def before_request():
    g.db = conn.cupcakes
    
    referrer = session.get('referrer', None)
    if not referrer:
        session['referrer'] = request.referrer
    
@app.after_request
def after_request(response):
    return response
    
# application

RECENT_SORT = [('timestamp',DESCENDING), ('date_aired', DESCENDING)]
US_STATE_CODES = [s[0] for s in US_STATES]
US_STATE_NAMES = [s[1].upper() for s in US_STATES]

@app.route('/')
def index():
    """ The index with the submission form and recent submissions.
    """
    
    form = SubmissionForm(request.form)
    form.referrer.data = session.get('referrer', '')
    recent = g.db.submissions.find().sort(RECENT_SORT).limit(2)
    return render_template('index.html', form=form, recent=recent)

@app.route('/submit', methods=['POST'])
def submit():
    """ On post, save form. The form shows errors if validation fails.
        
        If the form is valid, a further step of geocoding is done.
        The zipcode is passed to Yahoo to get information about the
        county, city, and state that the zipcode is in. This data is then
        cached to save on future geocoding calls.
    """
    
    valid_tv_stations = [('other', 'other')]
    for r in tv_lookup(request.form.get('zipcode', None)):
        name = '%s %s (%s)' % (r['network'], r['channel'], r['callsign'])
        valid_tv_stations.append((str(r['_id']), name))
    
    form = SubmissionForm(request.form)
    form.tv_channel.choices = valid_tv_stations
    
    if not form.referrer.data:
        form.referrer.data = session['referrer']
    
    if not form.validate():
        recent = g.db.submissions.find().sort(RECENT_SORT).limit(3)  
        return render_template('index.html', form=form, recent=recent)
    
    submission = form.data.copy()
    submission['timestamp'] = datetime.datetime.utcnow()
    
    if submission['tv_channel'] == 'other':
        if submission['tv_channel_other']:
            submission['tv_channel'] = submission['tv_channel_other']
    else:
        channel = g.db.tvstations.find_one({u'_id': ObjectId(submission['tv_channel'])})
        if channel:
            submission['tv_channel'] = '%s %s %s' % (channel['callsign'], channel['network'], channel['channel'])
        else:
            submission['tv_channel'] = 'unknown'
    
    # location lookup
    location = zipcode_lookup(submission['zipcode'])
        
    if location:
        submission['city'] = location.get('city', None)
        submission['state'] = location.get('statecode', None)
        submission['latitude'] = location.get('latitude', None)
        submission['longitude'] = location.get('longitude', None)
        submission['timezone'] = location.get('timezone', None)
    
    # date conversion
    month = int(submission['dt_month'])
    day = int(submission['dt_day'])
    year = int(submission['dt_year'])
    (hour, minute) = (int(t) for t in submission['dt_time'].split(":"))
    
    submission['date_aired'] = datetime.datetime(year, month, day, hour, minute)
    
    del submission['dt_month']
    del submission['dt_day']
    del submission['dt_year']
    del submission['dt_time']
    
    submission['flag'] = False

    # timezone conversion
    if 'timezone' in submission and submission['timezone']:
        tz = pytz.timezone(submission['timezone'])
        tz_dt = tz.localize(submission['date_aired'])
        submission['date_aired_utc'] = tz_dt.astimezone(pytz.utc)
    
    g.db.submissions.save(submission)
    
    return redirect(url_for('thanks'))

@app.route('/thanks', methods=['GET'])
def thanks():
    params = {}
    params['form'] = SubmissionForm(request.form)
    referrer = session.get('referrer', None)
    if referrer:
        u = urlparse(referrer)
        params['referrer'] = referrer
        params['referrer_domain'] = u.netloc
        params['return_to_ref'] = u.netloc != settings.DOMAIN
    return render_template('thanks.html', **params)

@app.route('/browse', methods=['GET'])
def browse():
    """ Browse and filter submissions.
        
        Filter parameters:
        candidate - name of candidate
        sponsor - name of sponsor
        state - state in which ad aired (from geocoding of zipcode)
        zipcode - user specified zipcode in which ad aired
    """

    # get filter form
    form = FilterForm(request.args)
    
    # basic paging
    
    page = int(request.args.get('page', 1))
    limit = settings.PAGE_SIZE
    offset = limit * (page - 1)

    # build filter spec and description phrase
    
    spec = {}
    qdesc_phrases = []
    
    if 'q' in request.args and request.args['q']:
    
        regex = re.compile(request.args['q'], re.I)
    
        spec['$or'] = [
            {'candidate': regex},
            {'sponsor': regex},
        ]
        qdesc_phrases.append('related to &#8220;%s&#8221;' % request.args['q'])
        
    else:

        if 'candidate' in request.args and request.args['candidate']:
            spec['candidate'] = re.compile(request.args['candidate'], re.I)
            qdesc_phrases.append('about &#8220;%s&#8221;' % request.args['candidate'])
        
        if 'sponsor' in request.args and request.args['sponsor']:
            spec['sponsor'] = re.compile(request.args['sponsor'], re.I)
            qdesc_phrases.append('sponsored by &#8220;%s&#8221;' % request.args['sponsor'])
    
        if 'state' in request.args and request.args['state']:
            spec['state'] = request.args['state'].upper()
            qdesc_phrases.append('aired in %s' % request.args['state'])
        
        if 'zipcode' in request.args and request.args['zipcode']:
            spec['zipcode'] = request.args['zipcode'].upper()
            if 'state' in request.args and request.args['state']:
                qdesc_phrases.append('(%s)' % request.args['zipcode'])
            else:
                qdesc_phrases.append('aired in %s' % request.args['zipcode'])

    # copy params for returning as querystring
    params = request.args.copy()
    if 'page' in params:
        del params['page']
    
    # get submissions that match filter criteria
    submissions = g.db.submissions.find(spec).sort(RECENT_SORT).skip(offset).limit(limit)
    total = g.db.submissions.find(spec).count()
    last_page = int(math.ceil(float(total) / float(limit)))
    
    # redirect if requested page is greater than max page
    if page > last_page and last_page > 0:
        if last_page > 1:
            params['page'] = last_page
            return redirect('/browse?%s' % urllib.urlencode(params))
        else:
            return redirect('/browse')
    
    # paging data
    pager = {
        'has_previous': offset > 0,
        'has_next': total > offset + limit,
        'offset': offset,
        'limit': limit,
        'page': page,
        'page_start': offset + 1,
        'page_end': min(offset + limit, total),
        'last_page': last_page,
        'previous_page': page - 1,
        'next_page': page + 1,
        'total': total,
    }
    
    return render_template('browse.html',
                           form=form,
                           submissions=submissions,
                           pager=pager,
                           qdesc=' '.join(qdesc_phrases),
                           qs=urllib.urlencode(params))

@app.route('/search', methods=['POST'])
def search():
    
    q = request.form.get('q', '').strip()
    
    if not q:
        return redirect(url_for('index'))
    
    params = {}
    qu = q.upper()
    
    if re.match(r'\d{5}', q):
        params['zipcode'] = q
    
    elif qu in US_STATE_CODES:
        params['state'] = qu
    
    elif qu in US_STATE_NAMES:
        params['state'] = US_STATE_CODES[US_STATE_NAMES.index(qu)]
    
    else:
        params['q'] = q
    
    return redirect('/browse?%s' % urllib.urlencode(params))

@app.route('/download', methods=['GET'])
def download():
    """ Download all submissions as CSV.
    """
    
    headers = ('timestamp', 'mediatype','for_against','radio_callsign',
               'tv_provider','tv_channel','internet_link','zipcode','candidate',
               'sponsor','description','issue','date_aired','city','state')
    
    bffr = StringIO()
    writer = csv.writer(bffr)
    writer.writerow(headers)
    
    for d in g.db.submissions.find():
        row = [d.get(key, '') for key in headers]
        writer.writerow(row)
    
    content = bffr.getvalue()
    bffr.close()
    
    now = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    
    return Response(content, mimetype="text/csv", headers={
        'Content-Disposition': 'Content-Disposition: attachment; filename=sunlightcam-%s.csv' % now,
    })

@app.route('/stations/tv', methods=['GET'])
def stations_tv():
    
    zipcode = request.args.get('zipcode', None)
    stations = []
    
    res = tv_lookup(zipcode)
    
    if res:
        for r in res:
            stations.append({
                'id': str(r['_id']),
                'name': '%s %s (%s)' % (r['network'], r['channel'], r['callsign']),
            })
            
    return Response(json.dumps(stations), mimetype="application/json")

@app.route('/contact', methods=['GET','POST'])
def contact():
    
    if request.method == 'POST':
        form = ContactForm(request.form)
        if form.validate():
            form.send()
            flask.flash("Thank you for contacting us. We'll get back to you shortly.")
            return redirect(url_for('contact'))
    else:
        form = ContactForm()
    
    return render_template('contact.html', form=form)

@app.route('/about', methods=['GET'])
def about():
   return render_template('about.html')
   
@app.route('/use', methods=['GET'])
def use():
  return render_template('use.html')