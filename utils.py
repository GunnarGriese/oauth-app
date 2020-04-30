import pandas as pd
import google_auth
import googleapiclient.discovery

class Filter:
    def __init__(self, f_id,f_name, f_type, f_update, f_details=None):
        self.id = f_id
        self.name = f_name
        self.type = f_type
        self.update = f_update
        self.details = f_details

def response2df(report):
    """Parses and prints the Analytics Reporting API V4 response"""
    report = report.get('reports', [])[0]
    #Initialize empty data container for the two date ranges (if there are two that is)
    data_csv = []

    #Initialize header rows
    header_row = []

    #Get column headers, metric headers, and dimension headers.
    column_header = report.get('columnHeader', {})
    
    metric_headers = column_header.get('metricHeader', {}).get('metricHeaderEntries', [])
    
    dimension_headers = column_header.get('dimensions', [])

    #Combine all of those headers into the header_row, which is in a list format
    for dheader in dimension_headers:
        header_row.append(dheader)
    for mheader in metric_headers:
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


class AnalyticsReporting:
    API_VER = 'v4'
    API_NAME = 'analyticsreporting'

    def __init__(self, view_id):
        credentials = google_auth.build_credentials()
        self.analytics = googleapiclient.discovery.build(self.API_NAME, self.API_VER, credentials=credentials)
        self.view_id = view_id

    def _get_report_data(self, dimensions, metrics, date_range):
        reportRequests = [
            {
                "viewId": self.view_id,
                "dateRanges": [{
                    "startDate": date_range[0],
                    "endDate": date_range[1],
                }],
                'metrics': metrics,
                'dimensions': dimensions
            }]
        return self.analytics.reports().batchGet(
            body={
                'reportRequests': reportRequests
            }
        ).execute()

    def report(self, dimensions, metrics, date_range):
        """Parses and and returns a pd.DataFrame of the Analytics Reporting API V4 response"""
        report = self._get_report_data(dimensions=dimensions, metrics=metrics, date_range=date_range)
        report = report.get('reports', [])[0]
        #Initialize empty data container for the two date ranges (if there are two that is)
        data = []
        header_row = []

        #Get column headers, metric headers, and dimension headers.
        column_header = report.get('columnHeader', {})
        metric_headers = column_header.get('metricHeader', {}).get('metricHeaderEntries', [])
        dimension_headers = column_header.get('dimensions', [])

        #Combine all of those headers into the header_row, which is in a list format
        for dheader in dimension_headers:
            header_row.append(dheader)
        for mheader in metric_headers:
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
            
            data.append(row_temp)
    
        #Putting those list formats into pandas dataframe, and append them into the final result
        result_df = pd.DataFrame(data, columns=header_row)
        return result_df

class AnalyticsManagement:
    API_VER = 'v3'
    API_NAME = 'analytics'

    def __init__(self, account_id, property_id, view_id):
        credentials = google_auth.build_credentials()
        self.analytics = googleapiclient.discovery.build(self.API_NAME, self.API_VER, credentials=credentials)
        self.account_id = account_id
        self.property_id = property_id
        self.view_id = view_id

    def list_accounts(self):
        """returns a list of management.accountSummaries Resource"""
        accounts = self.analytics.management().accounts().list().execute()
        return accounts.get('items', [])

    def list_account_users(self):
        users = self.analytics.management().accountUserLinks().list(accountId=self.account_id).execute()
        return users.get('items', [])

    def list_account_filters(self):
        filters = self.analytics.management().filters().list(accountId=self.account_id).execute() 
        return filters.get('items', [])

    def get_property(self):
        """per default pre-defined property is returned"""
        prop = self.analytics.management().webproperties().get(
            accountId=self.account_id,
            webPropertyId=self.property_id).execute()
        return prop

    def list_view_filters(self):
        """per default view filters for pre-defined property and view are returned"""
        view_filters = self.analytics.management().profileFilterLinks().list(
            accountId=self.account_id,
            webPropertyId=self.property_id,
            profileId=self.view_id).execute()
        return view_filters.get('items', [])

    def handle_filters(self):
        account_filters = self.list_account_filters()
        filter_dict = {}
        for idx, filter in enumerate(account_filters):
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