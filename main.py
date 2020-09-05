import functools
import json
import os
import flask

from authlib.integrations.requests_client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery

import google_auth
import google_audit
import google_audit_data
import account_structure


app = flask.Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.environ.get("FN_FLASK_SECRET_KEY", default=False)

app.register_blueprint(google_auth.app)
app.register_blueprint(google_audit.app)
app.register_blueprint(google_audit_data.app)
app.register_blueprint(account_structure.app)

@app.route('/')
def index():
    if google_auth.is_logged_in():
        user = google_auth.get_user_info()
        return flask.render_template('frontpage.html',user_info=user)

    return flask.render_template('index.html')