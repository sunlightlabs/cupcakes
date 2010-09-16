from cupcakes import settings
from cupcakes.data import RECENT_SORT, submission_lookup, tv_lookup
from cupcakes.forms import SubmissionForm
from flask import Module, Response, g, redirect, render_template, request, session, url_for
from urlparse import urlparse
import datetime
import pytz

submission = Module(__name__)

@submission.route('/flag', methods=['POST'])
def flag():
    
    sid = request.form.get('submission', None)
    
    if sid:
        submission = submission_lookup(sid)
        if 'ok' in request.args:
            submission['flagged'] = False
            submission['removed'] = False
            submission['approved'] = True
        elif 'remove' in request.args:
            submission['flagged'] = True
            submission['removed'] = True
            submission['approved'] = False
        elif not submission.get('approved', False):
            submission['flagged'] = True
        g.db.submissions.save(submission)
        
    return Response("{}", mimetype="application/json")
        
@submission.route('/submit', methods=['POST'])
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
        channel = tv_lookup(submission['tv_channel'])
        if channel:
            submission['tv_channel'] = '%s %s %s' % (channel['callsign'], channel['network'], channel['channel'])
        else:
            submission['tv_channel'] = 'unknown'
    
    # location lookup
    location = g.geo.zipcode_lookup(submission['zipcode'])
        
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

@submission.route('/thanks', methods=['GET'])
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