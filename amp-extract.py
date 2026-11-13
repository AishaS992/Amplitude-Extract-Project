
import os                                   # folders, file paths and reading the .env values
import requests                             # calling the API
import dotenv
from dotenv import load_dotenv              # loading the API key and secret from .env
from datetime import datetime, timedelta    # timestamps and working out yesterday
import json
import time                                 # waiting between retries
import logging                              # writing a log file for each run
import zipfile, gzip, shutil                # unzipping, decompressing and deleting folders
#-----------------------------------------------------------------------------------------------
# Timestamp for this run, used to give every file a unique name so nothing gets overwritten
timestamp = datetime.now().strftime('%Y-%m-%d-T%H-%M-%S')

# Load the API key and secret from .env so they are never written in the script
load_dotenv()

amp_api_key = os.getenv("AMP_API_KEY")
amp_secret_key = os.getenv("AMP_SECRET_KEY")


#-----------------------------------------------------------------------------------------------
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

#-----------------------------------------------------------------------------------------------
# Folder for the raw data, and the file name the ZIP will be saved as

data_dir = 'data'
os.makedirs(data_dir, exist_ok=True)

zip_filename = f'{data_dir}/{timestamp}.zip'

#-----------------------------------------------------------------------------------------------
# Work out yesterday and build the start and end times in the format the API needs (YYYYMMDDTHH)
# T00 to T23 covers all 24 hours, because the API includes both the start and end hour

yesterday = (datetime.now() - timedelta(days=1))
start_time = yesterday.strftime('%Y%m%dT00')
end_time = yesterday.strftime('%Y%m%dT23')
print(yesterday)
print(start_time)
print(end_time)

#-----------------------------------------------------------------------------------------------
# EU endpoint, as our project's data is stored in the EU

url = 'https://analytics.eu.amplitude.com/api/2/export'

# start and end are both required parameters
parameters = {
    'start': start_time,
    'end': end_time

}

#-----------------------------------------------------------------------------------------------
# Call the API, retrying when it makes sense to and stopping when it doesn't

attempt = 1
max_attempts = 4

while attempt<= max_attempts:
    # Basic authentication: API key as the username, secret key as the password
    response = requests.get(url, params=parameters, auth=(amp_api_key, amp_secret_key), timeout=10)
    status_code = response.status_code
    print(response.status_code) 

    if status_code == 200:
        # Success: the response is a ZIP, which isn't text, so it is written as bytes ('wb')
        with open(zip_filename, 'wb') as file:
            file.write(response.content)
            print(f'File {zip_filename} saved successfully')
            logger.info(f'File {zip_filename} saved successfully')
        break
    elif status_code in (400, 401, 403):
        # A problem with the request or the key, so retrying won't help until it's fixed
        print(f'API call failed, status code {status_code}')
        logger.error(f'API call failed, status code {status_code}')
        break
        
    elif status_code == 404:
        # No data for this range yet, usually because of Amplitude's 2 hour processing delay
        print(f'No data available for this range.')
        logger.info(f'No data available for this range.')
        break

    else:
        if status_code == 429 or 500<=status_code<600:
            # Too many requests or a server problem, both temporary, so wait and try again
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
            # Any code not handled above, so stop rather than loop forever
            print(f'Unexpected error {status_code}.')
            logger.error(f'Unexpected error {status_code}.')
            break

#-----------------------------------------------------------------------------------------------
# Unnest: ZIP > numbered folder > .gz files > JSON files
# The raw ZIP is kept, so the data can be reprocessed without calling the API again

# Temporary folder to unzip into, deleted at the end
empty_zip = 'zip'
os.makedirs(empty_zip, exist_ok=True)

# Open the ZIP saved above in read mode and extract everything into the temporary folder
with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
    zip_ref.extractall(empty_zip)
    print(os.listdir(empty_zip))

#-----------------------------------------------------------------------------------------------
# Check: walk through the temporary folder and print every .gz file found

for folder_path, folders, files in os.walk(empty_zip):
    for file_name in files:
        if file_name.endswith('.gz'):
            print(file_name)

#-----------------------------------------------------------------------------------------------
# Folder where the final JSON files go

json_dir = f'{data_dir}/json'
os.makedirs(json_dir, exist_ok=True)

# Walk through the temporary folder and every folder inside it, picking out the .gz files
for folder_path, folders, files in os.walk(empty_zip):
    for file_name in files:
        if file_name.endswith('.gz'):
            gz_path = os.path.join(folder_path, file_name)     # full path to the .gz file
            json_name = file_name.replace('.gz', '')           # same name without .gz
            json_path = os.path.join(json_dir, json_name)      # where the JSON will be saved

            # Read the compressed file (gzip decompresses as it reads) and write it out as JSON
            with gzip.open(gz_path,'rb') as gz_file:
                with open(json_path, 'wb') as json_file:
                    json_file.write(gz_file.read())

            print(f'Decompressed {json_name}')

#-----------------------------------------------------------------------------------------------
# Delete the temporary folder. On Windows this sometimes failed with "access denied" even though
# the folder was empty, so errors are ignored here and a warning is logged if it's still there

shutil.rmtree(empty_zip, ignore_errors=True)
if os.path.exists(empty_zip):
    logger.warning(f'Could not fully delete {empty_zip}, delete it manually. ')
