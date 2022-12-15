-- SQLite

-- Group total volume by date and type_id
SELECT date, type_id, SUM(volume)
FROM orders
GROUP BY "date", "type_id" limit 10;

-- Get change in volume for every day
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
    LIMIT 100;


-- Delete from table data that is older than 31 days
DELETE FROM orders WHERE date <= date('now','-31 day');