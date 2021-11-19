from google.cloud import storage, bigquery, pubsub_v1
from os import path
import sys, json, time, uuid, traceback
from tempfile import gettempdir
import resize_binaryC
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
    # binary C file to be processed 
    file = event_data["file"]
    
    projectName = "rxms-roseda"
    bucketName = "rxms-roseda-archive"
    datasetName = "joh_experimental"
    tableName = "resize_binaryC"
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
    local_original_path = path.join(troot, "original.png")
    local_flip_path = path.join(troot, "flip.png")
    local_resized_path = path.join(troot, "resized.png")
    rosedaGS.download_file(gsClient, bucketName, file, local_original_path)
    # Process file
    m,n = 300,300
    top_min = 75
    bottom_max = 225
    resize_binaryC.flip_c(local_original_path, local_flip_path, m, n)
    resize_binaryC.resize_c(local_flip_path, local_resized_path, top_min, bottom_max)

    analysis_uuid = str(uuid.uuid4())

    report = {}
    report["analysis_uuid"] = analysis_uuid
    report["source_file"] = file 
    gs_path = path.join("extract_binaryC", analysis_uuid, "resized.png")
    rosedaGS.upload_file(gsClient, bucketName, gs_path, local_resized_path)
    report["resized_image"] = gs_path
    report["m"] = m
    report["n"] = n
    report["top_min"] = top_min
    report["bottom_max"] = bottom_max
        
    # Construct sample structure
    t_report = {}
    t_report["analysis_uuid"] = "test"
    t_report["source_file"] = "test"
    t_report["resized_image"] = "test"
    t_report["m"] = 1.2
    t_report["n"] = 1.2
    t_report["top_min"] = 1.2
    t_report["bottom_max"] = 1.2
    # Initialize BigQuery 
    test = rosedaBQ.dict2BQ_initialize(t_report, bqClient, datasetName, tableName)
    # Upload to BQ
    jobResult = rosedaBQ.dict2BQ(report, bqClient, datasetName, tableName)
    # Note image in image table
    topic = "rxms-roseda-topic-images"
    message = {}
    message["analysis_name"] = "rxms-roseda-resize_binaryC"
    message["uuid"] = analysis_uuid
    message["file"] = gs_path
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
    message["file"] = "extract_binaryC/540cad90-3d67-49ac-b873-5b73685df488/HDS2_sample10_y7.2894mm_x10.0972mm_C9.png"
    # Setting some other variables
    projectName = "rxms-roseda"
    bucketName = "rxms-roseda-archive"
    datasetName = "joh_experimental"
    tableName = "resize_binaryC" 
    
    #Exploring
    
    # Simulated cfunction call
    # Uncomment the next two lines to make this work
    event["attributes"]["message"] = json.dumps(message)
    t0 = time.time()
    thing = safe_function(event, context, bqClient=bqClient, gsClient=gsClient, psClient=psClient)
    dt = round(time.time() - t0)
    print (f"Took {dt} seconds")

