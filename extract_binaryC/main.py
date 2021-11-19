from google.cloud import storage, bigquery, pubsub_v1
from os import path
import sys, json, time, uuid, traceback
from tempfile import gettempdir
import extract_binaryC
import rosedaGS, rosedaBQ

def helloPubSub(event, context):
    # Try/except loop to ensure traceback in cloud function
    try:
        safe_function(event, context)
    except:
        traceback.print_exc(file=sys.stdout)

def safe_function(event, context, bqClient=None, gsClient=None, psClient=None):
    print('Starting')
    event_data = json.loads(event["attributes"]["message"])
    print(str(event_data))
    # Points it to a list of images
    file = event_data["file"]
    
    projectName = "rxms-roseda"
    bucketName = "rxms-roseda-archive"
    datasetName = "joh_experimental"
    tableName = "extract_binaryC"
    # Setting up clients this enables the passing of credentialed clients for
    # local development
    if gsClient == None:
        gsClient = storage.Client(project = str(projectName))
    if bqClient == None:
        bqClient = bigquery.Client(project = str(projectName))    
    if psClient == None:
        psClient =  pubsub_v1.PublisherClient()
    
    # Download image file
    troot = gettempdir()
    imageName = file.split(r"/")[-1].split(".")[0]
    local_source_path = path.join(troot, imageName)
    rosedaGS.download_file(gsClient, bucketName, file, local_source_path)
    # Process file
    cfiles = extract_binaryC.extract_cs(local_source_path, local_source_path, "pattern.png")
    cdata = []
    analysis_uuid = str(uuid.uuid4())
    for n, cfile in enumerate(cfiles):
        report = {}
        report["analysis_uuid"] = analysis_uuid
        report["source_file"] = file
        cfile_name = path.split(cfile)[-1] 
        cfile_path = path.join("extract_binaryC", analysis_uuid, cfile_name)
        rosedaGS.upload_file(gsClient, bucketName, cfile_path, cfile)
        report["c_image"] = cfile_path
        report["order"] = n
        cdata.append(report)
        
    # Construct sample structure
    report = {}
    report["analysis_uuid"] = "test"
    report["source_file"] = "test"
    report["c_image"] = "test"
    report["order"] = 1.0
    # Initialize BigQuery 
    test = rosedaBQ.dict2BQ_initialize(report, bqClient, datasetName, tableName)
    # Upload to BQ
    jobResult = rosedaBQ.dict2BQ(cdata, bqClient, datasetName, tableName)
    # Note image in image table
    for cfile in cdata:
        topic = "rxms-roseda-topic-images"
        message = {}
        message["analysis_name"] = "rxms-roseda-extract_binaryC"
        message["uuid"] = analysis_uuid
        message["file"] = cfile["c_image"]
        sendPubSub(psClient, projectName, topic, message)
        # Resize the C's
        topic = "rxms-roseda-topic-resize_binaryC"
        message = {}
        message["file"] = cfile["c_image"]
        sendPubSub(psClient, projectName, topic, message)


#----------------------------------------------------------------------------

def sendPubSub(psClient, project, topic, message_dict):
    topic_name = psClient.topic_path(project, topic)
    #Convert the message_dict to a string and reformat for decoding
    message = json.dumps(message_dict)
    #Carry the information in an attribute
    psClient.publish(topic_name, b"Nothing here", message=message)


if __name__ == "__main__":
    print("Testing")
    # Set up local credentialed clients
    import os
    from google.oauth2 import service_account
    kfile = "/home/james_hardin_11/Desktop/jhardin-repos-1sud/Keys/rxms-roseda-eb7721e580d1.json"
    project_name = 'rxms-roseda'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = kfile
    credentials = service_account.Credentials.from_service_account_file(
        kfile, scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    bqClient = bigquery.Client(credentials=credentials, project=credentials.project_id,)
    gsClient = storage.Client(credentials=credentials, project=credentials.project_id,)
    psClient = pubsub_v1.PublisherClient(credentials=credentials,)
    # Set up mock event and context
    event = {"attributes":{}}
    context = {}
    message = {"file":""}
    message["file"] = "1631723023_97e5a413/fromRWeeks/fromPrinter/100P_SESY_50PSI_02-09-2020-S1UPLOAD_ME/Payload/Data/100P_SESY_50PSI_02-09-2020-S1.png"
    # Setting some other variables
    projectName = "rxms-roseda"
    bucketName = "rxms-roseda-archive"
    datasetName = "joh_experimental"
    tableName = "extract_binaryC" 
    
    #Exploring
    
    # Simulated cfunction call
    # Uncomment the next two lines to make this work
    event["attributes"]["message"] = json.dumps(message)
    t0 = time.time()
    thing = safe_function(event, context, bqClient=bqClient, gsClient=gsClient, psClient=psClient)
    dt = round(time.time() - t0)
    print (f"Took {dt} seconds")

