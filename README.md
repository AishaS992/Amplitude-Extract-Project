# Amplitude-Project

An end to end data pipeline for Amplitude event data, built in stages: [extract](#extract), [load](#load) and transform (to come).

The pipeline pulls the previous day's events from the Amplitude API, unpacks them into JSON files and uploads them to an AWS S3 bucket. Snowpipe then loads each new file into Snowflake automatically. The whole thing runs once a day, scheduled by Kestra.

    Amplitude API > main.py (extract, unnest, load) > S3 > Snowpipe > Snowflake

## Contents

- [Project structure](#project-structure)
- [Setup](#setup)
- [Extract](#extract)
- [Load](#load)
- [Modularised pipeline](#modularised-pipeline)
- [Orchestration (Kestra)](#orchestration-kestra)
- [Snowpipe](#snowpipe)

---

## Project structure

    main.py                      runs the whole pipeline in order
    modules/
        extract_function.py      calls the API and saves the ZIP
        unnest_function.py       unpacks the ZIP into JSON files
        load_function.py         uploads the JSON files to S3
    archive/
        amp-extract.py           original extract script, before modularising
        amp-load.py              original load script, before modularising
    requirements.txt             packages the pipeline needs

---

## Setup

- Clone the repo and open it in VS Code
- Create and activate a virtual environment, then install the packages:

      python -m venv .venv
      .venv\Scripts\activate
      pip install -r requirements.txt

- Create a `.env` file in the top folder. It's in `.gitignore` and should never be committed.

      AMP_API_KEY=your_api_key
      AMP_SECRET_KEY=your_secret_key
      AWS_ACCESS_KEY=your_access_key
      AWS_SECRET_ACCESS_KEY=your_secret_key
      AWS_BUCKET_NAME=your_bucket_name

- Run the pipeline:

      python main.py

---

## Extract

> This section describes the original extract script, now kept in `archive/`. The same logic now runs through `main.py`, see [Modularised pipeline](#modularised-pipeline).

`amp-extract.py` pulls the previous day's events from Amplitude's Export API, saves the raw ZIP and unpacks it into JSON files.

    python archive/amp-extract.py

### Output

- `data/` holds the raw ZIP, named with the time the script ran
- `data/json/` holds the unpacked JSON files, one event per line
- `logs/` holds a log file for each run

### Key points

- Uses the EU endpoint with basic auth (API key as username, secret key as password)
- `start` and `end` are required, in the format `YYYYMMDDTHH`
- Data is only available around 2 hours after Amplitude receives it, which is why the script pulls yesterday
- Status codes: 200 saves the ZIP, 429 and 5xx retry up to 4 times, anything else logs the error and stops

### Known limitations

- During British Summer Time, "yesterday" in UTC is out by an hour
- Running it twice in one day downloads the same data twice
- If the API call fails, the unpacking section still runs and errors (fixed in the modularised version, where unpacking only runs if the extract worked)

---

## Load

> This section describes the original load script, now kept in `archive/`. The upload now runs through `main.py`, and the move from S3 into Snowflake is automated with [Snowpipe](#snowpipe).

`amp-load.py` uploads the JSON files from `data/json/` to an AWS S3 bucket. From there they're loaded into Snowflake using SQL.

    python archive/amp-load.py

### Output

- Each JSON file is uploaded to the S3 bucket with the same name
- The local copy in `data/json/` is deleted once it has uploaded, while the raw ZIP stays in `data/`
- `logs/` holds a log file for each run, including any failed uploads
- In Snowflake, the data lands in the `raw` table, with the JSON in a `VARIANT` column and the source file name

### Key points

- The Python script connects to S3 with `boto3`, using the IAM user keys from `.env`
- The files in S3 are encrypted with a KMS key, and an IAM policy allows access to the bucket and the key
- Snowflake reads the bucket through an IAM role, linked with a storage integration and a stage (`as_amplitude_stage`)
- `COPY INTO` loads the files from the stage into the `raw` table, and skips any files it has already loaded

---

## Modularised pipeline

The extract and load scripts were split into reusable functions, so the same code can be run in one go, locally or by Kestra. `main.py` handles the setup and calls each function in order.

### What main.py does

1. Creates a timestamp for the run and sets up logging
2. Loads the Amplitude and AWS keys from `.env` (or from the Kestra KV store when it runs there)
3. Works out yesterday's start and end times
4. Calls `extract_api_to_zip`
5. If the extract worked, calls `unnest_zip`
6. If unnesting worked, calls `load_to_s3`

Each function returns `True` or `False`, so a step only runs if the one before it worked. If no data comes back, nothing is unpacked or uploaded.

### The functions

- `extract_api_to_zip` calls the API with retries and saves the ZIP to `data/`
- `unnest_zip` unzips into a temporary folder, decompresses each `.gz` file into `data/json/`, then deletes the temporary folder
- `load_to_s3` uploads each JSON file to S3 and deletes the local copy once it has uploaded

Each function's arguments are documented in its docstring.

---

## Orchestration (Kestra)

Kestra runs the pipeline automatically once a day. Kestra itself runs in Docker.

### What the flow does

- Flow `amplitude_ingestion_DES9` in the `amplitude` namespace
- Clones this repo from GitHub into a working directory
- Starts a Python container, installs `requirements.txt`, then runs `python main.py`
- Passes the keys in as environment variables from the namespace's KV store

### Schedule

- Runs daily at 3am UTC (`0 3 * * *`)
- Once a day because the pipeline pulls the whole of yesterday. Running it more often would pull the same day again, and the API doesn't remove duplicates
- 3am leaves time for the day to finish and for Amplitude's 2 hour delay

### KV store

These keys need adding to the `amplitude` namespace's KV store, with the same names as `.env`:

    AMP_API_KEY
    AMP_SECRET_KEY
    AWS_ACCESS_KEY
    AWS_SECRET_ACCESS_KEY
    AWS_BUCKET_NAME

### Things to know

- Kestra clones the `main` branch, so changes need merging into main before Kestra uses them
- Each run happens in a temporary container, so the log file and raw ZIP are deleted when the run ends. The print messages show in Kestra's logs instead

---

## Snowpipe

Snowpipe loads each new file into Snowflake automatically, shortly after it lands in S3, so no manual `COPY INTO` is needed.

### How it's set up

1. A pipe, `as_des9_amplitude_snowpipe`, with `AUTO_INGEST = TRUE`, runs the same `COPY INTO` from `@as_amplitude_stage` into the `raw` table
2. `show pipes;` gives the pipe's `notification_channel` value (an SQS queue ARN), the location Snowflake watches for new files
3. The S3 bucket has an event notification (Properties, then Event notifications) that sends new object events to that SQS queue

The full SQL for the pipe is in [`snowflake/snowpipe.sql`](snowflake/snowpipe.sql).

When a file lands, S3 notifies Snowflake and Snowpipe runs the copy.

### Checking it works

- `select system$pipe_status('as_des9_amplitude_snowpipe');` should show `RUNNING`, and `lastReceivedMessageTimestamp` should update after each Kestra run
- `select count(*) from raw;` should go up after each daily run
- `COPY_HISTORY` shows which files loaded or failed, and why

### Things to know

- Snowpipe only picks up files that arrive after the pipe was created. To load files already in the bucket, run `alter pipe as_des9_amplitude_snowpipe refresh;`
- Files with a name that has already been loaded are skipped
