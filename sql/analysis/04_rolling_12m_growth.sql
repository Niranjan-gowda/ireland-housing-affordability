-- Q4. Rolling 12-month growth: smoothed RPPI and rent trends.
-- ----------------------------------------------------------------------------
-- Single-month YoY (Q1) is noisy, so a rolling 12-month average smooths seasonal
-- and sampling noise, so turning points are easier to read. Two measures here:
--   rppi_roll12      - trailing 12-month average of the price index
--   roll12_growth_pct - % change of that average vs. the same average one year
--                       earlier (i.e. annual growth of the smoothed series)
-- Uses window functions (SQLite >= 3.25 and Postgres). Self-contained: joins
-- the star schema directly, no views required.
--
-- Sample-data note: the committed RPPI sample (2005-2006, 24 monthly rows per
-- series) yields rppi_roll12 from month 12 onward and roll12_growth_pct only
-- for the final month (needs 23 prior months). The rent section mirrors the
-- logic at quarterly grain (rolling 4 quarters). The committed seed holds a
-- single quarter (2025Q3), so its rolling columns are NULL until `make full`
-- loads the complete RTB history. No data is fabricated here.

-- ---------------------------------------------------------------------------
-- Part A: national RPPI, rolling 12-month average and its annual growth.
-- COUNT(*) OVER the same frame guards partial windows: the first 11 months
-- have fewer than 12 observations, so the average is suppressed rather than
-- reported from an incomplete window.
-- ---------------------------------------------------------------------------
WITH rppi_flat AS (
    SELECT
        d.full_date,
        d.date_key,
        p.property_type,
        f.rppi_index_2015base AS rppi
    FROM fact_rppi f
    JOIN dim_date          d ON d.date_key = f.date_key
    JOIN dim_property_type p ON p.pt_key   = f.pt_key
    JOIN dim_geography     g ON g.geo_key  = f.geo_key
                            AND g.geography_name = 'National'
),
rolled AS (
    SELECT
        full_date,
        property_type,
        rppi,
        CASE WHEN COUNT(*) OVER w = 12
             THEN AVG(rppi) OVER w
        END AS rppi_roll12
    FROM rppi_flat
    WINDOW w AS (PARTITION BY property_type
                 ORDER BY date_key
                 ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
)
SELECT
    full_date              AS month,
    property_type,
    rppi,
    ROUND(rppi_roll12, 1)  AS rppi_roll12,
    ROUND(100.0 * (rppi_roll12 - LAG(rppi_roll12, 12) OVER (
              PARTITION BY property_type ORDER BY full_date))
          / LAG(rppi_roll12, 12) OVER (
              PARTITION BY property_type ORDER BY full_date), 1)
        AS roll12_growth_pct
FROM rolled
ORDER BY property_type, full_date;

-- ---------------------------------------------------------------------------
-- Part B: county rents, rolling 4-quarter average and its annual growth.
-- Same pattern at quarterly grain. quarter_label sorts correctly as text
-- ('2024Q4' < '2025Q1'), so it can drive the window ORDER BY directly.
-- Returns one row per seed quarter on the sample DB (rolling columns NULL),
-- fully populated after `make full`.
-- ---------------------------------------------------------------------------
WITH rent_flat AS (
    SELECT
        f.quarter_label,
        g.geography_name AS county,
        f.property_type,
        f.bedrooms,
        f.avg_monthly_rent_eur AS rent
    FROM fact_rent f
    JOIN dim_geography g ON g.geo_key = f.geo_key
                        AND g.geo_level = 'County'
    WHERE f.bedrooms = 'All bedrooms'
      AND f.property_type = 'All property types'
),
rolled AS (
    SELECT
        quarter_label,
        county,
        rent,
        CASE WHEN COUNT(*) OVER w = 4
             THEN AVG(rent) OVER w
        END AS rent_roll4
    FROM rent_flat
    WINDOW w AS (PARTITION BY county
                 ORDER BY quarter_label
                 ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
)
SELECT
    quarter_label,
    county,
    ROUND(rent, 0)       AS avg_rent_eur,
    ROUND(rent_roll4, 0) AS rent_roll4_eur,
    ROUND(100.0 * (rent_roll4 - LAG(rent_roll4, 4) OVER (
              PARTITION BY county ORDER BY quarter_label))
          / LAG(rent_roll4, 4) OVER (
              PARTITION BY county ORDER BY quarter_label), 1)
        AS roll4_growth_pct
FROM rolled
ORDER BY county, quarter_label;
