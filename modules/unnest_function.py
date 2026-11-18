import os
import gzip                 # decompressing the .gz files
import shutil               # deleting the temp folder
import zipfile              # unzipping
import logging

logger = logging.getLogger(__name__)

#-----------------------------------------------------------------------------------------------

def unnest_zip(zip_filename: str, json_dir: str, temp_dir: str = 'zip'):
    """Unpacks the Amplitude ZIP (ZIP > numbered folder > .gz files) into one folder of JSON files.

    Args:
        zip_filename (str): file path of the ZIP saved by the extract
        json_dir (str): folder to save the JSON files to
        temp_dir (str, optional): temporary folder to unzip into, deleted at the end. Defaults to 'zip'.

    Returns:
        bool: True if at least one JSON file was saved, False if not
    """

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    json_count = 0      # counts how many JSON files get saved
    worked = True       # switched to False if anything goes wrong

    try:
        #------ unzip everything into the temp folder
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        #------ walk through the temp folder and every folder inside it, picking out the .gz files
        for folder_path, folders, files in os.walk(temp_dir):
            for file_name in files:
                if file_name.endswith('.gz'):
                    gz_path = os.path.join(folder_path, file_name)     # full path to the .gz file
                    json_name = file_name.replace('.gz', '')           # same name without .gz
                    json_path = os.path.join(json_dir, json_name)      # where the JSON will be saved

                    # gzip decompresses as it reads, then it's written out as the JSON file
                    with gzip.open(gz_path, 'rb') as gz_file:
                        with open(json_path, 'wb') as json_file:
                            json_file.write(gz_file.read())

                    json_count += 1
                    print(f'Decompressed {json_name}')

    except Exception as e:
        print(f'Something went wrong unnesting {zip_filename}. Error: {e}')
        logger.error(f'Something went wrong unnesting {zip_filename}. Error: {e}')
        worked = False

    #------ delete the temp folder whether it worked or not
    # on windows this sometimes failed with "access denied" even when empty, so errors are ignored
    # and a warning is logged if it's still there
    shutil.rmtree(temp_dir, ignore_errors=True)
    if os.path.exists(temp_dir):
        logger.warning(f'Could not fully delete {temp_dir}, delete it manually.')

    if not worked or json_count == 0:
        logger.warning('No JSON files were saved.')
        return False

    logger.info(f'{json_count} JSON files saved to {json_dir}')
    return True