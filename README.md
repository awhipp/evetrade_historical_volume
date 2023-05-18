# EVE Trade Historical Volume Job

This is a job that will impute the historical volume based on the regular market orders provided by EVE Trade ESI

[![Historical Volume Ingest](https://github.com/awhipp/evetrade_historical_volume/actions/workflows/historical-volume-ingest.yml/badge.svg)](https://github.com/awhipp/evetrade_historical_volume/actions/workflows/historical-volume-ingest.yml)

## Requirements

* python3.10
* poetry
  * poetry install
  * poetry update
  * poetry run python app.py

## Development

* Generate requirements.txt
  * `poetry export --without-hashes --format=requirements.txt > requirements.txt`

## Process

* Iteratively pulls region IDs and type IDs and requests data from EVE ESI API.
