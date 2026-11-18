import os
import logging
import boto3                # the AWS package


logger = logging.getLogger(__name__)



def load_to_s3(AWS_BUCKET_NAME: str, AWS_ACCESS_KEY: str, AWS_SECRET_ACCESS_KEY: str, data_dir: str):
    """Function to load data into AWS S3 bucket

    Args:
        AWS_BUCKET_NAME (str): name of AWS S3 bucket
        AWS_ACCESS_KEY (str): key value (get value from .env in main)
        AWS_SECRET_ACCESS_KEY (str): secret value (get value from .env in main)
        data_dir (str): folder of files to upload
    """

    # connect to s3 with our credentials
    s3_client = boto3.client(
    's3',
    aws_access_key_id = AWS_ACCESS_KEY,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY
    )

    files = os.listdir(data_dir)

    for file in files:
        to_upload = f'{data_dir}/{file}'  # what we are calling the files we have saved locally to upload in AWS
        try:
            s3_client.upload_file(to_upload, AWS_BUCKET_NAME, file)  # find file locally, bucket you want it in, what you want the file to be called in AWS
            print(f'File {file} has successfully uploaded!')
            logger.info(f'File {file} has successfully uploaded!')
            os.remove(to_upload)        # only reached if the upload worked
        except Exception as e:
            print(f'Something went wrong. Error: {e}')
            logger.error(f'Something went wrong uploading {file}. Error: {e}')