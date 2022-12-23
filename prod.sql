-- SQLite

-- Group total volume by date and type_id
SELECT date, type_id, SUM(volume)
FROM orders
GROUP BY "date", "type_id" limit 10;

-- Get change in volume for every day between orders
select
    t1.date,
    t1.type_id,
    t1.order_id,
    t1.volume,
    t2.volume,
    (t1.volume - t2.volume) as diff
from orders t1
join orders t2 
    on t2.order_id = t1.order_id
WHERE  
    t2.date = DATE(t1.date, '-1 day')
    LIMIT 10;

-- Get change in volume for every day for a given station and type id
SELECT
    t1.date,
    t1.type_id,
    t1.is_buy_order,
    SUM((t1.volume - t2.volume)) as diff
FROM orders t1
JOIN orders t2 
    on t2.order_id = t1.order_id
WHERE  
    t1.station_id == 60003760 AND
    t1.type_id == 34 AND 
    t2.date = DATE(t1.date, '-1 day')
GROUP BY t1.date
LIMIT 10;

-- Get change in volume grouped by station_id and type_id
-- Work in progress
-- SELECT
--     t1.date,
--     t1.type_id,
--     t1.station_id,
--     t1.is_buy_order,
--     SUM((t1.volume - t2.volume)) as diff
-- FROM orders t1
-- JOIN orders t2 
--     on t2.order_id = t1.order_id
-- WHERE  
--     t2.date = DATE(t1.date, '-1 day') AND
--     t1.type_id == 34 AND
--     t1.station_id == 60003760
-- GROUP BY t1.date, t1.is_buy_order
-- LIMIT 10;

-- Delete from table data that is older than 31 days
DELETE FROM orders WHERE date <= date('now','-31 day');