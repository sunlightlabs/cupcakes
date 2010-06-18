from cupcakes import settings
from cupcakes.forms import SubmissionForm
from flask import Flask, render_template, request, session
from pymongo import Connection

app = Flask(__name__)

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
    return render_template('index.html', form=form)

@app.route('/submit', methods=['POST'])
def submit():
    
    form = SubmissionForm(request.form)
    
    if not form.referrer.data:
        form.referrer.data = request.referrer
    
    if form.validate():
        session['referrer'] = form.referrer.data
        g.db.submissions.save(form.referrer.data)
        return redirect(url_for('thanks'))
        
    return render_template('index.html', form=form)

@app.route('/thanks', methods=['GET'])
def thanks():
    referrer = session.pop('referrer', None)
    return render_template('thanks.html', referrer=referrer)