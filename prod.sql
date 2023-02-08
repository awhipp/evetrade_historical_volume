-- SQLite

-- PRAGMA for faster queries
pragma temp_store = memory;
pragma mmap_size = 30000000000;
pragma page_size = 32768;
pragma optimize;
.headers ON
.timer ON
.open data.db
.mode csv
.output volume20day.csv

-- Get the latest order for each order_id
SELECT 
    region_id, type_id, order_id, max(date), volume
FROM orders
GROUP BY region_id, type_id, order_id
LIMIT 10;

-- Get the latest order for each order_id and sum the volume
SELECT agg.region_id, agg.type_id, sum(agg.volume)
FROM (
    SELECT 
        region_id, type_id, order_id, max(date), volume
    FROM orders
    GROUP BY region_id, type_id, order_id 
    LIMIT 10
) agg
GROUP BY agg.region_id, agg.type_id

-- Get the latest order for each order_id and sum the volume
SELECT agg.region_id, agg.type_id, AVG(agg.volume) -- Get average over N-days
FROM (
    SELECT 
        region_id, type_id, order_id, MAX(date), volume -- Get most recent order for order_id
    FROM orders
    WHERE date >= date('now','-20 day') -- Number of days to average
    GROUP BY region_id, type_id, order_id -- Include order_id in order to average
) agg
GROUP BY agg.region_id, agg.type_id