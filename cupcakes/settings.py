DEBUG = True
SECRET_KEY = None

MONGODB_HOST = None
MONGODB_PORT = None

YAHOO_APPID = ''

PAGE_SIZE = 30

try:
    from local_settings import *
except ImportError:
    pass