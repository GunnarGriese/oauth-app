# Code walk-through: https://requests-oauthlib.readthedocs.io/en/latest/examples/real_world_example_with_refresh.html
import functools
import os
import flask
from authlib.integrations.requests_client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery
from utils import AnalyticsManagement
import json

# OAuth endpoints given in the Google API documentation
ACCESS_TOKEN_URI = 'https://www.googleapis.com/oauth2/v4/token'
REFRESH_URI = ACCESS_TOKEN_URI # True for Google but not all oauth providers.
AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent'
BASE_URI = os.environ.get("FN_BASE_URI", default=False)

AUTHORIZATION_SCOPE ='openid email profile https://www.googleapis.com/auth/analytics.readonly https://www.googleapis.com/auth/spreadsheets.readonly https://www.googleapis.com/auth/analytics.readonly https://www.googleapis.com/auth/analytics.manage.users.readonly'

# This information is obtained upon registration of a new Google OAuth
# application at console.developers.google.com
AUTH_REDIRECT_URI = os.environ.get("FN_AUTH_REDIRECT_URI", default=False)
CLIENT_ID = os.environ.get("FN_CLIENT_ID", default=False)
CLIENT_SECRET = os.environ.get("FN_CLIENT_SECRET", default=False)

AUTH_TOKEN_KEY = 'auth_token'
AUTH_STATE_KEY = 'auth_state'

app = flask.Blueprint('google_auth', __name__)

def is_logged_in():
    return True if AUTH_TOKEN_KEY in flask.session else False

def build_credentials():
    if not is_logged_in():
        raise Exception('User must be logged in')

    oauth2_tokens = flask.session[AUTH_TOKEN_KEY]
    
    return google.oauth2.credentials.Credentials(
                oauth2_tokens['access_token'],
                refresh_token=oauth2_tokens['refresh_token'],
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                token_uri=ACCESS_TOKEN_URI,
                #scopes=SCOPES
                )

def get_user_info():
    # Adjust to match: https://github.com/googleapis/google-api-python-client 
    credentials = build_credentials()

    oauth2_client = googleapiclient.discovery.build(
                        'oauth2', 'v2',
                        credentials=credentials)

    flask.session['user'] = oauth2_client.userinfo().get().execute()

    return flask.session['user']

def no_cache(view):
    @functools.wraps(view)
    def no_cache_impl(*args, **kwargs):
        response = flask.make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return functools.update_wrapper(no_cache_impl, view)

@app.route('/google/login')
@no_cache
def login():
    """Step 1: User Authorization.

    Redirect the user/resource owner to Google
    using an URL with a few key OAuth parameters.
    """
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=AUTHORIZATION_SCOPE,
                            redirect_uri=AUTH_REDIRECT_URI)
    
    # Build redirect URL for user login
    uri, state = session.create_authorization_url(AUTHORIZATION_URL)
    
    # Uncomment to get insights into OAuth process.
    #print("URI: {}".format(json.dumps(uri)))
    #print("State: {}".format(json.dumps(state)))

    # State is used to prevent CSRF, keep this for later.
    flask.session[AUTH_STATE_KEY] = state
    flask.session.permanent = False

    return flask.redirect(uri, code=302)

# Step 2: User authorization, this happens on the provider.

@app.route('/google/auth')
@no_cache
def google_auth_redirect():
    """ Step 3: Retrieving an access token.

    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """

    req_state = flask.request.args.get('state', default=None, type=None)
    print("Request Args: {}".format(json.dumps(flask.request.args)))
    if req_state != flask.session[AUTH_STATE_KEY]:
        response = flask.make_response('Invalid state parameter', 401)
        return response
    
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=AUTHORIZATION_SCOPE,
                            state=flask.session[AUTH_STATE_KEY],
                            redirect_uri=AUTH_REDIRECT_URI)

    oauth2_tokens = session.fetch_access_token(
                        ACCESS_TOKEN_URI,            
                        authorization_response=flask.request.url)
    
    # We use the session as a simple DB for this app.
    flask.session[AUTH_TOKEN_KEY] = oauth2_tokens

    # Uncomment to get insights into authentication process.
    #step3_logging(flask.request.url, oauth2_tokens)

    return flask.redirect(BASE_URI, code=302)

@app.route('/google/logout')
@no_cache
def logout():
    ''' Pop tokens from client on logout. '''
    flask.session.pop(AUTH_TOKEN_KEY, None)
    flask.session.pop(AUTH_STATE_KEY, None)

    return flask.redirect(BASE_URI, code=302)

def step3_logging(request_url, tokens):
    print("Auth Response URL: {}".format(json.dumps(request_url)))
    print("Access token: {}".format(tokens))