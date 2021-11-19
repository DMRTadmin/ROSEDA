from google.cloud import storage

def upload_file(gsClient, bucket, gspath, file):
    outBucket = gsClient.bucket(bucket)
    blob = outBucket.blob(gspath)
    blob.upload_from_filename(file)

def download_file(gsClient, bucket, gspath, file):
    outBucket = gsClient.bucket(bucket)
    blob = outBucket.blob(gspath)
    blob.download_to_filename(file)