import io
import tempfile
import flask
import googleapiclient.discovery
from google_auth import build_credentials, get_user_info
from werkzeug.utils import secure_filename
import pandas as pd

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1d3PV4NPgsRfeNVaDgOjTpkJGMl3bMiRSENU9708ajLc'
RANGE_NAME = 'CausalImpact!A15:B'

app = flask.Blueprint('google_sheets', __name__)

def build_sheets():
    credentials = build_credentials()
    return googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)

def get_data():
    g_service = build_sheets()
    gsheet = g_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    return gsheet

def gsheet2df():
    """ Converts Google sheet data to a Pandas Df.
    Note: This script assumes that your data contains a header file on the first row!
    Also note that the Google API returns 'none' from empty cells - in order for the code
    below to work, you'll need to make sure your sheet doesn't contain empty cells,
    or update the code to account for such instances.
    """
    gsheet = get_data()
    header = gsheet.get('values', [])[0]   # Assumes first line is header!
    values = gsheet.get('values', [])[1:]  # Everything else is data.
    if not values:
        print('No data found.')
    else:
        all_data = []
        for col_id, col_name in enumerate(header):
            column_data = []
            for row in values:
                column_data.append(row[col_id])
            ds = pd.Series(data=column_data, name=col_name)
            all_data.append(ds)
        df = pd.concat(all_data, axis=1)
    return df