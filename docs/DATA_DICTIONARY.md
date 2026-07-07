# Data dictionary

## Sources
- **CSO HPM09** — Residential Property Price Index (RPPI), monthly, base 2015 = 100,
  by region and property type. Central Statistics Office, PxStat open API.
- **CSO RIQ02 / RIA02** — RTB Average Monthly Rent Report, standardised average
  monthly rent by location, property type and number of bedrooms.
- **RTB/ESRI Rent Index** — quarterly standardised rent figures (used for the
  committed 2025Q3 seed).

## Tables

### dim_date
| column | type | notes |
|--------|------|-------|
| date_key | INTEGER PK | yyyymmdd, e.g. 20050101 |
| full_date | TEXT | ISO date |
| year, month, quarter | INTEGER | month NULL for quarter-only rows |
| month_name | TEXT | January … December |
| quarter_label | TEXT | e.g. 2005Q1 |

### dim_geography
| column | type | notes |
|--------|------|-------|
| geo_key | INTEGER PK | surrogate |
| geography_name | TEXT UNIQUE | e.g. Dublin, Cork, National |
| geo_level | TEXT | National / Region / County |

### dim_property_type
| column | type | notes |
|--------|------|-------|
| pt_key | INTEGER PK | surrogate |
| property_type | TEXT UNIQUE | All residential properties / Houses / Apartments |

### fact_rppi (grain: month × geography × property type)
| column | type | notes |
|--------|------|-------|
| date_key, geo_key, pt_key | INTEGER FK | composite PK |
| rppi_index_2015base | REAL | index, base 2015 = 100 |

### fact_rent (grain: quarter × county × property type × bedrooms)
| column | type | notes |
|--------|------|-------|
| quarter_label | TEXT | e.g. 2025Q3 |
| geo_key | INTEGER FK | county / national |
| property_type, bedrooms | TEXT | 'All property types' / 'All bedrooms' in the seed |
| avg_monthly_rent_eur | REAL | standardised average monthly rent, € |

## Committed data vs full data
`data/sample/` and `data/seed/` hold small **verified** extracts so the repo runs
out of the box. `etl/extract_cso.py` pulls the **full current** series into
`data/processed/` (gitignored) from the live CSO API.
