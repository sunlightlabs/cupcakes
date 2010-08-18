#!/usr/bin/env python
from cupcakes import app, settings

if __name__ == "__main__":
    
    port = 8000 if settings.DEBUG else 80
    host = 'localhost' if not hasattr(settings, 'HOST') else settings.HOST

    app.secret_key = settings.SECRET_KEY or "thisreallyisntasecretkey"
    app.run(host=host, port=port, debug=settings.DEBUG)