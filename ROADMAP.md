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
- [x] Query: rank counties by 1yr / 5yr rent growth
- [x] Add a `views/` layer with reusable SQL views
- [x] Notebook: exploratory charts (matplotlib) exported to `docs/`

## Week 3 — polish & showcase
- [ ] Build the `.pbix`; export a PDF/screenshots into `powerbi/`
- [ ] Publish an interactive HTML preview to GitHub Pages
- [x] README badges, ERD diagram image
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
- 2026-08-09 — Added `sql/analysis/06_county_rent_growth_ranking.sql`: ranks counties by 1-year rent growth and 5-year CAGR side by side, anchored on each county's latest quarter and comparing like-for-like quarters (Q3-vs-Q3) to avoid seasonality. Portable window/POWER SQL over the views layer. Verified on a fresh sample build: executes cleanly and returns 0 rows as expected (rent seed is a single quarter, 2025Q3 — no prior-year/5yr comparator; populates after `make full`). Proved the 1yr and CAGR arithmetic against a synthetic two-county, multi-year fixture (CountyA 1000→1200→1320: g1 10.0%, 5yr CAGR 5.7%; CountyB 2000→2100→2205: g1 5.0%, 5yr CAGR 2.0%) — SQL output matched the hand-computed figures and ranks exactly. (CPI deflator item and the `make full` local run remain — need real CPI / a local machine.)
- 2026-08-15 — Added `docs/ERD.md`: a Mermaid entity-relationship diagram of the star schema (GitHub renders it as an image natively), plus five status badges on the README and links to the ERD from the architecture and layout sections. Verified the Mermaid source parses cleanly via the mermaid library (diagramType `er`), and cross-checked programmatically that all 21 columns across the 5 tables in the DDL appear in the diagram. Took this Week-3 item out of order: the first two unchecked items remain blocked here — `make full` needs a local internet-connected machine, and the CPI deflator needs a real CPI series (CSO API unreachable from the sandbox; hardcoding remembered CPI values would be fabrication).
- 2026-08-04 — Added `notebooks/exploratory_charts.py` (headless matplotlib, script-style notebook) plus `docs/CHARTS.md`, exporting three PNGs to `docs/charts/`: national RPPI by property type, YoY price growth National/Dublin/rest, and rent by county for the latest quarter. Date-agnostic — renders the sample now and the full history after `make full`. Verified on a fresh sample build: all three charts render (85/76/57 KB); visually checked the YoY chart — Dublin > National > National-excl-Dublin, Dublin peaking above 23% in 2006, consistent with the Celtic Tiger boom. (CPI deflator and county rent-growth items still blocked — need real CPI / full RTB history; `make full` still needs a local run.)
