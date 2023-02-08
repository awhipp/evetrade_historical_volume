-- SQLite

-- PRAGMA for faster queries
pragma temp_store = memory;
pragma mmap_size = 1099511627776;
pragma page_size = 65536;
.open data.db;
pragma optimize;
.headers ON;
.timer ON;
-- .mode csv;
-- .output output.csv
-- .mode stdout

-- Step 1: Get the latest order for each order_id and sum the volume
SELECT 
    region_id, type_id, order_id, MAX(date) as date, SUM(volume) as volume -- Get most recent order for order_id
FROM orders
WHERE date >= date('now','-20 day') -- Number of days to average
GROUP BY region_id, type_id, order_id -- Include order_id in order to average

-- Step 2: Collapse orders to date
SELECT sum_agg.region_id, sum_agg.type_id, sum_agg.date, SUM(sum_agg.volume) as volume
FROM (
    SELECT 
        region_id, type_id, order_id, MAX(date) as date, SUM(volume) as volume -- Get most recent order for order_id
    FROM orders
    WHERE date >= date('now','-20 day') -- Number of days to average
    GROUP BY region_id, type_id, order_id -- Include order_id in order to average
) sum_agg
GROUP BY sum_agg.region_id, sum_agg.type_id, sum_agg.date

-- Step 3: Collapse orders to date
SELECT avg_agg.region_id, avg_agg.type_id, AVG(avg_agg.volume) as volume
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
GROUP BY avg_agg.region_id, avg_agg.type_id