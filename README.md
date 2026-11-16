# Amplitude-Project

An end to end data pipeline for Amplitude event data, built in stages: extract, load and transform.

## Setup

- Clone the repo and open it in VS Code
- Create and activate a virtual environment:

      python -m venv .venv
      .venv\Scripts\activate

- Install the packages:

      pip install -r requirements.txt

- Create a `.env` file in the top folder with the Amplitude credentials. It's in `.gitignore` and should never be committed.

      AMP_API_KEY=your_api_key
      AMP_SECRET_KEY=your_secret_key



---

## Extract

`amp-extract.py` pulls the previous day's events from Amplitude's Export API, saves the raw ZIP, and unpacks it into individual JSON files.

### How to run

    python amp-extract.py

### Output

- `data/` holds the raw ZIP, named with the time the script ran
- `data/json/` holds the unpacked JSON files, one event per line
- `logs/` holds a log file for each run

### Key points from the API documentation

- Uses the EU endpoint, `https://analytics.eu.amplitude.com/api/2/export`
- Basic auth, with the API key as the username and the secret key as the password
- `start` and `end` are required, in the format `YYYYMMDDTHH`, and both hours are included
- Times are in UTC, and data is only available around 2 hours after Amplitude receives it, which is why the script pulls yesterday
- The response is a ZIP of gzip compressed files, each holding JSON with one event per line
- Limits: 6 GB per export, 360 requests an hour and 4 at once

### Pseudocode

- Load the API key and secret from `.env`
- Set up logging and the data folder
- Work out yesterday and build the start and end times
- Call the API
- Check the status code
    - 200: save the ZIP and carry on
    - 400, 401 or 403: log the error and stop
    - 404: log that there's no data yet and stop
    - 429 or 5xx: wait 30 seconds and try again, stopping after 4 attempts
    - Anything else: log it and stop
- Unzip the ZIP into a temporary folder
- Find every `.gz` file inside it
- Decompress each one and save it as JSON in `data/json/`
- Delete the temporary folder, and log a warning if it can't be deleted

### Known limitations

- During British Summer Time, "yesterday" in UTC is out by an hour
- Running it twice in one day downloads the same data twice
- If the API call fails, the unpacking section still runs and errors
- On Windows, deleting the temporary folder sometimes failed with "access denied", so it uses `ignore_errors=True` and logs a warning instead

---

