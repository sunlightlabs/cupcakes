#!/usr/bin/env python
from cupcakes import app, settings

if __name__ == "__main__":
    
    port = 8000 if settings.DEBUG else 80

    app.secret_key = settings.SECRET_KEY or "thisreallyisntasecretkey"
    app.run(port=port, debug=settings.DEBUG)