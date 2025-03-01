# EVE Trade Historical Volume Job

This is a job that will use the EVE API to get he average volume for orders in a region and store hem in redis.

Originally it was used impute the historical volume based on the regular market orders provided by EVE Trade ESI when the volume endpoint was down. This is why there are releases which had the historical market data.

[![Historical Volume Ingest](https://github.com/awhipp/evetrade_historical_volume/actions/workflows/historical-volume-ingest.yml/badge.svg)](https://github.com/awhipp/evetrade_historical_volume/actions/workflows/historical-volume-ingest.yml)

## Requirements

* python3.10
* poetry
  * poetry install
  * poetry update
  * poetry run python app.py

### Precommit

* poetry run pre-commit install
* poetry run pre-commit run --all-files

## Process

* Iteratively pulls region IDs and type IDs and requests data from EVE ESI API.
* Does one region every hour, and loops through all in roughly 1.5 days.
