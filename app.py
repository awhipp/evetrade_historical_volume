"""
Generates historical volume details and loads them into Redis
"""

import concurrent.futures
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import redis
import requests
import urllib3
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
REDIS_PW: str = os.getenv("REDIS_PW", "password")

redis_connection = redis.StrictRedis(
    host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW, decode_responses=True
)

ONE_YEAR: int = 60 * 60 * 24 * 7 * 4 * 12

# urllib3 ignore SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def chunks(lst: List[Any], length: int) -> List[List[Any]]:
    """
    Returns successive length-sized chunks from lst.
    """
    return [lst[i : i + length] for i in range(0, len(lst), length)]


def get_region_ids() -> List[str]:
    """
    Gets the region IDs from the universeList.json file
    """
    response = requests.get(
        "https://evetrade.s3.amazonaws.com/resources/universeList.json", timeout=30
    )
    universe_list: Dict[str, Any] = response.json()

    region_ids: List[str] = []
    for item in universe_list:
        station = universe_list[item]

        if "region" in station:
            region_ids.append(station["region"])

    region_ids = list(set(region_ids))

    print(f"Getting orders for {len(region_ids)} regions.")

    return region_ids


def get_type_ids(region_id: int) -> List[int]:
    """
    Gets the type IDs from the typeIDToNames.json file
    """
    type_ids: List[int] = []
    curr_page: int = 1
    pages: int = 2
    while curr_page <= pages:
        response = requests.get(
            f"https://esi.evetech.net/latest/markets/{region_id}/types/?datasource=tranquility&page={curr_page}",
            timeout=30,
            verify=False,
        )
        temp_ids: List[int] = response.json()
        pages = int(response.headers["X-Pages"])
        curr_page += 1
        type_ids += temp_ids

    return type_ids


def get_average_volume(history: List[Dict[str, Any]]) -> int:
    """
    Gets the average volume for a given type over the last 20 days
    """
    # Get the date 20 days ago
    twenty_days_ago = datetime.now() - timedelta(days=20)

    # Filter history to include only the last 20 days
    recent_history = [
        day
        for day in history
        if datetime.strptime(day["date"], "%Y-%m-%d") >= twenty_days_ago
    ]

    if not recent_history:
        return 0  # or handle this case as needed

    total_volume = sum(day["volume"] for day in recent_history)
    return int(total_volume / len(recent_history))


def slice_history(history: List[Dict[str, Any]], num_days: int) -> List[Dict[str, Any]]:
    """
    Gets the last N days of history, where N is num_days.
    The history is a list of dictionaries where date may be unsorted. Ensure the list is sorted by date.
    """
    history = sorted(history, key=lambda x: x["date"])

    if len(history) < num_days:
        return history
    return history[-num_days:]


def fetch_history(region_id: int, type_id: int) -> List[Dict[str, Any]]:
    """
    Fetches the history for a given type in a given region
    """
    response = requests.get(
        f"https://esi.evetech.net/latest/markets/{region_id}/history/?datasource=tranquility&type_id={type_id}",
        timeout=30,
        verify=False,
    )
    return response.json()


def get_data(region_id: int) -> None:
    """
    Gets market data for a given region and saves it to the local file system
    """
    pipeline = redis_connection.pipeline()

    type_ids: List[int] = get_type_ids(region_id)
    print(f"-- Getting data for {len(type_ids)} types in region {region_id}")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_type_id = {}
        for type_id in type_ids:
            future = executor.submit(fetch_history, region_id, type_id)
            future_to_type_id[future] = type_id

        for future in concurrent.futures.as_completed(future_to_type_id):
            type_id = future_to_type_id[future]
            try:
                history = future.result()
                if len(history) == 0 or "error" in history:
                    continue
                else:
                    history = slice_history(history, 20)
                    try:
                        average: int = get_average_volume(history)
                        print(f"-- Setting {region_id}-{type_id} to {average}")
                        pipeline.set(
                            name=f"{region_id}-{type_id}", value=average, ex=ONE_YEAR
                        )
                    except Exception:  # pylint: disable=broad-except
                        print(f"Error setting {region_id}-{type_id} to {average}")
                        print(history)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"Error fetching data for type_id {type_id}: {exc}")

    print(f"-- Executing pipeline for region {region_id}")
    pipeline.execute()


def execute_sync() -> bool:
    """
    Executes the data sync process
    """
    start: float = time.time()

    # Get next region to process
    region_ids: List[str] = get_region_ids()
    curr_region: Any = redis_connection.get("volume_region")
    curr_index: int = -1

    # If no region is set, start at the beginning
    if curr_region is None:
        curr_region = region_ids[0]
        curr_index = 0
    else:
        curr_region = int(curr_region)
        curr_index = region_ids.index(curr_region)

    # If we're at the end of the list, start over
    next_region: str = ""
    try:
        next_region = region_ids[curr_index + 1]
    except IndexError:
        next_region = region_ids[0]

    redis_connection.set("volume_region", next_region)
    print(f"Current region: {curr_region}")
    print(f"Next region: {next_region}")

    get_data(curr_region)

    end: float = time.time()
    minutes: float = round((end - start) / 60, 2)
    print(f"Completed in {minutes} minutes.")
    return True


COMPLETE: bool = False
while not COMPLETE:
    try:
        COMPLETE = execute_sync()
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error: {e}")
        print("Retrying in 2 minutes.")
        time.sleep(120)
