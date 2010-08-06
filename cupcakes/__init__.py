from cupcakes import settings
from cupcakes.forms import SubmissionForm, FilterForm
from cupcakes.geo import YahooGeocoder
from flask import Flask, Response, g, render_template, redirect, request, session, url_for
from pymongo import Connection
import datetime
import json
import math
import pytz
import re
import urllib

app = Flask(__name__)

# jinja2 loading

@app.template_filter('datetimeformat')
def datetimeformat_filter(value, format='%b %d %I:%M %p'):
    return value.strftime(format)
    
# geo stuff

geo = YahooGeocoder(settings.YAHOO_APPID)

# request lifecycle

conn = Connection(settings.MONGODB_HOST or 'localhost', settings.MONGODB_PORT or 27017)

@app.before_request
def before_request():
    g.db = conn.cupcakes
    
@app.after_request
def after_request(response):
    return response
    
# application

@app.route('/')
def index():
    form = SubmissionForm(request.form)
    recent = g.db.submissions.find().sort('-timestamp').limit(5)
    return render_template('index.html', form=form, recent=recent)

@app.route('/submit', methods=['POST'])
def submit():
    
    form = SubmissionForm(request.form)
    
    if not form.referrer.data:
        form.referrer.data = request.referrer
    
    if form.validate():
        
        session['referrer'] = form.referrer.data
        
        submission = form.data.copy()
        submission['timestamp'] = datetime.datetime.utcnow()
        
        # location lookup
        location = geo.lookup(postal=submission['zipcode'])
        if location:
            submission['city'] = location.get('city', None)
            submission['state'] = location.get('statecode', None)
            submission['latitude'] = location.get('latitude', None)
            submission['longitude'] = location.get('longitude', None)
            submission['timezone'] = location.get('timezone', None)
        
        # date conversion
        d = submission['date']
        (h, m) = (int(t) for t in submission['time'].split(":"))
        submission['date_aired'] = datetime.datetime(d.year, d.month, d.day, h, m)
        del submission['date']
        del submission['time']

        # timezone conversion
        if submission['timezone']:
            tz = pytz.timezone(submission['timezone'])
            tz_dt = tz.localize(submission['date_aired'])
            submission['date_aired_utc'] = tz_dt.astimezone(pytz.utc)
        
        g.db.submissions.save(submission)
        
        return redirect(url_for('thanks'))
        
    return render_template('index.html', form=form)

@app.route('/thanks', methods=['GET'])
def thanks():
    referrer = session.pop('referrer', None)
    return render_template('thanks.html', referrer=referrer)

@app.route('/browse', methods=['GET'])
def browse():

    form = FilterForm(request.args)
    
    page = int(request.args.get('page', 1))
    limit = settings.PAGE_SIZE
    offset = limit * (page - 1)
    
    spec = {}
    qdesc_phrases = []
        
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

    params = request.args.copy()
    if 'page' in params:
        del params['page']
    
    submissions = g.db.submissions.find(spec).sort('-timestamp').skip(offset).limit(limit)
    total = g.db.submissions.find(spec).count()
    last_page = int(math.ceil(float(total) / float(limit)))
    
    if page > last_page:
        if last_page > 1:
            params['page'] = last_page
            return redirect('/browse?%s' % urllib.urlencode(params))
        else:
            return redirect('/browse')
    
    pager = {
        'has_previous': offset > 0,
        'has_next': total > offset + limit,
        'offset': offset,
        'limit': limit,
        'page': page,
        'page_start': offset + 1,
        'page_end': min(offset + limit, total),
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
    
@app.route('/submissions.json', methods=['GET'])
def download():
    def gen():
        for d in g.db.submissions.find():
            yield {
                'id': "%s" % d['_id'],
                'mediatype': d['mediatype'],
                'for_against': d['for_against'],
                'radio_callsign': d['radio_callsign'],
                'tv_provider': d['tv_provider'],
                'tv_channel': d['tv_channel'],
                'zipcode': d['zipcode'],
                'candidate': d['candidate'],
                'sponsor': d['sponsor'],
                'description': d['description'],
                'date_aired': d['date_aired'].isoformat(),
                'state': d['state'],
            }
    js = json.dumps([d for d in gen()])
    return Response(js, mimetype="application/json")