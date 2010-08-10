from cupcakes import app, settings

app.secret_key = settings.SECRET_KEY
applications = {
    '/': app,
}