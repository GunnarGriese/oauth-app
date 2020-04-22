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

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

app = flask.Blueprint('google_audit', __name__)

def build_service():
    credentials = google_auth.build_credentials()
    return googleapiclient.discovery.build('analytics', 'v3', credentials=credentials)

def get_accounts(api_service):
    accounts = api_service.management().accounts().list().execute()
    return accounts

def get_account_users(api_service, account_id):
    response = api_service.management().accountUserLinks().list(accountId=account_id).execute()
    users = response.get('items', [])
    return users

def get_properties(api_service, account_id, property_id):
    prop = api_service.management().webproperties().get(
        accountId=account_id,
        webPropertyId=property_id).execute()
    return prop

def get_ads_accounts(api_service, account_id, property_id):
    response = api_service.management().webPropertyAdWordsLinks().list(
        accountId=account_id,
        webPropertyId=property_id).execute()
    ads = response.get('items', [])
    return ads

def get_custom_ds(api_service, account_id, property_id):
    response = api_service.management().customDimensions().list(
        accountId=account_id,
        webPropertyId=property_id).execute()
    cds = response.get('items', [])
    return cds

def get_custom_ms(api_service, account_id, property_id):
    response = api_service.management().customMetrics().list(
        accountId=account_id,
        webPropertyId=property_id).execute()
    mds = response.get('items', [])
    return mds

def get_audiences(api_service, account_id, property_id):
    response = api_service.management().remarketingAudience().list(
        accountId=account_id,
        webPropertyId=property_id).execute()
    audiences = response.get('items', [])
    return audiences

def get_view(api_service, account_id, property_id, view_id):
    view = api_service.management().profiles().get(
      accountId=account_id,
      webPropertyId=property_id,
      profileId=view_id).execute()
    return view

def get_view_filters(api_service, account_id, property_id, view_id):
    response = api_service.management().profileFilterLinks().list(
      accountId=account_id,
      webPropertyId=property_id,
      profileId=view_id).execute()
    view_filters = response.get('items', [])
    return view_filters

def get_goals(api_service, account_id, property_id, view_id):
    response = api_service.management().goals().list(
      accountId=account_id,
      webPropertyId=property_id,
      profileId=view_id).execute()
    goals = response.get('items', [])
    return goals

@app.route('/ga-settings', methods=['GET', 'POST'])
def google_audit():
    api_service = build_service()
    req_data = flask.request.form
    print(flask.request.method)
    if flask.request.method == "POST":
        accounts = get_accounts(api_service)
        users = get_account_users(api_service, req_data['account'])
        prop = get_properties(api_service, req_data['account'], req_data['property'])
        ads = get_ads_accounts(api_service, req_data['account'], req_data['property'])
        cds = get_custom_ds(api_service, req_data['account'], req_data['property'])
        cms = get_custom_ms(api_service, req_data['account'], req_data['property'])
        audiences = get_audiences(api_service, req_data['account'], req_data['property'])
        view = get_view(api_service, req_data['account'], req_data['property'], req_data['view'])
        view_filters = get_view_filters(api_service, req_data['account'], req_data['property'], req_data['view'])
        goals = get_goals(api_service, req_data['account'], req_data['property'], req_data['view'])

        for account in accounts['items']:
            if account['id'] == req_data['account']:
                return flask.render_template('ga_audit.html', 
                                                user_info=google_auth.get_user_info(),
                                                account_name=account['name'],
                                                users=users,
                                                property=prop,
                                                ads=ads,
                                                cds=cds,
                                                cms=cms,
                                                audiences=audiences,
                                                view=view,
                                                view_filters=view_filters,
                                                goals=goals)
    
    return flask.render_template('ga_audit.html', user_info=google_auth.get_user_info())