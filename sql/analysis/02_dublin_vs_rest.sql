-- Q2. Dublin vs the rest of the country: RPPI gap for all residential
-- properties, month by month. Positive gap = Dublin priced above the
-- rest-of-country index.
SELECT
    d.full_date AS month,
    MAX(CASE WHEN g.geography_name = 'Dublin' THEN f.rppi_index_2015base END)                      AS dublin,
    MAX(CASE WHEN g.geography_name = 'National excluding Dublin' THEN f.rppi_index_2015base END)    AS rest_of_country,
    ROUND(
        MAX(CASE WHEN g.geography_name = 'Dublin' THEN f.rppi_index_2015base END)
      - MAX(CASE WHEN g.geography_name = 'National excluding Dublin' THEN f.rppi_index_2015base END)
    , 1) AS dublin_gap
FROM fact_rppi f
JOIN dim_date        d ON d.date_key = f.date_key
JOIN dim_property_type p ON p.pt_key = f.pt_key AND p.property_type = 'All residential properties'
JOIN dim_geography   g ON g.geo_key  = f.geo_key
WHERE g.geography_name IN ('Dublin', 'National excluding Dublin')
GROUP BY d.full_date
ORDER BY d.full_date;
