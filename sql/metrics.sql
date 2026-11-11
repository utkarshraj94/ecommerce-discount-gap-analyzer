-- 1. Segment summary: listings, average price, average discount
SELECT c.segment,
       COUNT(*) AS listings,
       ROUND(AVG(f.price), 0) AS avg_price,
       ROUND(AVG(f.discount_pct), 1) AS avg_discount
FROM fact_listing f
JOIN dim_category c ON f.category_id = c.category_id
GROUP BY c.segment
ORDER BY listings DESC;

-- 2. Share of full-price listings and unrated listings per segment
SELECT c.segment,
       ROUND(100.0 * SUM(f.discount_pct = 0) / COUNT(*), 1) AS pct_full_price,
       ROUND(100.0 * SUM(f.has_rating = 0) / COUNT(*), 1) AS pct_unrated
FROM fact_listing f
JOIN dim_category c ON f.category_id = c.category_id
GROUP BY c.segment;

-- 3. Top 10 brands by listings in Men's Kurtas
SELECT b.brand_name,
       COUNT(*) AS listings,
       ROUND(AVG(f.discount_pct), 1) AS avg_discount
FROM fact_listing f
JOIN dim_brand b ON f.brand_id = b.brand_id
JOIN dim_category c ON f.category_id = c.category_id
WHERE c.segment = 'Men''s Kurtas'
GROUP BY b.brand_name
ORDER BY listings DESC
LIMIT 10;