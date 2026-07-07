#!/usr/bin/env python3
"""
load_sqlite.py
--------------
Build a ready-to-query SQLite database from the CSV data in this repo and the
star-schema DDL in sql/schema/01_create_schema.sql.

By default it loads the small committed *sample/seed* files so the project runs
out of the box with `python etl/load_sqlite.py`. If you have run
`etl/extract_cso.py` first, pass --full to load the complete processed files
(data/processed/rppi_monthly.csv and rents_quarterly.csv) instead.

Output: data/processed/affordability.db
"""

from __future__ import annotations
import argparse
import csv
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DB = os.path.join(ROOT, "data", "processed", "affordability.db")
SCHEMA = os.path.join(ROOT, "sql", "schema", "01_create_schema.sql")

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def geo_level(name: str) -> str:
    if name in ("National", "State (national average)", "State", "National average"):
        return "National"
    # 'Dublin' is a NUTS3 region on the price side but an administrative county
    # on the rent side; treat it as a County so it appears in county rankings.
    if name in ("National excluding Dublin", "Border", "Midland", "West",
                "Mid-East", "Mid-West", "South-East", "South-West"):
        return "Region"
    return "County"


def upsert_geo(cur, cache, name):
    if name not in cache:
        cur.execute("INSERT INTO dim_geography(geography_name, geo_level) VALUES (?,?)",
                    (name, geo_level(name)))
        cache[name] = cur.lastrowid
    return cache[name]


def upsert_pt(cur, cache, name):
    if name not in cache:
        cur.execute("INSERT INTO dim_property_type(property_type) VALUES (?)", (name,))
        cache[name] = cur.lastrowid
    return cache[name]


def upsert_date(cur, seen, iso_date):
    y, m, d = (int(x) for x in iso_date.split("-"))
    key = y * 10000 + m * 100 + d
    if key not in seen:
        q = (m - 1) // 3 + 1
        cur.execute(
            "INSERT INTO dim_date(date_key, full_date, year, month, month_name, quarter, quarter_label)"
            " VALUES (?,?,?,?,?,?,?)",
            (key, iso_date, y, m, MONTHS[m - 1], q, f"{y}Q{q}"))
        seen.add(key)
    return key


def load_rppi(cur, path, geo_cache, pt_cache, date_seen):
    with open(path, newline="") as f:
        n = 0
        for row in csv.DictReader(f):
            dk = upsert_date(cur, date_seen, row["period_date"])
            gk = upsert_geo(cur, geo_cache, row["geography"])
            pk = upsert_pt(cur, pt_cache, row["property_type"])
            cur.execute(
                "INSERT OR REPLACE INTO fact_rppi(date_key, geo_key, pt_key, rppi_index_2015base)"
                " VALUES (?,?,?,?)", (dk, gk, pk, float(row["rppi_index_2015base"])))
            n += 1
    return n


def load_rents(cur, path, geo_cache):
    with open(path, newline="") as f:
        n = 0
        for row in csv.DictReader(f):
            gk = upsert_geo(cur, geo_cache, row["county"])
            cur.execute(
                "INSERT OR REPLACE INTO fact_rent(quarter_label, geo_key, property_type, bedrooms, avg_monthly_rent_eur)"
                " VALUES (?,?,?,?,?)",
                (row["quarter"], gk, "All property types", "All bedrooms",
                 float(row["standardised_avg_monthly_rent_eur"])))
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="load data/processed/*.csv from extract_cso.py instead of samples")
    args = ap.parse_args()

    rppi_path = (os.path.join(ROOT, "data", "processed", "rppi_monthly.csv") if args.full
                 else os.path.join(ROOT, "data", "sample", "rppi_national_2005_2006.csv"))
    rent_path = os.path.join(ROOT, "data", "seed", "rtb_rent_2025q3_by_county.csv")

    os.makedirs(os.path.dirname(DB), exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()
    with open(SCHEMA) as f:
        cur.executescript(f.read())

    geo_cache, pt_cache, date_seen = {}, {}, set()
    n_rppi = load_rppi(cur, rppi_path, geo_cache, pt_cache, date_seen)
    n_rent = load_rents(cur, rent_path, geo_cache)
    con.commit()
    con.close()
    print(f"Built {os.path.relpath(DB)}: {n_rppi} RPPI rows, {n_rent} rent rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
