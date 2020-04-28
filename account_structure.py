import io
import os
import tempfile
import flask
from flask import Response
import googleapiclient.discovery
import google_auth
import google_sheets
from werkzeug.utils import secure_filename
import pandas as pd
import requests
from utils import Filter, response2df

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

def handle_filters(filter_list):
    filter_dict = {}
    for idx, filter in enumerate(filter_list):
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
        filter_dict["filter_{}".format(idx)] = filter_ins

    return filter_dict

def get_demographics_report(api_service, VIEW_ID):
  report = api_service.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:sessions'}],
          'dimensions': [{'name': 'ga:userGender'},
                        {'name': 'ga:userAgeBracket'}],
          "pageSize": 100000
        }]
      }
  ).execute()
  df = response2df(report)
  df["ga:sessions"] = df["ga:sessions"].astype('int64')
  df['perc'] = df['ga:sessions'] / df['ga:sessions'].sum()
  df.columns = ['Gender', 'Age Bucket', 'Sessions', 'Session Share']
  return df

def get_hits_report(api_service, VIEW_ID):
  report = api_service.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:hits'}],
          'dimensions': [{'name': 'ga:date'}],
          "pageSize": 100000
        }]
      }
  ).execute()
  df = response2df(report)
  df["ga:hits"] = df["ga:hits"].astype('int64')
  hits_greater = {}
  hits_greater['hit_count'] = df['ga:hits'].sum()
  hits_greater['text'] = 'Hit limit is NOT reached.' if hits_greater['hit_count'] < 10000000 else 'Hit limit is reached. Consider reducing your hit count!'
  return hits_greater

@app.route('/ga-account-structure', methods=['GET', 'POST'])
def google_audit():
    mgmt_api = build_mgmt_service()
    reporting_api = build_reporting_service()
    req_data = flask.request.form
    print(flask.request.method)
    if flask.request.method == "POST":
        accounts = get_accounts(mgmt_api)
        users = get_account_users(mgmt_api, req_data['account'])
        filters = get_account_filters(mgmt_api, req_data['account'])
        filter_data = handle_filters(filters)
        data_retention = get_property(mgmt_api, req_data['account'], req_data['property'])
        demographics_df = get_demographics_report(reporting_api, req_data['view'])
        hits_greater = get_hits_report(reporting_api, req_data['view'])
        for account in accounts['items']:
            if account['id'] == req_data['account']:
                return flask.render_template('account_structure.html', 
                                                user_info=google_auth.get_user_info(),
                                                account_name=account['name'],
                                                users=users,
                                                filters=filter_data,
                                                demographics=[demographics_df.to_html(classes='table')],
                                                hits_greater = hits_greater,
                                                data_retention=data_retention)
    
    return flask.render_template('account_structure.html', user_info=google_auth.get_user_info())