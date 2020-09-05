import io
import os
import tempfile
import flask
from flask import Response
import googleapiclient.discovery
import google_auth
#import google_sheets
from werkzeug.utils import secure_filename
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly
import json
import time
from utils import Filter, response2df, AnalyticsReporting, AnalyticsManagement

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

app = flask.Blueprint('account_structure', __name__)

def build_mgmt_service():
    credentials = google_auth.build_credentials()
    return googleapiclient.discovery.build('analytics', 'v3', credentials=credentials)

def build_reporting_service():
    credentials = google_auth.build_credentials()
    return googleapiclient.discovery.build('analyticsreporting', 'v4', credentials=credentials)

def get_accounts(api_service):
    accounts = api_service.management().accounts().list().execute()
    return accounts

def get_accounts_for_drop(api_service):
    accounts_json = api_service.management().accounts().list().execute()
    account_items = accounts_json.get('items', [])
    account_dict = {account['id']:account['name'] for account in account_items}
    return account_dict

def get_account_users(api_service, account_id):
    response = api_service.management().accountUserLinks().list(accountId=account_id).execute()
    users = response.get('items', [])
    return users

def get_account_filters(api_service, account_id):
    response = api_service.management().filters().list(accountId=account_id).execute()
    filters = response.get('items', [])
    return filters

def get_property(api_service, account_id, property_id):
    prop = api_service.management().webproperties().get(
        accountId=account_id,
        webPropertyId=property_id).execute()
    return prop

def list_properties(api_service, account_id):
    props = api_service.management().webproperties().list(
        accountId=account_id).execute()
    props_items = props.get('items', [])
    prop_list = ['{} - {}'.format(prop['id'], prop['name']) for prop in props_items]
    return prop_list

def get_view_filters(mgmt_api, account_id, property_id, view_id):
    response = mgmt_api.management().profileFilterLinks().list(
      accountId=account_id,
      webPropertyId=property_id,
      profileId=view_id).execute()
    view_filters = response.get('items', [])
    view_filter_list = []
    for filter_obj in view_filters:
        filter_id = filter_obj['id'].split(':')[1]
        rank = filter_obj['rank']
        view_filter_list.append({'id': filter_id, 'rank': rank})
    return view_filter_list

def handle_filters(filter_list):
    filter_dict = []
    for filter in filter_list:
        filter_ins = Filter(f_id=filter['id'], f_name=filter['name'], f_type=filter['type'], f_update=filter['updated'])
        if filter['type'] == "SEARCH_AND_REPLACE":
            filter_ins.details = filter['searchAndReplaceDetails']
        elif filter['type'] == "INCLUDE":
            filter_ins.details = filter["includeDetails"]
        elif filter['type'] == "EXCLUDE":
            filter_ins.details = filter["excludeDetails"]
        elif filter['type'] == "LOWERCASE":
            filter_ins.details = filter["lowercaseDetails"]
        elif filter['type'] == "UPPERCASE":
            filter_ins.details = filter["uppercaseDetails"]
        elif filter['type'] == "ADVANCED":
            filter_ins.details = filter["advancedDetails"]
        else:
            filter_ins.details = {'key': 'value'}
        filter_dict.append(filter_ins)

    return filter_dict

def list_views(api_service, account_id, property_id):
    views_raw = api_service.management().profiles().list(
      accountId=account_id,
      webPropertyId=property_id).execute()
    view_items = views_raw.get('items', [])
    view_list = ['{} - {}'.format(view['id'], view['name']) for view in view_items]
    return view_list

def get_demographics_report(analytics):
    df = analytics.report(
        dimensions=[{'name': 'ga:userGender'}, {'name': 'ga:userAgeBracket'}],
        metrics=[{'expression': 'ga:sessions'}],
        date_range=['30daysAgo', 'today']
        )
    df["ga:sessions"] = df["ga:sessions"].astype('int64')
    df.columns = ['Gender', 'Age Bucket', 'Sessions']
    return df


