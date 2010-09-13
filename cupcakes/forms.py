from cupcakes import settings
from cupcakes.geo import YahooGeocoder
from postmark import PMMail
from wtforms import Form, validators, ValidationError
from wtforms.fields import DateField, HiddenField, SelectField, TextField, TextAreaField
from wtforms.widgets import TextInput
import datetime

TIMES = []
current = datetime.datetime(1981, 8, 6, 0, 0, 0)
xv_minutes = datetime.timedelta(0, 0, 0, 0, 15)
for i in range(0, 24 * 4):
    TIMES.append((current.strftime("%H:%M"), current.strftime("%I:%M %p")))
    current += xv_minutes

DAYS = [(str(x), str(x)) for x in range(1, 32)]

MONTHS = (
    ("1","January"),
    ("2","February"),
    ("3","March"),
    ("4","April"),
    ("5","May"),
    ("6","June"),
    ("7","July"),
    ("8","August"),
    ("9","September"),
    ("10","October"),
    ("11","November"),
    ("12","December"),
)

YEARS = (
    ("2010", "2010"),
)

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

FOR_AGAINST = (
    ('for', 'in favor of candidate'),
    ('against', 'against candidate'),
    ('neither', 'neither'),
)
MEDIATYPES = [(c,c) for c in ('','radio','television')]

geo = YahooGeocoder(settings.YAHOO_APPID)

# date field and widgets

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

class DayValidator(object):
    def __call__(self, form, field):
        day = int(field.data)
        month = int(form.dt_month.data)
        year = int(form.dt_year.data)
        try:
            datetime.date(year, month, day)
        except ValueError:
            raise ValidationError(u'%s has less than %s days' % (MONTHS[month - 1][1], day))

# submission form

def this_day():
    return datetime.datetime.today().day

def this_month():
    return datetime.datetime.today().month

class SubmissionForm(Form):
    dt_month = SelectField(u'Month', default=this_month, choices=MONTHS, validators=[validators.Required()])
    dt_day = SelectField(u'Date Aired', default=this_day, choices=DAYS, validators=[DayValidator()])
    dt_year = HiddenField(u'Year', default='2010', validators=[validators.Required()])
    dt_time = SelectField(u'Time', default='12:00', choices=TIMES, validators=[validators.Required()])
    # date = DateField(u'Date', default=datetime.date.today, widget=DateInput(), validators=[validators.Required()])
    # time = SelectField(u'Time', default='12:00', choices=TIMES, validators=[validators.Required()])
    mediatype = SelectField(u'Media type', choices=MEDIATYPES, validators=[MediaTypeValidator()])
    for_against = SelectField(u'Type of ad', choices=FOR_AGAINST)
    radio_callsign = TextField(u'Radio station')
    tv_provider = SelectField(u'Provider', choices=PROVIDERS)
    tv_channel = SelectField(u'Channel', choices=[('other', 'Other')])
    tv_channel_other = TextField(u'Channel other')
    internet_link = TextField(u'Site URL')
    zipcode = TextField(u'Zipcode', validators=[validators.Length(min=5, max=5)])
    candidate = TextField(u'Candidate mentioned')
    issue = TextField(u'Issue')
    sponsor = TextField(u'Paid for by')
    description = TextAreaField(u'Description of ad')
    referrer = HiddenField()

class FilterForm(Form):
    zipcode = TextField(u'Zipcode', validators=[validators.Length(min=5, max=5)])
    state = SelectField(u'State', choices=US_STATES)
    candidate = TextField(u'Candidate')
    sponsor = TextField(u'Sponsor')

class ContactForm(Form):
    name = TextField(u'Name', validators=[validators.Required()])
    email = TextField(u'Email Address', validators=[validators.Required()])
    comments = TextAreaField(u'Comments', validators=[validators.Required()])
    
    def send(self):
        body = """%s <%s>\n\n%s""" % (self.name.data, self.email.data, self.comments.data)
        PMMail(
            api_key=settings.POSTMARK_KEY,
            to='sunlightcam@sunlightfoundation.com',
            sender='sunlightcam@sunlightfoundation.com',
            subject='[SunlightCAM] contact form submission',
            text_body=body,
        ).send()