# Amplitude-Project

An end to end data pipeline for Amplitude event data, built in stages: extract, load and transform.

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

---

## Extract

`amp-extract.py` pulls the previous day's events from Amplitude's Export API, saves the raw ZIP and unpacks it into JSON files.

    python amp-extract.py

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
- If the API call fails, the unpacking section still runs and errors

---

## Load

`amp-load.py` uploads the JSON files from `data/json/` to an AWS S3 bucket. From there they're loaded into Snowflake using SQL.

    python amp-load.py

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
