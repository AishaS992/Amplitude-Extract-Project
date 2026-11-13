# Amplitude-Extract-Project

A Python script that extracts the previous day's event data from Amplitude's Export API, saves the raw ZIP locally, and unpacks it into individual JSON files ready to be loaded into cloud storage.

## What it extracts
Every event recorded in our Amplitude project for yesterday (all 24 hours, T00 to T23), using the EU endpoint `https://analytics.eu.amplitude.com/api/2/export`.

## Setup
1. Clone the repo and open it in VS Code
2. Create and activate a virtual environment: `python -m venv .venv` then `.venv\Scripts\activate`
3. Install the packages: `pip install -r requirements.txt`
4. Create a `.env` file in the top folder with:
   AMP_API_KEY=your_api_key
   AMP_SECRET_KEY=your_secret_key

## How to run
`python amp-extract.py`

## Output
- `data/` holds the raw ZIP for each run, named with the time it ran
- `data/json/` holds the unpacked JSON files, one event per line
- `logs/` holds a log file for each run

## How it works
1. Loads the API key and secret from `.env`
2. Works out yesterday's date and builds the start and end times
3. Calls the Export API, retrying on 429 and 5xx errors and stopping on 400, 401, 403 and 404
4. Saves the ZIP exactly as it arrives
5. Unzips it into a temporary folder, finds every `.gz` file, and decompresses each one into `data/json/`
6. Deletes the temporary folder and logs the result

## Known limitations
- Amplitude works in UTC, so during British Summer Time "yesterday" is out by an hour
- Running the script twice in one day downloads the same data twice, as nothing tracks what has already been pulled
- On Windows, deleting the temporary folder sometimes failed with an "access denied" error even though the folder was empty. The cause isn't confirmed, so the script uses `ignore_errors=True` and logs a warning if the folder is still there afterwards
