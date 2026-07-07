# Ireland Housing Affordability — SQL + Power BI

An end-to-end analytics project on Irish housing costs, built around the two
skills most requested in Dublin Business Analyst / Data Analyst job ads:
**SQL** and **Power BI**. It combines house-price and rent data into a single
affordability story, from raw open-data extraction through a dimensional model
to a Power BI dashboard.

**Skills demonstrated:** SQL (star schema, window functions, self-joins, CTEs) ·
Power BI (data model, DAX, what-if analysis) · Python ETL (JSON-stat parsing) ·
data modelling · working with official open data.

## The question
How affordable is Irish housing, and how does it vary by region and county?
The project tracks the residential property price index over time (boom, crash,
recovery) alongside standardised rents by county, and derives affordability
signals (year-on-year growth, Dublin premium, rent-to-income).

## Data sources
- **CSO HPM09** — Residential Property Price Index (RPPI), monthly, base 2015 = 100
  (Central Statistics Office, PxStat open API).
- **CSO RIQ02 / RTB-ESRI Rent Index** — standardised average monthly rent by
  county and property type.

Small **verified** extracts are committed so the repo runs immediately; the ETL
script pulls the full current series from the live CSO API.

## Architecture

```
CSO PxStat API ──▶ etl/extract_cso.py ──▶ data/processed/*.csv
                                              │
data/sample + data/seed  ─────────────────────┤
                                              ▼
                        etl/load_sqlite.py ──▶ affordability.db (star schema)
                                              ▼
                        sql/analysis/*.sql   +   Power BI (powerbi/POWER_BI_GUIDE.md)
```

Star schema: `fact_rppi` (month × geography × property type) and `fact_rent`
(quarter × county) share conformed dimensions `dim_date`, `dim_geography`,
`dim_property_type`, so one slicer filters both price and rent visuals. See
[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

## Quick start

```bash
python3 etl/load_sqlite.py                 # build affordability.db from committed data
sqlite3 data/processed/affordability.db < sql/analysis/03_rent_ranking_affordability.sql

# full current data (run on a normal internet connection):
make full                                  # pull from CSO API, then rebuild the DB
```

No external Python packages required — the ETL and loader use the standard
library only.

## Sample findings (committed data)
- **Dublin is the most expensive county to rent**: €2,173/month in 2025Q3,
  **+64% above the €1,325 national average** — matching the RTB's own headline.
- Cheapest counties: Donegal (€994), Leitrim (€997), Monaghan (€1,031).
- National house prices rose **~14% year-on-year through 2006**, the tail of the
  Celtic-Tiger boom, before the 2007-08 downturn visible in the series.

## Repository layout
```
etl/            extract_cso.py (API pull), load_sqlite.py (build DB)
sql/schema/     star-schema DDL
sql/analysis/   analytical queries (YoY, Dublin gap, rent ranking)
data/sample/    verified RPPI sample (2005-2006)
data/seed/      verified RTB rents (2025Q3)
powerbi/        POWER_BI_GUIDE.md — model, DAX, report spec
docs/           data dictionary
ROADMAP.md      daily build log
```

## Roadmap
Built in small daily increments — see [ROADMAP.md](ROADMAP.md).

---
*Data © Central Statistics Office Ireland and the Residential Tenancies Board,
reused under their open-data terms. Author: Niranjan Chikkegowda.*
