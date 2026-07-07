-- Q3. County rent ranking and affordability signal (latest quarter).
-- Ranks counties by standardised average monthly rent, shows the premium /
-- discount vs the national average, and the implied annual rent bill.
WITH national AS (
    SELECT avg_monthly_rent_eur AS nat_rent
    FROM fact_rent r
    JOIN dim_geography g ON g.geo_key = r.geo_key
    WHERE g.geo_level = 'National'
)
SELECT
    RANK() OVER (ORDER BY r.avg_monthly_rent_eur DESC) AS rent_rank,
    g.geography_name                                    AS county,
    r.avg_monthly_rent_eur                              AS monthly_rent,
    r.avg_monthly_rent_eur * 12                         AS annual_rent,
    ROUND(100.0 * (r.avg_monthly_rent_eur - n.nat_rent) / n.nat_rent, 1)
                                                        AS pct_vs_national
FROM fact_rent r
JOIN dim_geography g ON g.geo_key = r.geo_key
CROSS JOIN national n
WHERE g.geo_level = 'County'
ORDER BY r.avg_monthly_rent_eur DESC;
