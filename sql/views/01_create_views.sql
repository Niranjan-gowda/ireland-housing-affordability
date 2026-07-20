-- ============================================================================
-- Reusable analysis views
-- ----------------------------------------------------------------------------
-- A thin semantic layer over the star schema so analysis queries (and the
-- Power BI model) don't repeat the same dimension joins and YoY self-joins.
-- Portable SQL: runs as-is on SQLite and Postgres. Idempotent (safe to re-run).
--
-- Apply with:  sqlite3 data/processed/affordability.db < sql/views/01_create_views.sql
-- ============================================================================

DROP VIEW IF EXISTS v_rent_yoy;
DROP VIEW IF EXISTS v_rent;
DROP VIEW IF EXISTS v_rppi_yoy;
DROP VIEW IF EXISTS v_rppi;

-- ---------------------------------------------------------------------------
-- v_rppi: flattened price-index fact — one row per month/geography/type.
-- ---------------------------------------------------------------------------
CREATE VIEW v_rppi AS
SELECT
    f.date_key,
    d.full_date,
    d.year,
    d.month,
    d.quarter_label,
    g.geography_name,
    g.geo_level,
    p.property_type,
    f.rppi_index_2015base
FROM fact_rppi f
JOIN dim_date          d ON d.date_key = f.date_key
JOIN dim_geography     g ON g.geo_key  = f.geo_key
JOIN dim_property_type p ON p.pt_key   = f.pt_key;

-- ---------------------------------------------------------------------------
-- v_rppi_yoy: year-over-year % change in the price index.
-- date_key is yyyymmdd, so the same month one year earlier is date_key-10000;
-- that keeps the self-join to plain integer arithmetic (no date functions).
-- LEFT JOIN: the first 12 months of the series have no prior-year comparator
-- and appear with yoy_pct NULL rather than being dropped.
-- ---------------------------------------------------------------------------
CREATE VIEW v_rppi_yoy AS
SELECT
    cur.full_date,
    cur.year,
    cur.month,
    cur.geography_name,
    cur.geo_level,
    cur.property_type,
    cur.rppi_index_2015base,
    prv.rppi_index_2015base AS rppi_prior_year,
    ROUND((cur.rppi_index_2015base - prv.rppi_index_2015base)
          / prv.rppi_index_2015base * 100.0, 1) AS yoy_pct
FROM v_rppi cur
LEFT JOIN v_rppi prv
       ON prv.date_key       = cur.date_key - 10000
      AND prv.geography_name = cur.geography_name
      AND prv.property_type  = cur.property_type;

-- ---------------------------------------------------------------------------
-- v_rent: flattened rent fact with year/quarter parsed from quarter_label
-- ('2025Q3' -> 2025, 3). SUBSTR is available in both SQLite and Postgres.
-- ---------------------------------------------------------------------------
CREATE VIEW v_rent AS
SELECT
    f.quarter_label,
    CAST(SUBSTR(f.quarter_label, 1, 4) AS INTEGER) AS year,
    CAST(SUBSTR(f.quarter_label, 6, 1) AS INTEGER) AS quarter,
    g.geography_name,
    g.geo_level,
    f.property_type,
    f.bedrooms,
    f.avg_monthly_rent_eur
FROM fact_rent f
JOIN dim_geography g ON g.geo_key = f.geo_key;

-- ---------------------------------------------------------------------------
-- v_rent_yoy: year-over-year % change in average rent (same quarter, year-1).
-- The committed seed holds a single quarter (2025Q3), so on the sample DB
-- rent_prior_year/yoy_pct are NULL; both populate after `make full` loads the
-- complete RTB history.
-- ---------------------------------------------------------------------------
CREATE VIEW v_rent_yoy AS
SELECT
    cur.quarter_label,
    cur.year,
    cur.quarter,
    cur.geography_name,
    cur.geo_level,
    cur.property_type,
    cur.bedrooms,
    cur.avg_monthly_rent_eur,
    prv.avg_monthly_rent_eur AS rent_prior_year,
    ROUND((cur.avg_monthly_rent_eur - prv.avg_monthly_rent_eur)
          / prv.avg_monthly_rent_eur * 100.0, 1) AS yoy_pct
FROM v_rent cur
LEFT JOIN v_rent prv
       ON prv.year           = cur.year - 1
      AND prv.quarter        = cur.quarter
      AND prv.geography_name = cur.geography_name
      AND prv.property_type  = cur.property_type
      AND prv.bedrooms       = cur.bedrooms;
