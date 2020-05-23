# Source: https://www.mattbutton.com/2019/01/05/google-authentication-with-python-and-flask/
import functools
import json
import os
from collections import deque 
import flask

from authlib.integrations.requests_client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery

import google_auth
import google_sheets
import causal_impact
import google_audit
import google_audit_data
import account_structure


app = flask.Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.environ.get("FN_FLASK_SECRET_KEY", default=False)

app.register_blueprint(google_auth.app)
app.register_blueprint(google_sheets.app)
app.register_blueprint(causal_impact.app)
app.register_blueprint(google_audit.app)
app.register_blueprint(google_audit_data.app)
app.register_blueprint(account_structure.app)

@app.route('/')
def index():
    if google_auth.is_logged_in():
        df = google_sheets.gsheet2df()
        #user = google_auth.get_user_info()
        columns = deque(df.columns.values) 
        columns.appendleft('Index') 
        columns = list(columns) 
        df.reset_index(drop=True, inplace=True)
        df.index.name=None
        return flask.render_template('dataframe.html', tables=[df.to_html(classes='table')], titles=columns, user_info=flask.session['user']) #items['files']

    return flask.render_template('index.html')