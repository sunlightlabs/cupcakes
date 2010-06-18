#!/usr/bin/env python
from cupcakes import app as application, settings

if __name__ == "__main__":

    application.secret_key = settings.SECRET_KEY or "fasijefpaowi3jfpaw8pawih3pw"
    application.run(port=8000, debug=settings.DEBUG)