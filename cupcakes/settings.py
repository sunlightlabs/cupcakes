DEBUG = True
SECRET_KEY = None

MONGODB_HOST = None
MONGODB_PORT = None

YAHOO_APPID = ''

PAGE_SIZE = 3

try:
    from local_settings import *
except ImportError:
    pass