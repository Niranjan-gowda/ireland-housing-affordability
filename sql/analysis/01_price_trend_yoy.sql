-- Q1. National RPPI: level and year-on-year % change, by property type.
-- Demonstrates a self-join on a 12-month lag (classic BA/DA growth metric).
SELECT
    d.full_date                              AS month,
    p.property_type,
    f.rppi_index_2015base                    AS rppi,
    ROUND(100.0 * (f.rppi_index_2015base - prev.rppi_index_2015base)
          / prev.rppi_index_2015base, 1)     AS yoy_pct_change
FROM fact_rppi f
JOIN dim_date        d ON d.date_key = f.date_key
JOIN dim_property_type p ON p.pt_key  = f.pt_key
JOIN dim_geography   g ON g.geo_key  = f.geo_key AND g.geography_name = 'National'
LEFT JOIN fact_rppi  prev
       ON prev.geo_key = f.geo_key
      AND prev.pt_key  = f.pt_key
      AND prev.date_key = (f.date_key - 10000)   -- same month, previous year
ORDER BY p.property_type, d.full_date;