def create_piechart(df):
    """Create a plotly figure
    Parameters
    ----------
    df : pandas.Dataframe
    Returns
    -------
    fig1, fig2:
        Plotly bar chart
    """
    # Count class occurences
    df_female = df[df['Gender']=='female'].sort_values(by='Age Bucket', ascending=False)
    df_male = df[df['Gender']=='male'].sort_values(by='Age Bucket', ascending=False)

    layout = go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            font=dict(
                family="sans-serif",
                color="white")
                )
            )
    fig_female = go.Figure(data=[go.Pie(labels=df_female['Age Bucket'], values=df_female['Sessions'])], layout=layout)
    fig_male = go.Figure(data=[go.Pie(labels=df_male['Age Bucket'], values=df_male['Sessions'])], layout=layout)
    return fig_female, fig_male

def get_hits_report(analytics):
  df = analytics.report(
        dimensions=[{'name': 'ga:date'}],
        metrics=[{'expression': 'ga:hits'}],
        date_range=['30daysAgo', 'today']
        )
  df["ga:hits"] = df["ga:hits"].astype('int64')
  hits_greater = {}
  hits_greater['hit_count'] = df['ga:hits'].sum()
  hits_greater['text'] = 'Hit limit is NOT reached.' if hits_greater['hit_count'] < 10000000 else 'Hit limit is reached. Consider reducing your hit count!'
  return hits_greater

@app.route('/ga-account-structure', methods=['GET', 'POST'])
def google_audit():

    mgmt_api = build_mgmt_service()
    account_drop = get_accounts_for_drop(mgmt_api)
    
    if flask.request.method == "POST":
        # GA information processing
        req_data = flask.request.form
        account_id = req_data['account'].split(" ")[0]
        property_id = req_data['property'].split(" ")[0]
        view_id = req_data['view'].split(" ")[0]
        analytics = AnalyticsReporting(view_id=view_id)

        # User account eval
        accounts = get_accounts(mgmt_api)
        users = get_account_users(mgmt_api, account_id)
        user_chunks = [users[i:i+3] for i in range(0,len(users),3)]

        # Filter eval
        filters = get_account_filters(mgmt_api, account_id)
        filter_data = handle_filters(filters)
        view_filters = get_view_filters(mgmt_api, account_id, property_id, view_id)
        final_filters = []
        
        for filter_obj in filter_data:
            if filter_obj.id in [f['id'] for f in view_filters]:
                filter_obj.rank = [f['rank'] for f in view_filters if f['id']==filter_obj.id ][0]
                final_filters.append(filter_obj)
        filter_chunks = [final_filters[i:i+3] for i in range(0,len(final_filters),3)]
        
        # Data retention
        data_retention = get_property(mgmt_api, account_id, property_id)
        
        # Demographics
        demographics_df = get_demographics_report(analytics)
        if demographics_df.shape[0] == 0:
            demographics_bool = False
        else:
            demographics_bool = True
        fig_female, fig_male = create_piechart(demographics_df)
        graphs = [fig_female, fig_male]
        graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
        
        # Hit limit
        hits_greater = get_hits_report(analytics)
        for account in accounts['items']:
            if account['id'] == account_id:
                return flask.render_template('account_structure.html', 
                                                user_info=google_auth.get_user_info(),
                                                account_name=account['name'],
                                                users=user_chunks,
                                                filters=filter_chunks,
                                                #demographics=[demographics_df.to_html(classes='table')],
                                                hits_greater = hits_greater,
                                                data_retention=data_retention,
                                                ids=['Female', 'Male'],
                                                graphJSON=graphJSON,
                                                demographics_bool=demographics_bool,
                                                accounts=account_drop)
    # GET request
    return flask.render_template('account_structure.html', user_info=flask.session['user'], accounts=account_drop)


# Dropdown functionality - Account
@app.route('/get-properties/<account_id>')
def get_properties(account_id):
    flask.session['account_id'] = account_id
    mgmt_api = build_mgmt_service()
    prop_list = list_properties(mgmt_api, account_id)                      
    return flask.jsonify(prop_list)

# Dropdown functionality - Property
@app.route('/get-views/<property_id>')
def get_views(property_id):
    account_id = flask.session['account_id']
    mgmt_api = build_mgmt_service()
    view_list = list_views(mgmt_api, account_id, property_id) 
    return flask.jsonify(view_list)

