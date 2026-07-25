-- Q5. Price-to-rent ratio by region over time.
-- ----------------------------------------------------------------------------
-- The price-to-rent ratio is the classic gauge of whether buying is getting
-- expensive *relative to* renting. When it climbs, house prices are outpacing
-- rents (buying looks dear vs. renting); when it falls, the reverse. OECD and
-- the Central Bank track a version of this to flag potential over/undervaluation.
--
-- Grain here: one row per (quarter, geography). The price side (RPPI) is monthly
-- and the rent side (RTB) is quarterly, so RPPI is first averaged to a quarter to
-- put both on the same footing. We then join on geography_name + quarter_label.
--
-- Two measures are returned:
--   pr_ratio_raw       - quarterly RPPI index divided by average monthly rent.
--                        Units are "index points per euro of monthly rent", so
--                        the level is only meaningful *within* one geography over
--                        time, not for cross-geography comparison (the RPPI is an
--                        index, not a price level).
--   pr_index_rebased   - pr_ratio_raw rebased so each geography's first common
--                        quarter = 100. This strips out the arbitrary units and
--                        makes the *trend* directly readable and comparable across
--                        regions: 110 means price-to-rent is 10% above where it
--                        started for that region.
--
-- Portable SQL: FIRST_VALUE / window functions run on SQLite (>= 3.25) and
-- Postgres. Reads the reusable views, so apply sql/views/01_create_views.sql
-- first:  sqlite3 data/processed/affordability.db < sql/views/01_create_views.sql
--
-- Sample-data note: the committed RPPI sample is National, 2005-2006; the
-- committed rent seed is a single quarter, 2025Q3. They do not overlap in time,
-- so on the sample DB this query executes cleanly but returns 0 rows. It
-- populates for every geography where price and rent share a quarter once
-- `make full` loads the complete CSO RPPI (HPM09) and RTB (RIQ02) histories,
-- which overlap from the RTB series start (2007Q3) onward. No data is fabricated.

WITH rppi_q AS (
    -- Collapse monthly RPPI to a quarterly average per geography.
    -- 'All residential properties' is the headline series matched to the
    -- standardised all-property rent.
    SELECT
        geography_name,
        geo_level,
        quarter_label,
        AVG(rppi_index_2015base) AS rppi_q_index
    FROM v_rppi
    WHERE property_type = 'All residential properties'
    GROUP BY geography_name, geo_level, quarter_label
),
rent_q AS (
    -- Standardised all-property, all-bedroom rent, one row per geography/quarter.
    SELECT
        geography_name,
        quarter_label,
        avg_monthly_rent_eur
    FROM v_rent
    WHERE property_type = 'All property types'
      AND bedrooms      = 'All bedrooms'
),
joined AS (
    -- Only quarters where BOTH a price and a rent observation exist for the
    -- geography survive the inner join.
    SELECT
        p.geography_name,
        p.geo_level,
        p.quarter_label,
        p.rppi_q_index,
        r.avg_monthly_rent_eur,
        p.rppi_q_index / r.avg_monthly_rent_eur AS pr_ratio_raw
    FROM rppi_q p
    JOIN rent_q r
      ON r.geography_name = p.geography_name
     AND r.quarter_label  = p.quarter_label
)
SELECT
    geography_name,
    geo_level,
    quarter_label,
    ROUND(rppi_q_index, 1)        AS rppi_q_index,
    ROUND(avg_monthly_rent_eur, 0) AS avg_monthly_rent_eur,
    ROUND(pr_ratio_raw, 4)         AS pr_ratio_raw,
    -- Rebase each geography's series to its earliest common quarter = 100.
    -- quarter_label ('2007Q3' < '2007Q4' < '2008Q1') sorts chronologically as
    -- text within a century, so it drives the ORDER BY directly and the first
    -- value is the earliest common quarter. The index then reads as a clean trend.
    ROUND(
        100.0 * pr_ratio_raw
        / FIRST_VALUE(pr_ratio_raw) OVER (
              PARTITION BY geography_name
              ORDER BY quarter_label
              ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING),
        1) AS pr_index_rebased
FROM joined
ORDER BY geography_name, quarter_label;
