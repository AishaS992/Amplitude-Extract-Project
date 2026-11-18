import os                   # making the data folder
import time                 # waiting between retries
import logging
import requests             # calling the API

logger = logging.getLogger(__name__)

#-----------------------------------------------------------------------------------------------

def extract_api_to_zip(url: str, api_key: str, secret_key: str, start_time: str, end_time: str,
                       data_dir: str, timestamp: str, max_attempts: int, delay: int):
    """Calls the Amplitude Export API for a time range and saves the ZIP it sends back.

    Args:
        url (str): API endpoint to call
        api_key (str): API key, used as the username
        secret_key (str): secret key, used as the password
        start_time (str): first hour to pull, format YYYYMMDDTHH
        end_time (str): last hour to pull, format YYYYMMDDTHH
        data_dir (str): folder to save the ZIP to
        timestamp (str): timestamp for the file name
        max_attempts (int): number of times to try the call
        delay (int): seconds to wait between attempts

    Returns:
        bool: True if the ZIP was saved, False if not
    """

    # make the data folder if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)

    # build the file name, the timestamp means nothing gets overwritten
    zip_filename = f'{data_dir}/{timestamp}.zip'

    parameters = {
        'start': start_time,    # both start and end are required by the API
        'end': end_time
    }

    attempt = 1

    while attempt <= max_attempts:
        # basic auth, api key as the username and secret key as the password
        response = requests.get(url, params=parameters, auth=(api_key, secret_key), timeout=10)
        status_code = response.status_code

        if status_code == 200:
            with open(zip_filename, 'wb') as file:     # ZIP isn't text so it's written as bytes ('wb')
                file.write(response.content)
            print(f'File {zip_filename} saved successfully')
            logger.info(f'File {zip_filename} saved successfully')
            return True                                 # tells main.py the extract worked

        elif status_code in (400, 401, 403):
            # problem with the request or the keys, retrying won't help until it's fixed
            print(f'API call failed, status code {status_code}')
            logger.error(f'API call failed, status code {status_code}')
            return False

        elif status_code == 404:
            # no data for this range yet, usually bc of the 2 hour processing delay
            print('No data available for this range.')
            logger.info('No data available for this range.')
            return False

        elif status_code == 429 or 500 <= status_code < 600:
            # too many requests or a server problem, both temporary so wait and try again
            if attempt == max_attempts:
                print(f'Max number of attempts reached. Status code {status_code}. Investigate further.')
                logger.error(f'Max number of attempts reached. Status code {status_code}. Investigate further.')
                return False

            print(f'Attempt {attempt} failed, status code {status_code}, try again.')
            logger.warning(f'Attempt {attempt} failed, status code {status_code}, try again.')
            attempt += 1
            time.sleep(delay)

        else:
            # any code not handled above, stop rather than loop forever
            print(f'Unexpected error {status_code}.')
            logger.error(f'Unexpected error {status_code}.')
            return False

    return False    # safety net, shouldn't normally get here