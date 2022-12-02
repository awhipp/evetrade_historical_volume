# EVE Trade Historical Volume Job

This is a job that will impute the historical volume based on the daily orders provided by EVE Trade ESI

## Requirements

* sqlite3
* python3.10
* poetry
    * poetry install
    * poetry update
    * poetry run python app.py

## Development

* Generate requirements.txt
    * `poetry export --without-hashes --format=requirements.txt > requirements.txt`

## Process

* Pulls the latest release from GitHub repository releases (contains 30 days of compressed order data in SQLite format)
* Decompresses the SQLite file
* Appends new data to the existing SQLite database
* Imputes the historical volume based on the daily orders
* Adds the historical volume to the existing REDIS cache
* Compresses the SQLite file
* Pushes the compressed SQLite file to GitHub repository releases