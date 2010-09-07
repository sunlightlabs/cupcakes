from cupcakes import settings
from cupcakes.geo import YahooGeocoder
from wtforms import Form, validators, ValidationError
from wtforms.fields import DateField, HiddenField, SelectField, TextField, TextAreaField
from wtforms.widgets import TextInput
import datetime

US_STATES = (
    ("", ""),
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("DC", "Dist of Columbia"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
)

PROVIDERS = [(s, s) for s in (
    "",
    "AT&T Digital TV",
    "Bresnan",
    "Brighthouse Networks",
    "CableOne",
    "Cablevision Systems",
    "Charter Communications",
    "Comcast",
    "Cox Communications",
    "DirecTV",
    "Dish Network",
    "Insight",
    "Mediacom",
    "RCN",
    "Suddenlink",
    "Time Warner Cable",
    "Verizon FIOS",
    "WideOpenWest",
    "---",
    "other cable",
    "other satellite",
    "Broadcast (antenna)",
    "Internet (Hulu, YouTube, etc.)",
)]

TIMES = []
current = datetime.datetime(1981, 8, 6, 0, 0, 0)
xv_minutes = datetime.timedelta(0, 0, 0, 0, 15)
for i in range(0, 24 * 4):
    TIMES.append((current.strftime("%H:%M"), current.strftime("%I:%M %p")))
    current += xv_minutes

FOR_AGAINST = (
    ('for', 'in favor of candidate'),
    ('against', 'against candidate'),
    ('neither', 'neither'),
)
MEDIATYPES = [(c,c) for c in ('','radio','television')]

geo = YahooGeocoder(settings.YAHOO_APPID)

# date widget

class DateInput(TextInput):    
    def __call__(self, field, **kwargs):
        html = super(DateInput, self).__call__(field, **kwargs).replace('type="text"', 'type="date"')
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
            self.tv_provider_validator(form, form.tv_provider)
            self.tv_channel_validator(form, form.tv_channel)
        else:
            raise ValidationError(u'This field is required')

# submission form

class SubmissionForm(Form):
    date = DateField(u'Date', default=datetime.date.today, widget=DateInput(), validators=[validators.Required()])
    time = SelectField(u'Time', default='12:00', choices=TIMES, validators=[validators.Required()])
    mediatype = SelectField(u'Media type', choices=MEDIATYPES, validators=[MediaTypeValidator()])
    for_against = SelectField(u'Type of ad', choices=FOR_AGAINST)
    radio_callsign = TextField(u'Radio station')
    tv_provider = SelectField(u'Provider', choices=PROVIDERS)
    tv_channel = SelectField(u'Channel', choices=[('other', 'Other')])
    tv_channel_other = TextField(u'Channel other')
    internet_link = TextField(u'Site URL')
    zipcode = TextField(u'Zipcode', validators=[validators.Length(min=5, max=5)])
    candidate = TextField(u'Candidate mentioned')
    sponsor = TextField(u'Paid for by')
    description = TextAreaField(u'Description of ad')
    referrer = HiddenField()

class FilterForm(Form):
    zipcode = TextField(u'Zipcode', validators=[validators.Length(min=5, max=5)])
    state = SelectField(u'State', choices=US_STATES)
    candidate = TextField(u'Candidate')
    sponsor = TextField(u'Sponsor')