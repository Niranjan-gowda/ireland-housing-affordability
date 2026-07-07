# Power BI build guide

This project ships the data model, the DAX, and the dashboard spec so the
`.pbix` can be rebuilt in ~30 minutes. Power BI Desktop is Windows-only, so the
binary `.pbix` is not committed; follow the steps below to produce it.

## 1. Get the data in

Run the ETL first so you have the full series, then point Power BI at the CSVs:

```bash
python etl/extract_cso.py          # -> data/processed/rppi_monthly.csv, rents_quarterly.csv
python etl/load_sqlite.py --full   # optional: also build affordability.db
```

In Power BI Desktop: **Home → Get data → Text/CSV** and load
`data/processed/rppi_monthly.csv` and `data/processed/rents_quarterly.csv`
(or connect to `affordability.db` with the SQLite ODBC driver to import the
star schema directly).

## 2. Model (star schema)

Recreate the same star used by the SQL layer. In **Model view** create these
tables and relationships (all one-to-many, single direction, from dim to fact):

| From (dimension)        | To (fact)   | Key                 |
|-------------------------|-------------|---------------------|
| `dim_date[date_key]`    | `fact_rppi` | `date_key`          |
| `dim_geography[geo_key]`| `fact_rppi` | `geo_key`           |
| `dim_property_type`     | `fact_rppi` | `pt_key`            |
| `dim_geography[geo_key]`| `fact_rent` | `geo_key`           |

Mark `dim_date` as the official date table (**Table tools → Mark as date
table**). `dim_geography` is the conformed dimension shared by both facts, so a
county/region slicer filters price and rent visuals together.

## 3. DAX measures

Create a dedicated `_Measures` table (**Enter data**, one blank column) and add:

```dax
RPPI = AVERAGE ( fact_rppi[rppi_index_2015base] )

RPPI YoY % =
VAR Curr = [RPPI]
VAR Prior =
    CALCULATE ( [RPPI], DATEADD ( dim_date[full_date], -1, YEAR ) )
RETURN
    DIVIDE ( Curr - Prior, Prior )

RPPI vs 2015 base =
DIVIDE ( [RPPI], 100 ) - 1        -- index is base 2015 = 100

Avg Monthly Rent = AVERAGE ( fact_rent[avg_monthly_rent_eur] )

Annual Rent = [Avg Monthly Rent] * 12

National Rent =
CALCULATE (
    [Avg Monthly Rent],
    FILTER ( ALL ( dim_geography ), dim_geography[geo_level] = "National" )
)

Rent Premium vs National % =
DIVIDE ( [Avg Monthly Rent] - [National Rent], [National Rent] )

-- Affordability proxy: rent as a share of a user-set gross salary.
-- Add a what-if parameter "Gross Salary" (Modeling -> New parameter), then:
Rent-to-Income % =
DIVIDE ( [Annual Rent], SELECTEDVALUE ( 'Gross Salary'[Gross Salary Value] ) )
```

Format `RPPI YoY %`, `Rent Premium vs National %`, and `Rent-to-Income %` as
percentages; `Avg Monthly Rent` / `Annual Rent` as whole euro (`€#,0`).

## 4. Report pages

**Page 1 — Market overview**
- KPI cards: `RPPI`, `RPPI YoY %`, `Avg Monthly Rent`, `Rent Premium vs National %`.
- Line chart: `RPPI` by `dim_date[full_date]`, legend `property_type` — the
  2005-2008 boom, the crash, and recovery.
- Slicers: `geo_level` / `geography_name` and `property_type`.

**Page 2 — Dublin vs the rest**
- Line chart: `RPPI` by month with `geography_name` in {Dublin, National
  excluding Dublin} to show the price gap.
- Card: latest `dublin_gap` (replicates `sql/analysis/02_dublin_vs_rest.sql`).

**Page 3 — Rent affordability**
- Map or bar chart: `Avg Monthly Rent` by county (filled map on `geography_name`).
- Table: county, `Avg Monthly Rent`, `Annual Rent`, `Rent Premium vs National %`
  (replicates `sql/analysis/03_rent_ranking_affordability.sql`).
- What-if slicer `Gross Salary` driving `Rent-to-Income %`.

## 5. Publish
Save as `powerbi/ireland_housing_affordability.pbix`. To share a public preview,
File → Export → PDF (commit the PDF), or publish to the Power BI Service and add
the link to the README and your portfolio.
