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


app = flask.Flask(__name__)
app.secret_key = os.environ.get("FN_FLASK_SECRET_KEY", default=False)

app.register_blueprint(google_auth.app)
app.register_blueprint(google_sheets.app)
app.register_blueprint(causal_impact.app)

@app.route('/')
def index():
    if google_auth.is_logged_in():
        df = google_sheets.gsheet2df()
        #columns = df.columns.values
        #columns[:0] = ['Index']
        columns = deque(df.columns.values) 
        columns.appendleft('Index') 
        columns = list(columns) 
        print(columns)
        df.reset_index(drop=True, inplace=True)
        df.index.name=None
        for i in google_auth.get_user_info():
            print(i)
        return flask.render_template('dataframe.html', tables=[df.to_html(classes='table')], titles=columns, user_info=google_auth.get_user_info()) #items['files']

    return flask.render_template('index.html')

#@app.route('/causal-impact')
#def causal_impact():
#    if google_auth.is_logged_in():
#        df = google_sheets.gsheet2df()