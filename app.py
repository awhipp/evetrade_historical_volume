'''
Data Sync Service which pulls data from the EVE API and loads it into the Elasticsearch instance
'''

import time
import asyncio
import requests
import sqlite3

from market_data import MarketData

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

def get_data(region_ids):
    '''
    Gets market data for a given region and saves it to the local file system
    '''

    all_orders = []

    for region_id in region_ids:
        print(f'-- Getting orders for region {region_id}')

        market_data = MarketData(region_id)

        orders = asyncio.run(market_data.execute_requests())
        all_orders = all_orders + orders

        print(f'-- Got {len(orders)} orders for region {region_id}')

    return all_orders

def ingest_into_sqlite(all_orders):
    '''
    Ingests the market data into the SQLite database
    '''
    start = time.time()

    conn = sqlite3.connect('data.db')

    cursor = conn.cursor()

    # Create the orders table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            date DATE DEFAULT CURRENT_DATE,
            order_id INTEGER,
            region_id INTEGER,
            system_id INTEGER,
            station_id INTEGER,
            type_id INTEGER,
            is_buy_order BOOLEAN,
            volume_remain INTEGER,
            volume_total INTEGER,
            volume INTEGER,
            PRIMARY KEY (date, order_id)
        )
    ''')

    # Insert the orders into the database
    for order in all_orders:
        cursor.execute('''
            INSERT INTO orders (
                order_id,
                region_id,
                system_id,
                station_id,
                type_id,
                is_buy_order,
                volume_remain,
                volume_total,
                volume
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (date, order_id) 
            DO UPDATE SET
                volume_remain = excluded.volume_remain,
                volume_total = excluded.volume_total,
                volume = excluded.volume
        ''', (
            order['order_id'],
            order['region_id'],
            order['system_id'],
            order['station_id'],
            order['type_id'],
            order['is_buy_order'],
            order['volume_remain'],
            order['volume_total'],
            order['volume_total'] - order['volume_remain']
        ))

    # Delete orders older than 31 days (to save space)
    ## 31 days instead of 30 so we can see the change over time from 30 days
    cursor.execute("DELETE FROM orders WHERE date <= date('now','-31 day')")
    conn.commit()

    # Vacuum the database to save space
    conn.execute("VACUUM")
    conn.commit()

    conn.close()

    end = time.time()
    minutes = round((end - start) / 60, 2)
    print(f'Ingested into SQLite in {minutes} minutes.')

def execute_sync():
    '''
    Executes the data sync process
    '''
    start = time.time()

    region_ids = get_region_ids()
    data = get_data(region_ids)
    ingest_into_sqlite(data)
    print(f'{len(data)} orders retrieved.')
    end = time.time()
    minutes = round((end - start) / 60, 2)
    print(f'Completed in {minutes} minutes.')

execute_sync()
