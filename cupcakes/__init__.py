from cupcakes import settings
from cupcakes.data import RECENT_SORT, tv_lookup
from cupcakes.forms import ContactForm, SubmissionForm
from cupcakes.geo import YahooGeocoder
from cupcakes.views.search import search
from cupcakes.views.submission import submission
from flask import Flask, Response, g, json, render_template, redirect, request, session, url_for
from pymongo import Connection, GEO2D
import flask
import urllib
import urllib2

app = Flask(__name__)
app.register_module(search)
app.register_module(submission)

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

# request lifecycle

conn = Connection(settings.MONGODB_HOST or 'localhost', settings.MONGODB_PORT or 27017)
conn.cupcakes.tvstations.ensure_index([("location", GEO2D)])

@app.before_request
def before_request():
    g.db = conn.cupcakes
    g.geo = YahooGeocoder(settings.YAHOO_APPID)
    
    referrer = session.get('referrer', None)
    if not referrer:
        session['referrer'] = request.referrer
    
@app.after_request
def after_request(response):
    return response

#
# boring app views
#

@app.route('/')
def index():
    """ The index with the submission form and recent submissions.
    """
    
    form = SubmissionForm(request.form)
    form.referrer.data = session.get('referrer', '')
    recent = g.db.submissions.find().sort(RECENT_SORT).limit(2)
    return render_template('index.html', form=form, recent=recent)

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

@app.route('/subscribe', methods=['POST'])
def subscribe():
    
    email = request.form.get('email', None)
    data = {"message": "Something terrible happened. Please reload the page and try again."}
    
    if email:
        
        bsd_url = "http://bsd.sunlightfoundation.com/page/s/sfc"
        response = urllib2.urlopen(bsd_url, urllib.urlencode({"email": email})).read()

        if "Success" in response:
            data["message"] = "Thanks for signing up!"
            
    return Response(json.dumps(data), mimetype="application/json")

@app.route('/about', methods=['GET'])
def about():
   return render_template('about.html')
   
@app.route('/use', methods=['GET'])
def use():
  return render_template('use.html')