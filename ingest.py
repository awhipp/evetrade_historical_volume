'''
Imputes the 20-day Historical Volume for all Regions and Item IDs
Ingests this data into Redis for query
'''

import time
import os
import redis
import sqlite3


REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_PW = os.getenv('REDIS_PW', 'password')

ONE_MONTH = 60 * 60 * 24 * 7 * 4

SETUP = [
    "pragma temp_store = memory;",
    "pragma mmap_size = 1099511627776;",
    "pragma page_size = 65536;",
    "pragma optimize;",
]

QUERY = """SELECT avg_agg.region_id, avg_agg.type_id, AVG(avg_agg.volume) as volume
FROM (
    SELECT sum_agg.region_id, sum_agg.type_id, sum_agg.date, SUM(sum_agg.volume) as volume
    FROM (
        SELECT 
            region_id, type_id, order_id, MAX(date) as date, SUM(volume) as volume -- Get most recent order for order_id
        FROM orders
        WHERE date >= date('now','-20 day') -- Number of days to average
        GROUP BY region_id, type_id, order_id -- Include order_id in order to average
    ) sum_agg
    GROUP BY sum_agg.region_id, sum_agg.type_id, sum_agg.date
) avg_agg 
GROUP BY avg_agg.region_id, avg_agg.type_id;
"""

def setup_sqlite():
    '''
    Sets up SQLite
    '''
    setup_start = time.time()
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    for query in SETUP:
        cursor.execute(query)
    conn.commit()
    conn.close()
    print(f'-- Setup SQLite in {int(time.time() - setup_start)} seconds')

def execute_sqlite_query():
    '''
    Generates 20-Day Historical Volume
    '''
    query_start = time.time()

    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute(QUERY)
    results = []
    for row in cursor:
        region_id = row[0]
        type_id = row[1]
        volume = int(row[2])
        results.append({
            'name': f'{region_id}-{type_id}',
            'value': f'{volume}',
        })
    conn.commit()
    conn.close()
    print(f'-- Executed SQLite query in {int(time.time() - query_start)} seconds')
    print(f'-- Going to ingest {cursor.rowcount} rows into Redis')
    return results

def chunks(lst, length):
    """
    Returns successive length-sized chunks from lst.
    """
    return [lst[i:i + length] for i in range(0, len(lst), length)]

def redis_ingest(chunked_results):
    """
    Connect and ingest keys into Redis
    """
    redis_connection = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW, decode_responses=True)
    start_redis = time.time()
    print('-- Executing Redis pipeline...')

    ingested = 0
    for chunk in chunked_results:
        pipeline = redis_connection.pipeline()
        for result in chunk:
            pipeline.set(
                name = result['name'],
                value = result['value'],
                ex = ONE_MONTH
            )
        pipeline.execute()
        ingested += len(chunk)
        print(f'-- Ingested {ingested} rows into Redis')
    print(f'-- Ingested into Redis in {int(time.time() - start_redis)} seconds')


start = time.time()
setup_sqlite()

volume_data = execute_sqlite_query()
redis_ingest(chunks(volume_data, 10000))

print(f'-- Total time: {int(time.time() - start)} seconds')
