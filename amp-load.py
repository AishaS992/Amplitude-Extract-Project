import os
import json
from dotenv import load_dotenv
import logging
from datetime import datetime
import boto3

timestamp = datetime.now().strftime('%Y-%m-%d-T%H-%M-%S')                # timestamp for logging

load_dotenv()

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

# Logging set up as early as possible so everything after this point is recorded

logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)
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
file_location = os.listdir(data_dir)


s3_client = boto3.client(
    's3',
    aws_access_key_id = AWS_ACCESS_KEY,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY
)

for file in file_location:
    to_upload = f'{data_dir}/{file}'  #name of local files what will be uploaded to AWS S3
    try:
        s3_client.upload_file(to_upload, AWS_BUCKET_NAME, file)
        logging.info(f'File {file} has successfully uploaded!')
        os.remove(to_upload)
    except Exception as e:
        print(f'Something went wrong. Error: {e}')
    