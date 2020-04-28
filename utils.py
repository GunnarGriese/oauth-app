import pandas as pd

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