import os
import json
from dotenv import load_dotenv          # lets us load the keys from the .env file so they're never written in the script
import logging
from datetime import datetime
import boto3                            # the AWS package we installed, this is how python talks to AWS
# this imports all the tools we need in the script

#---------------------------------------------------------------------------------------------------------------

timestamp = datetime.now().strftime('%Y-%m-%d-T%H-%M-%S')                # timestamp for logging

load_dotenv()                           # this gives the script access to the credentials in our .env file

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')                # access key and secret key come from our IAM user
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

#---------------------------------------------------------------------------------------------------------------

# Logging set up as early as possible so everything after this point is recorded

logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)            # makes the logs folder, if it's already there it just carries on
log_filename = f'{logs_dir}/{timestamp}.log'

logging.basicConfig(
    filename=log_filename,
    format= '%(asctime)s - %(levelname)s - %(message)s',   # time, severity, message
    level = logging.INFO                                    # record INFO and anything more serious
)

logger = logging.getLogger() 
logger.info('Logger was successfuly initialised.') 

#---------------------------------------------------------------------------------------------------------------

data_dir = 'data/json'                     #the data lives in the json folder within the data folder
file_location = os.listdir(data_dir)       # list of all the file names in the json folder, this is what we loop through



# this connects us to S3 using the credentials from our IAM user
s3_client = boto3.client(
    's3',
    aws_access_key_id = AWS_ACCESS_KEY,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY
)

#---------------------------------------------------------------------------------------------------------------

for file in file_location:
    to_upload = f'{data_dir}/{file}'  #name of local files what will be uploaded to AWS S3
    try:
        s3_client.upload_file(to_upload, AWS_BUCKET_NAME, file)     # find the file locally, bucket we want it in, what we want it called in S3
        logging.info(f'File {file} has successfully uploaded!')
        os.remove(to_upload)            # deletes the local copy, only happens if the upload worked
    except Exception as e:              # if the upload fails it jumps here, so the file doesn't get deleted and the loop moves on to the next one
        print(f'Something went wrong. Error: {e}')