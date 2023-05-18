'''
Generates a SQLite database of market data from the EVE Online API.
'''

import time
import requests
import os
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_PW = os.getenv('REDIS_PW', 'password')

ONE_YEAR = 60 * 60 * 24 * 7 * 4 * 12

# urllib3 ignore SSL
requests.packages.urllib3.disable_warnings()

def chunks(lst, length):
    """
    Returns successive length-sized chunks from lst.
    """
    return [lst[i:i + length] for i in range(0, len(lst), length)]

# Function which pulls universeList.json file from S3
# and returns the regionID values as an array
def get_region_ids():
    '''
    Gets the region IDs from the universeList.json file
    '''
    response = requests.get(
        'https://evetrade.s3.amazonaws.com/resources/universeList.json',
        timeout=30
    )
    universe_list = response.json()

    region_ids = []
    for item in universe_list:
        station = universe_list[item]

        if 'region' in station:
            region_ids.append(station['region'])

    region_ids = list(set(region_ids))

    print(f'Getting orders for {len(region_ids)} regions.')

    return region_ids

def get_type_ids(region_id):
    '''
    Gets the type IDs from the typeIDToNames.json file
    '''
    type_ids = []
    curr_page = 1
    pages = 2
    while curr_page <= pages:
        response = requests.get(
            f'https://esi.evetech.net/latest/markets/{region_id}/types/?datasource=tranquility&page={curr_page}',
            timeout=30,
            verify=False
        )
        temp_ids = response.json()
        pages = int(response.headers['X-Pages'])
        curr_page += 1
        type_ids += temp_ids
    
    return type_ids

def get_data(region_ids):
    '''
    Gets market data for a given region and saves it to the local file system
    '''
  
    redis_connection = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW, decode_responses=True)

    for region_idx, region_id in enumerate(region_ids):
        len_region_ids = len(region_ids)
        start = time.time()
        pipeline = redis_connection.pipeline()

        type_ids =  get_type_ids(region_id)
        print(f'-- Getting data for {len(type_ids)} types in region {region_id}')
        for id_idx, type_id in enumerate(type_ids):
            len_type_ids = len(type_ids)
            # Get the orders for the region
            response = requests.get(
                f'https://esi.evetech.net/latest/markets/{region_id}/history/?datasource=tranquility&type_id={type_id}',
                timeout=30,
                verify=False
            )
            history = response.json()
            if len(history) == 0 or 'error' in history:
                continue
            else:
                try:
                    print(f'-- (Region: {region_idx+1} of {len_region_ids} - ID: {id_idx+1} of {len_type_ids}) Setting {region_id}-{type_id} to {history[-1]["average"]}')
                    pipeline.set(
                        name = f'{region_id}-{type_id}',
                        value = history[-1]['average'],
                        ex = ONE_YEAR
                    )
                except Exception:
                    print(history)
        print(f'-- Executing pipeline for region {region_id}')
        pipeline.execute()
        print(f'Percent complete: {round((region_idx / len(region_ids)) * 100, 2)}%')
    
        end = time.time()
        minutes = round((end - start) / 60, 2)
        print(f'Completed in {minutes} minutes.')

def execute_sync():
    '''
    Executes the data sync process
    '''
    start = time.time()

    region_ids = get_region_ids()
    get_data(region_ids)

    end = time.time()
    minutes = round((end - start) / 60, 2)
    print(f'Completed in {minutes} minutes.')
    return True

complete = False
while not complete:
    try:
        complete = execute_sync()
    except Exception as e:
        print(f'Error: {e}')
        print('Retrying in 2 minutes.')
        time.sleep(120)

