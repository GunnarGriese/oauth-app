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
from urllib import parse

app = flask.Blueprint('google_audit_data', __name__)
VIEW_ID = '206310085'

def build_service():
    credentials = google_auth.build_credentials()
    return googleapiclient.discovery.build('analyticsreporting', 'v4', credentials=credentials)

# https://docs.google.com/spreadsheets/d/1bCL3eXcATDGloD-9pFodBMg-eBUuakMQdaZIpuRv7iE/edit#gid=988872659

def get_query_params(api_service, VIEW_ID):
    """Queries the Analytics Reporting API V4.

    Args:
        analytics: An authorized Analytics Reporting API V4 service object.
    Returns:
        The Analytics Reporting API V4 response.
    """
    report = api_service.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:pageviews'}],
          'dimensions': [{'name': 'ga:pagePath'}],
          "pageSize": 100000
        }]
      }).execute()
    df = response2df(report) # To Do: work with lists rather than dfs
    query_df = df[df['ga:pagePath'].str.contains('?', regex=False)==True] # To Do: Directly filter for pages w/ params in api request
    query_params = []
    for url in query_df['ga:pagePath']:
        key_list = dict(parse.parse_qs(parse.urlsplit(url).query)).keys()
        for key in key_list:
            query_params.append(key)
    query_params = list(set(query_params))
    pii_df = df[df['ga:pagePath'].str.contains('@', regex=False)==True]
    pii_urls = []
    for url in pii_df['ga:pagePath']:
        pii_urls.append(url)
    return query_params, pii_urls

def get_traffic_report(api_service, VIEW_ID):

  report = api_service.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:sessions'}],
          'dimensions': [{'name': 'ga:channelGrouping'}],
          "pageSize": 100000
        }]
      }
  ).execute()

  df = response2df(report)
  df["ga:sessions"] = df["ga:sessions"].astype('int64')
  df['perc'] = df['ga:sessions'] / df['ga:sessions'].sum()
  direct_share = df[df['ga:channelGrouping']== "Direct"]['perc'].values * 100
  other_share = df[df['ga:channelGrouping']== "(Other)"]['perc'].values * 100
  #direct = True if direct_share > 15 else False
  return round(direct_share[0], 2), round(other_share[0], 2)

def get_lp_report(api_service, VIEW_ID):

  report = api_service.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:sessions'},
                      {'expression': 'ga:bounceRate'}],
          'dimensions': [{'name': 'ga:landingPagePath'}],
          "pageSize": 100000
        }]
      }
  ).execute()
  df = response2df(report)
  df["ga:sessions"] = df["ga:sessions"].astype('int64')
  df["ga:bounceRate"] = df["ga:bounceRate"].astype('float64')
  df['perc'] = df['ga:sessions'] / df['ga:sessions'].sum()
  df = df[(df['perc']>0.03) & (df['ga:bounceRate']>=20)] # adjust thresholds
  df.columns = ['Landing Page', 'Sessions', 'Bounce Rate', 'Session Share']
  return df

def response2df(report):
    """Parses and prints the Analytics Reporting API V4 response"""
    report = report.get('reports', [])[0]
    #Initialize empty data container for the two date ranges (if there are two that is)
    data_csv = []

    #Initialize header rows
    header_row = []

    #Get column headers, metric headers, and dimension headers.
    columnHeader = report.get('columnHeader', {})
    
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
    
    dimensionHeaders = columnHeader.get('dimensions', [])

    #Combine all of those headers into the header_row, which is in a list format
    for dheader in dimensionHeaders:
        header_row.append(dheader)
    for mheader in metricHeaders:
        header_row.append(mheader['name'])

    #Get data from each of the rows, and append them into a list
    rows = report.get('data', {}).get('rows', [])
    
    for row in rows:
        row_temp = []
        dimensions = row.get('dimensions', [])
        metrics = row.get('metrics', [])
        
        for d in dimensions:
            row_temp.append(d)
            
        for m in metrics[0]['values']:
            row_temp.append(m)
            
        data_csv.append(row_temp)
    
    #Putting those list formats into pandas dataframe, and append them into the final result
    result_df = pd.DataFrame(data_csv, columns=header_row)

    return result_df

@app.route('/ga-data', methods=['GET', 'POST'])
def ga_data():
    req_data = flask.request.form
    if (flask.request.method == "POST") or (flask.request.method == "GET"):
        api_service = build_service()
        query_params, pii_urls = get_query_params(api_service, VIEW_ID) 
        direct_share, other_share = get_traffic_report(api_service, VIEW_ID)
        bounce = get_lp_report(api_service, VIEW_ID)
        return flask.render_template('ga_data.html', 
                                    user_info=google_auth.get_user_info(),
                                    query_params=query_params,
                                    direct_share=direct_share,
                                    other_share=other_share,
                                    pii_urls=pii_urls,
                                    bounce=[bounce.to_html(classes='table')],)
    
    return flask.render_template('ga_data.html', user_info=google_auth.get_user_info())