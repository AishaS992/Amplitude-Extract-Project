import os
import requests
import dotenv
from dotenv import load_dotenv
from datetime import datetime, timedelta 
import json 
import time 
import logging 
import zipfile, gzip, shutil
#-----------------------------------------------------------------------------------------------
timestamp = datetime.now().strftime('%Y-%m-%d-T%H-%M-%S')

load_dotenv()

amp_api_key = os.getenv("AMP_API_KEY")
amp_secret_key = os.getenv("AMP_SECRET_KEY")


#-----------------------------------------------------------------------------------------------

logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)
log_filename = f'{logs_dir}/{timestamp}.log'

logging.basicConfig(
    filename=log_filename,
    format= '%(asctime)s - %(levelname)s - %(message)s',
    level = logging.INFO
)

logger = logging.getLogger() 
logger.info('Logger was successfuly initialised.') 

#-----------------------------------------------------------------------------------------------

data_dir = 'data'
os.makedirs(data_dir, exist_ok=True)

zip_filename = f'{data_dir}/{timestamp}.zip'

#-----------------------------------------------------------------------------------------------


yesterday = (datetime.now() - timedelta(days=1))
start_time = yesterday.strftime('%Y%m%dT00')
end_time = yesterday.strftime('%Y%m%dT23')
print(yesterday)
print(start_time)
print(end_time)

#-----------------------------------------------------------------------------------------------

url = 'https://analytics.eu.amplitude.com/api/2/export'

parameters = {
    'start': start_time,
    'end': end_time

}

#-----------------------------------------------------------------------------------------------

attempt = 1
max_attempts = 4

while attempt<= max_attempts:
    response = requests.get(url, params=parameters, auth=(amp_api_key, amp_secret_key), timeout=10)
    status_code = response.status_code
    print(response.status_code) 

    if status_code == 200:
        with open(zip_filename, 'wb') as file:
            file.write(response.content)
            print(f'File {zip_filename} saved successfully')
            logger.info(f'File {zip_filename} saved successfully')
        break
    elif status_code in (400, 401, 403):
        print(f'API call failed, status code {status_code}')
        logger.error(f'API call failed, status code {status_code}')
        break
        
    elif status_code == 404:
        print(f'No data available for this range.')
        logger.info(f'No data available for this range.')
        break

    else:
        if status_code == 429 or 500<=status_code<600:
            if attempt==max_attempts:
                print(f'Max number of attempts reached. Status code {status_code}. Investigate further.')
                logger.error(f'Max number of attempts reached. Status code {status_code}. Investigate further.')
                break
        
            else:
                print(f'Attempt {attempt} failed, status code {status_code}, try again.')
                logger.warning(f'Attempt {attempt} failed, status code {status_code}, try again.')
                attempt+=1
                time.sleep(30) 
        else:
            print(f'Unexpected error {status_code}.')
            logger.error(f'Unexpected error {status_code}.')
            break

#-----------------------------------------------------------------------------------------------

empty_zip = 'zip'
os.makedirs(empty_zip, exist_ok=True)

with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
    zip_ref.extractall(empty_zip)
    print(os.listdir(empty_zip))

#-----------------------------------------------------------------------------------------------

for folder_path, folders, files in os.walk(empty_zip):
    for file_name in files:
        if file_name.endswith('.gz'):
            print(file_name)

#-----------------------------------------------------------------------------------------------

json_dir = f'{data_dir}/json'
os.makedirs(json_dir, exist_ok=True)

for folder_path, folders, files in os.walk(empty_zip):
    for file_name in files:
        if file_name.endswith('.gz'):
            gz_path = os.path.join(folder_path, file_name)
            json_name = file_name.replace('.gz', '')
            json_path = os.path.join(json_dir, json_name)

            with gzip.open(gz_path,'rb') as gz_file:
                with open(json_path, 'wb') as json_file:
                    json_file.write(gz_file.read())

            print(f'Decompressed {json_name}')

#-----------------------------------------------------------------------------------------------

shutil.rmtree(empty_zip, ignore_errors=True)
if os.path.exists(empty_zip):
    logger.warning(f'Could not fully delete {empty_zip}, delete it manually. ')
