from cStringIO import StringIO
from cupcakes import settings
from cupcakes.data import RECENT_SORT
from cupcakes.forms import FilterForm, US_STATES
from flask import Module, Response, g, redirect, render_template, request, url_for
import csv
import datetime
import math
import re
import urllib

search = Module(__name__)

US_STATE_CODES = [s[0] for s in US_STATES]
US_STATE_NAMES = [s[1].upper() for s in US_STATES]

@search.route('/browse', methods=['GET'])
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
    
    flagged = False

    # build filter spec and description phrase
    
    spec = {'removed': {'$ne': True}}
    qdesc_phrases = []
    
    if 'q' in request.args and request.args['q']:
    
        regex = re.compile(request.args['q'], re.I)
        
        spec['$or'] = [
            {'candidate': regex},
            {'sponsor': regex},
        ]
        
        qdesc_phrases.append('related to &#8220;%s&#8221;' % request.args['q'])
    
    elif 'flagged' in request.args:    

        spec['flagged'] = True
        flagged = True
    
    else:
        
        spec

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
                           flagged=flagged,
                           qdesc=' '.join(qdesc_phrases),
                           qs=urllib.urlencode(params))

@search.route('/search', methods=['POST'])
def filter():
    
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

@search.route('/download', methods=['GET'])
def download():
    """ Download all submissions as CSV.
    """
    
    headers = ('flagged','timestamp', 'mediatype','for_against','radio_callsign',
               'tv_provider','tv_channel','internet_link','zipcode','candidate',
               'sponsor','description','issue','date_aired','city','state')
    
    bffr = StringIO()
    writer = csv.writer(bffr)
    writer.writerow(headers)
    
    for d in g.db.submissions.find({'removed': {'$ne': True}}):
        row = [d.get(key, '') for key in headers]
        writer.writerow(row)
    
    content = bffr.getvalue()
    bffr.close()
    
    now = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    
    return Response(content, mimetype="text/csv", headers={
        'Content-Disposition': 'Content-Disposition: attachment; filename=sunlightcam-%s.csv' % now,
    })