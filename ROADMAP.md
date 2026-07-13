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
- [ ] Query: price-to-rent ratio by region over time
- [ ] Query: rolling 12-month RPPI and rent growth
- [ ] Query: rank counties by 1yr / 5yr rent growth
- [ ] Add a `views/` layer with reusable SQL views
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
- 2026-07-13 — Added `etl/data_quality_checks.py`, a stdlib-only DQ gate (row counts, null rate, referential integrity, measure sanity, RPPI month-gap continuity, grain uniqueness). Verified against the sample DB: 30 checks pass, exit 0; confirmed it returns exit 1 on injected orphan rows.
