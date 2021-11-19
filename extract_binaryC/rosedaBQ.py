from google.cloud import bigquery
from google.api_core.exceptions import NotFound
import os
import io
import pandas as pd
from google.oauth2 import service_account
import re, traceback, sys
import datetime

#Clean Functions
#----------------------------------------------------------------------------
def dict2BQ_initialize(data_dict, bqClient, datasetName, tableName, clean=True):
    dataset  = bqClient.dataset(datasetName) 
    try:
        #Assuming Table Exists
        tableOut = bqClient.get_table(dataset.table(tableName))
        print(tableName+' table found.')
    except NotFound: #(Not sure what type of error google api not found is)
        #Catched Error: Table does not exist
        tableOut = dataset.table(tableName)
        print('Table did not exist; created table '+tableName+'.')
        # Clean the dictionary
        if clean:
            dictIN = cleanDict(data_dict)
        else:
            dictIN = data_dict
        # Clean the dictionary
        if clean:
            dictIN = cleanDict(data_dict)
        else:
            dictIN = data_dict
        # Create a Schema
        jobConfig = bigquery.LoadJobConfig()
        jobConfig.autodetect = True
            
        # Upload to BQ
        #Convert to a newline delimited JSON
        jobConfig.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        if type(dictIN) == dict:
            df = pd.DataFrame.from_dict([dictIN]) #Dataframe
        elif type(dictIN) == list:
            df = pd.DataFrame.from_dict(dictIN) #Dataframe
        dfJSON = df.to_json(orient = 'records', lines = True) #JSON File
        strioData = io.StringIO(dfJSON) #String Input
        
        #Performing Upload Job to BQ
        job = bqClient.load_table_from_file(strioData, tableOut, job_config=jobConfig)
        try:
            job.result()
        except:
            print(str(job.errors))
            traceback.print_exc(file=sys.stdout)
            return job
        return job

def dict2BQ(data_dict, bqClient, datasetName, tableName, BQauto=False, clean=True):
    # Basic rules
    # Highest level structure must be dictionary
    # Everything in list needs to have the same structure
    # No lists of lists
    # Structure must match what is already in the database
    dataset  = bqClient.dataset(datasetName)
    tableOut = dataset.table(tableName)
    if clean:
        dictIN = cleanDict(data_dict)
    else:
        dictIN = data_dict
    # Create a Schema
    jobConfig = bigquery.LoadJobConfig()
    if BQauto:
        jobConfig.autodetect = True
        
    # Upload to BQ
    #Convert to a newline delimited JSON
    jobConfig.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    if type(dictIN) == dict:
        df = pd.DataFrame.from_dict([dictIN]) #Dataframe
    elif type(dictIN) == list:
        df = pd.DataFrame.from_dict(dictIN) #Dataframe
    dfJSON = df.to_json(orient = 'records', lines = True) #JSON File
    strioData = io.StringIO(dfJSON) #String Input
    
    #Performing Upload Job to BQ
    job = bqClient.load_table_from_file(strioData, tableOut, job_config=jobConfig)
    try:
        job.result()
    except:
        print(str(job.errors))
        traceback.print_exc(file=sys.stdout)
        return job
    return job


def cleanStr(string):
    return re.sub(r'[\W]+', '', str(string)) #Remove goop from strings to see if problem  
def cleanDict(dictIn):
    if type(dictIn) == list:
        rlist = []
        for record in dictIn:
            rlist.append(cleanDict(record))
        return rlist
    dictOut = {}
    for k in list(dictIn.keys()):
        if dictIn[k] == {}:
            # dictOut[cleanStr(k)] = '{}'
            pass
        elif dictIn[k] == []:
            # dictOut[cleanStr(k)] = '[]'
            pass
        elif type(dictIn[k]) is dict:
            dictOut[cleanStr(k)] = cleanDict(dictIn[k])
        elif type(dictIn[k]) is int:
            dictOut[cleanStr(k)] = float(dictIn[k])
        elif type(dictIn[k]) is list:
            dictOut[cleanStr(k)] = []
            for i in range(len(dictIn[k])):
                if dictIn[k][i] == None:
                    dictOut[cleanStr(k)].append('')
                elif type(dictIn[k][i]) is dict:
                    dictOut[cleanStr(k)].append(cleanDict(dictIn[k][i]))
                elif type(dictIn[k][i]) is int:
                    dictOut[cleanStr(k)].append(float(dictIn[k][i]))
                else:
                    dictOut[cleanStr(k)].append(str(dictIn[k][i]))
        else:    
            dictOut[cleanStr(k)] = dictIn[k]
    return dictOut  

def getData(query, bqClient):
    # getting relevant information from query
    qparts = query.split("`")[1].split(".")
    projectName = qparts[0]
    datasetName = qparts[1]
    #Accessing Google Cloud Big Query
    dataset  = bqClient.dataset(datasetName)
    jobConfig = bigquery.QueryJobConfig(use_query_cache=False)
    queryJob = bqClient.query(query, job_config=jobConfig)
    rows_iter = queryJob.result()
    rows = [row for row in rows_iter]
    data_list = []
    if len(rows)>0:
        keys = [key for key in rows[0].keys()]
        for row in rows:
            row_data={}
            for key in keys:
                row_data[key]=row[key]
            data_list.append(row_data)
    return data_list

if __name__ == "__main__":
    from copy import deepcopy
    kfile = "/home/james_hardin_11/Desktop/jhardin-repos-1sud/Keys/rxms-roseda-5c87e722e5b1.json"
    project_name = 'rxms-roseda'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = kfile
    credentials = service_account.Credentials.from_service_account_file(
        kfile, scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    BQ_client = bigquery.Client(credentials=credentials, project=credentials.project_id,)
    
    data = {"image_file":"test", "coordinates":[1.1,2.1,3.1], "Test_name":"test"}
    batch = []
    for n in range(10):
        neline = deepcopy(data)
        neline["coordinates"] = [n, n+1, n+2]
        batch.append(neline)
    test = dict2BQ_initialize(data, BQ_client, "joh_experimental", "test_table3")
    test = dict2BQ(batch, BQ_client, "joh_experimental", "test_table3")