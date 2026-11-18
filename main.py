from datetime import datetime, timedelta
from modules.extract_function import extract_api_to_zip
from modules.unnest_function import unnest_zip
from modules.load_function import load_to_s3
import logging
import os
from dotenv import load_dotenv


timestamp = datetime.now().strftime('%Y-%m-%d-T%H-%M-%S')

log_dir = 'logs' # set up logging as early in the script as possible
os.makedirs(log_dir, exist_ok=True)
log_filename = f'{log_dir}/{timestamp}.log'

logging.basicConfig(
    filename=log_filename,
    format= '%(asctime)s - %(levelname)s - %(message)s', # time, severity, message
    level = logging.INFO # record INFO and anything more serious
)

logger = logging.getLogger()
logger.info('Logger was successfully initialised.')

url = 'https://analytics.eu.amplitude.com/api/2/export' # EU endpoint as our data is stored in the EU
data_dir = 'data'
zip_filename = f'{data_dir}/{timestamp}.zip' # same path extract saves to, so unnest can find it
json_dir = f'{data_dir}/json'

load_dotenv() # gives the script access to the keys in .env

AMP_API_KEY = os.getenv('AMP_API_KEY')
AMP_SECRET_KEY = os.getenv('AMP_SECRET_KEY')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

# work out yesterday, T00 to T23 covers all 24 hours
yesterday = datetime.now() - timedelta(days=1)
start_time = yesterday.strftime('%Y%m%dT00')
end_time = yesterday.strftime('%Y%m%dT23')


extract_result = extract_api_to_zip(url, AMP_API_KEY, AMP_SECRET_KEY, start_time, end_time,
                                    data_dir, timestamp, max_attempts=4, delay=30)


# each step only runs if the one before it worked
if extract_result:
    unnest_result = unnest_zip(zip_filename, json_dir)

    if unnest_result:
        load_to_s3(AWS_BUCKET_NAME, AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, json_dir)
    else:
        logger.info('Unnest saved no JSON, nothing to upload so aborted.')
else:
    logger.info('Extract saved no data, nothing to unnest or upload so aborted.')