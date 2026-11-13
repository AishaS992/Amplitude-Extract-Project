# Amplitude-Extract-Project

This script extracts the previous day's event data from Amplitude's Export API, saves the raw download locally, and unpacks it into individual JSON files ready to be loaded into cloud storage. It's the extract step of a larger pipeline.

## Business context

Businesses use tools like Amplitude to track how people use their website or app, with every action recorded as an event. Those tools are great for quick answers, but the data lives inside them, which limits what you can do with it.

Extracting the raw data into your own storage means you control it. You can keep as much history as you need, combine it with data from other parts of the business, and analyse it in whatever tools your team already uses.

This script is the first step of that process. It pulls the data out of the source, keeps an untouched copy as a backup, and gets it into a format the next stage of the pipeline can load into cloud storage.

## About the data

Every action a user takes, such as viewing a page or clicking a button, is recorded as an event. Each event is a single JSON object holding details such as the event time, the user, their city and platform, and properties about the user and the event itself. The full list of fields is in the response schema in the Amplitude documentation.

## Setup

Clone the repo, open it in VS Code, then create and activate a virtual environment:

    python -m venv .venv
    .venv\Scripts\activate

Install the packages:

    pip install -r requirements.txt

Create a `.env` file in the top folder with the project's API key and secret key. This file is in `.gitignore` and should never be committed.

    AMP_API_KEY=your_api_key
    AMP_SECRET_KEY=your_secret_key

## How to run

    python amp-extract.py

Each run creates a raw ZIP in `data/`, unpacked JSON files in `data/json/`, and a log file in `logs/`, all named with the time the script ran so nothing gets overwritten.

## What the API documentation told us

A few things from the Amplitude documentation shaped how the script was built:

- Our project's data is stored in the EU, so the script uses `https://analytics.eu.amplitude.com/api/2/export` rather than the default URL
- Authentication is basic auth, with the API key as the username and the secret key as the password
- `start` and `end` are both required, written as `YYYYMMDDTHH`, and both hours are included, so `T00` to `T23` covers a full day
- The time range is based on when Amplitude received the data (`server_upload_time`), not when the event happened, and all times are in UTC
- Data only becomes available for export around 2 hours after Amplitude receives it, which is why the script asks for yesterday rather than today
- A single export can't be bigger than 6 GB, otherwise the API returns a 400
- The limit is 360 requests an hour and 4 at the same time, and going over either returns a 429
- The API doesn't remove duplicates, so asking for the same hours twice gives you the same events twice
- The response isn't plain JSON. It's a ZIP containing a numbered folder of gzip compressed files, and each of those holds JSON with one event per line

## Understanding the logic

The script has two jobs: get the data safely, then unpack it.

To get the data, it loads the key and secret, sets up logging, works out yesterday's date, and calls the API. Yesterday is used because it's a finished day that Amplitude has fully processed, and if the script runs once a day, each run picks up the next day without overlapping the last.

What happens next depends on the status code that comes back. A 200 means it worked, so the ZIP is saved exactly as it arrived. A 400, 401 or 403 means something is wrong with the request or the key, and since retrying the same request would just fail again, the script logs the error and stops. A 404 means there's no data for that range yet. A 429 or a 5xx means Amplitude is busy or having a temporary problem, so the script waits 30 seconds and tries again, up to 4 attempts in total. Any other code is unexpected, so the script stops rather than looping forever.

To unpack the data, the script keeps the raw ZIP untouched, so it can always be unpacked again without calling the API. It unzips everything into a temporary folder, works through every folder inside to find the `.gz` files, decompresses each one, and saves it with the same name minus `.gz` into `data/json/`. Once that's done, the temporary folder is deleted.

## Pseudocode

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

## Known limitations

- Amplitude works in UTC, so during British Summer Time "yesterday" is out by an hour
- Running the script twice in one day downloads the same data twice, as nothing keeps track of what has already been pulled
- If the API call fails, the unpacking section still runs and errors, because there's no ZIP to open
- On Windows, deleting the temporary folder sometimes failed with an "access denied" error even though the folder was empty. The cause isn't confirmed, so the script uses `ignore_errors=True` and logs a warning if the folder is still there afterwards
