from wtforms import Form, validators, ValidationError
from wtforms.fields import DateField, HiddenField, SelectField, TextField, TextAreaField
from wtforms.widgets import TextInput
import datetime

MEDIATYPES = [(c,c) for c in ('','radio','television')]

# date widget

class DateInput(TextInput):
    def __init__(self, *args, **kwargs):
        super(DateInput, self).__init__(*args, **kwargs)
    
    def __call__(self, field, **kwargs):
        html = super(DateInput, self).__call__(field, **kwargs).replace('type="text"', 'type="date"')
        print html
        return html

# validators

class CallsignValidator(object):
    def __call__(self, form, field):
        callsign = field.data.upper()
        if len(callsign) != 4 or not (callsign.startswith('K') or callsign.startswith('W')):
            raise ValidationError(u"Radio station must be 4 characters long and start with K or W")

class MediaTypeValidator(object):
    def __init__(self):
        self.radio_callsign_validator = CallsignValidator()
        self.tv_provider_validator = validators.Required()
        self.tv_channel_validator = validators.Required()
    def __call__(self, form, field):
        if field.data == 'radio':
            self.radio_callsign_validator(form, form.radio_callsign)
        elif field.data == 'television':
            dump(form.tv_provider)
            self.tv_provider_validator(form, form.tv_provider)
            self.tv_channel_validator(form, form.tv_channel)
        else:
            raise ValidationError(u'This field is required')

# submission form

class SubmissionForm(Form):
    date = DateField(u'Date', default=datetime.date.today, widget=DateInput(), validators=[validators.Required()])
    #time = TimeField(u'Time', validators=[validators.Required()])
    mediatype = SelectField(u'Media type', choices=MEDIATYPES, validators=[MediaTypeValidator()])
    radio_callsign = TextField(u'Radio station')
    tv_provider = SelectField(u'Provider')
    tv_channel = TextField(u'Channel')
    zipcode = TextField(u'Zipcode', validators=[validators.Length(min=5, max=5)])
    candidate = TextField(u'Candidate mentioned')
    sponsor = TextField(u'Sponsor')
    description = TextAreaField(u'Description of ad')
    referrer = HiddenField()