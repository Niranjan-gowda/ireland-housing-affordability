-- ============================================================================
-- Ireland Housing Affordability - star schema
-- ----------------------------------------------------------------------------
-- Portable SQL. Runs as-is on SQLite; notes mark the few Postgres differences.
-- Grain:
--   fact_rppi  : one row per (month, geography, property type)  - price index
--   fact_rent  : one row per (quarter, county, property type, bedrooms) - rent
-- Shared conformed dimensions: dim_date, dim_geography, dim_property_type.
-- ============================================================================

DROP VIEW  IF EXISTS v_affordability_latest;
DROP TABLE IF EXISTS fact_rppi;
DROP TABLE IF EXISTS fact_rent;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_geography;
DROP TABLE IF EXISTS dim_property_type;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,   -- yyyymmdd, e.g. 20050101
    full_date   TEXT NOT NULL,         -- ISO 'YYYY-MM-DD'
    year        INTEGER NOT NULL,
    month       INTEGER,               -- 1-12 (NULL for quarter-only rows)
    month_name  TEXT,
    quarter     INTEGER NOT NULL,      -- 1-4
    quarter_label TEXT NOT NULL        -- e.g. '2005Q1'
);

CREATE TABLE dim_geography (
    geo_key       INTEGER PRIMARY KEY, -- Postgres: GENERATED ALWAYS AS IDENTITY
    geography_name TEXT NOT NULL UNIQUE,
    geo_level      TEXT NOT NULL        -- 'National' | 'Region' | 'County'
);

CREATE TABLE dim_property_type (
    pt_key        INTEGER PRIMARY KEY,
    property_type TEXT NOT NULL UNIQUE  -- 'All residential properties' | 'Houses' | 'Apartments'
);

-- --------------------------------------------------------------------- facts
CREATE TABLE fact_rppi (
    date_key            INTEGER NOT NULL REFERENCES dim_date(date_key),
    geo_key             INTEGER NOT NULL REFERENCES dim_geography(geo_key),
    pt_key              INTEGER NOT NULL REFERENCES dim_property_type(pt_key),
    rppi_index_2015base REAL    NOT NULL,
    PRIMARY KEY (date_key, geo_key, pt_key)
);

CREATE TABLE fact_rent (
    quarter_label            TEXT    NOT NULL,
    geo_key                  INTEGER NOT NULL REFERENCES dim_geography(geo_key),
    property_type            TEXT    NOT NULL,
    bedrooms                 TEXT    NOT NULL,
    avg_monthly_rent_eur     REAL    NOT NULL,
    PRIMARY KEY (quarter_label, geo_key, property_type, bedrooms)
);

CREATE INDEX ix_rppi_geo  ON fact_rppi(geo_key);
CREATE INDEX ix_rent_geo  ON fact_rent(geo_key);
