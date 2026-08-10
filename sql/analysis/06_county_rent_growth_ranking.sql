-- Q6. Rank counties by 1-year and 5-year rent growth.
-- ----------------------------------------------------------------------------
-- Which counties have seen rents rise fastest? Two horizons are returned side
-- by side so the short-term move and the medium-term trend can be compared:
--   g1_pct  - growth vs the SAME quarter one year earlier   (1yr)
--   g5_cagr - compound annual growth rate over five years    (5yr, annualised)
-- The 5-year figure is expressed as a CAGR (not a raw 5yr %) so it is directly
-- comparable to the 1-year growth rate rather than being ~5x larger.
--
-- Grain: one row per county, anchored on the latest quarter present for that
-- county. Comparing like-for-like quarters (Q3 vs Q3) sidesteps the seasonal
-- pattern in the RTB rent series, so no separate seasonal adjustment is needed.
--
-- Portable SQL: reads the reusable views, so apply the views layer first:
--   sqlite3 data/processed/affordability.db < sql/views/01_create_views.sql
-- Uses only aggregation, self-joins on (year, quarter) and POWER()/exponent
-- arithmetic that runs on both SQLite (>= 3.25) and Postgres.
--
-- Sample-data note: the committed rent seed is a single quarter (2025Q3), so
-- there is no prior-year or 5-year-ago comparator and this query returns 0 rows
-- on the sample DB. It populates once `make full` loads the complete RTB
-- history. The arithmetic was verified separately against a synthetic
-- multi-year fixture (see the project build log).
-- ============================================================================

-- County-level average rent per quarter. The RTB seed is one standardised value
-- per county per quarter, but averaging keeps this correct even if the full pull
-- carries property-type / bedroom splits under the county grain.
WITH county_q AS (
    SELECT
        geography_name                 AS county,
        year,
        quarter,
        AVG(avg_monthly_rent_eur)      AS avg_rent
    FROM v_rent
    WHERE geo_level = 'County'
    GROUP BY geography_name, year, quarter
),

-- The most recent quarter each county appears in (its anchor point).
latest AS (
    SELECT county, year AS y, quarter AS q
    FROM (
        SELECT county, year, quarter,
               ROW_NUMBER() OVER (
                   PARTITION BY county
                   ORDER BY year DESC, quarter DESC
               ) AS rn
        FROM county_q
    ) t
    WHERE rn = 1
)

SELECT
    cur.county,
    printf('%dQ%d', l.y, l.q)                       AS latest_quarter,
    ROUND(cur.avg_rent, 0)                           AS rent_now,
    ROUND(p1.avg_rent, 0)                            AS rent_1yr_ago,
    ROUND(p5.avg_rent, 0)                            AS rent_5yr_ago,
    -- 1-year growth (%)
    ROUND(100.0 * (cur.avg_rent - p1.avg_rent) / p1.avg_rent, 1) AS g1_pct,
    RANK() OVER (ORDER BY (cur.avg_rent - p1.avg_rent) / p1.avg_rent DESC)
                                                     AS g1_rank,
    -- 5-year compound annual growth rate (%)
    ROUND(100.0 * (POWER(cur.avg_rent / p5.avg_rent, 1.0 / 5.0) - 1.0), 1)
                                                     AS g5_cagr,
    RANK() OVER (ORDER BY cur.avg_rent / p5.avg_rent DESC)
                                                     AS g5_rank
FROM county_q cur
JOIN latest    l  ON l.county = cur.county
                 AND cur.year = l.y AND cur.quarter = l.q
-- same quarter, one year earlier
JOIN county_q  p1 ON p1.county = cur.county
                 AND p1.year = l.y - 1 AND p1.quarter = l.q
-- same quarter, five years earlier
JOIN county_q  p5 ON p5.county = cur.county
                 AND p5.year = l.y - 5 AND p5.quarter = l.q
ORDER BY g1_pct DESC;
