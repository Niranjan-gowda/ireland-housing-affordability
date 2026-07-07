.PHONY: help db etl full clean

help:
	@echo "make db     - build SQLite DB from committed sample/seed data"
	@echo "make etl    - pull full current data from the CSO API"
	@echo "make full   - pull full data, then build DB from it"
	@echo "make clean  - remove generated data/processed artifacts"

db:
	python3 etl/load_sqlite.py

etl:
	python3 etl/extract_cso.py

full: etl
	python3 etl/load_sqlite.py --full

clean:
	rm -f data/processed/*.db data/processed/rppi_monthly.csv data/processed/rents_quarterly.csv
