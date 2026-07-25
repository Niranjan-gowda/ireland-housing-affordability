# Roadmap — daily build log

This project is built in small daily increments so progress is visible and each
commit is reviewable. Checked items are done; the rest are the planned cadence.

## Week 1 — foundation
- [x] Repo scaffold, `.gitignore`, `Makefile`
- [x] Star schema DDL (`sql/schema/01_create_schema.sql`)
- [x] Verified RPPI sample (2005-2006) + RTB 2025Q3 rent seed
- [x] ETL script pulling HPM09 + RIQ02 from the CSO API (`etl/extract_cso.py`)
- [x] SQLite loader (`etl/load_sqlite.py`) — runs out of the box
- [x] Analysis queries: YoY, Dublin-vs-rest, county rent ranking
- [x] Power BI guide (model + DAX + report spec)
- [ ] Run `make full` on a local machine; commit note confirming full pull
- [x] Add data-quality checks (row counts, null rate, index continuity)

## Week 2 — analysis depth
- [ ] Query: real vs nominal — deflate rent with CPI
- [x] Query: price-to-rent ratio by region over time
- [x] Query: rolling 12-month RPPI and rent growth
- [ ] Query: rank counties by 1yr / 5yr rent growth
- [x] Add a `views/` layer with reusable SQL views
- [ ] Notebook: exploratory charts (matplotlib) exported to `docs/`

## Week 3 — polish & showcase
- [ ] Build the `.pbix`; export a PDF/screenshots into `powerbi/`
- [ ] Publish an interactive HTML preview to GitHub Pages
- [ ] README badges, ERD diagram image
- [ ] Short write-up: 3 findings a Dublin renter/buyer would care about
- [ ] Link the project from niranjan-gowda.github.io portfolio

## Ideas backlog
- Eircode-level price map (HPM04/HPM08)
- Mortgage affordability calculator (rate + LTI what-if)
- Compare RPPI against average earnings (CSO earnings series)

## Build log
- 2026-07-13 — Added `etl/data_quality_checks.py`, a stdlib-only DQ gate (row counts, null rate, referential integrity, measure sanity, RPPI month-gap continuity, grain uniqueness). Verified against the sample DB: 29 checks pass, exit 0; confirmed it returns exit 1 on injected orphan rows.
- 2026-07-20 — Added `sql/views/01_create_views.sql`: reusable views layer (v_rppi, v_rppi_yoy, v_rent, v_rent_yoy) with integer-arithmetic YoY self-joins. Verified on a fresh sample build: idempotent, 120/120/9/9 rows, YoY figures hand-checked. (Took the views item out of order: `make full` needs a local run, and the CPI deflator item needs real CPI data — CSO API unreachable from this sandbox, and hardcoding remembered CPI values would be fabrication.)
- 2026-07-20 — Added `sql/analysis/04_rolling_12m_growth.sql`: rolling 12-month RPPI average + annual growth of the smoothed series (window functions, partial-window guard), plus the quarterly rolling-4 rent mirror that populates after `make full`. Verified on a fresh sample build: 72 RPPI rows, rolling avg from month 12, growth for Dec 2006 (14.9% national) hand-checked against a direct recomputation. (CPI deflator item still blocked — CSO API unreachable from sandbox.)
- 2026-07-25 — Added `sql/analysis/05_price_to_rent_ratio.sql`: price-to-rent ratio by region over time (quarterly-averaged RPPI ÷ standardised monthly rent), plus a per-geography index rebased to each region's first common quarter = 100 so the trend is directly readable and cross-region comparable. Portable window SQL over the views layer. Verified on a fresh sample build: executes cleanly and returns 0 rows as expected (the RPPI sample is 2005-06, the rent seed is 2025Q3 — no overlap; populates from 2007Q3 after `make full`). Proved the ratio + rebase arithmetic against a throwaway synthetic-overlap fixture and hand-checked the National figures (125.8/1000 → 100.0; 128.5/1100 → 92.8, i.e. rent outpacing price pulls the ratio below base). (CPI deflator and county rent-growth items remain blocked — need the full RTB history / real CPI.)
