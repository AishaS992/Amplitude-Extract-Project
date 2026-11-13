import os
import requests
import dotenv
from dotenv import load_dotenv
from datetime import datetime, timedelta 
import json 
import time 
import logging 
import zipfile, gzip, shutil, tempfile

timestamp = datetime.now().strftime('%Y-%m-%d-T%H-%M-%S')

load_dotenv()

amp_api_key = os.getenv("AMP_API_KEY")
amp_secret_key = os.getenv("AMP_SECRET_KEY")

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

data_dir = 'data'
os.makedirs(data_dir, exist_ok=True)

filename = f'{data_dir}/{timestamp}.zip'

empty_zip = 'zip'
os.makedirs(empty_zip, exist_ok=True)
filename = f'{empty_zip}/{timestamp}.txt'

with zipfile.ZipFile(empty_zip, 'r') as zip_ref:
    zip_ref.extractall()


#start_time = '20261110T00'
#end_time = '20261110T23'

yesterday = (datetime.now() - timedelta(days=1))
start_time = yesterday.strftime('%Y%m%dT00')
end_time = yesterday.strftime('%Y%m%dT23')
print(yesterday)
print(start_time)
print(end_time)

url = 'https://analytics.eu.amplitude.com/api/2/export'

parameters = {
    'start': start_time,
    'end': end_time

}

attempt = 1
max_attempts = 4

while attempt<= max_attempts:
    response = requests.get(url, params=parameters, auth=(amp_api_key, amp_secret_key), timeout=10)
    status_code = response.status_code
    print(response.status_code) 

    if status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
            print(f'File {filename} saved successfully')
            logger.info(f'File {filename} saved successfully')
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
