#!/usr/bin/env python3
"""
data_quality_checks.py
----------------------
Lightweight, dependency-free data-quality gate for the affordability database.
Run it after building the DB (`python3 etl/load_sqlite.py`) to confirm the load
is sane before doing analysis or refreshing Power BI.

It runs four families of checks:
  1. Row counts     - every dimension and fact table has rows.
  2. Null rate      - key columns and measures are populated (0 % nulls expected).
  3. Referential    - no fact row points at a missing dimension key.
  4. Index continuity - fact_rppi has no month gaps within each
                        (geography, property_type) series, and no duplicate keys.

Only the Python standard library is used, so it runs anywhere the loader does.

Usage:
    python3 etl/data_quality_checks.py                 # uses default DB path
    python3 etl/data_quality_checks.py --db path.db    # custom DB

Exit code is 0 if all checks pass, 1 if any check FAILs (handy for CI / make).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DEFAULT_DB = os.path.join(ROOT, "data", "processed", "affordability.db")

# Columns that must never be NULL: table -> list of columns to null-check.
NOT_NULL_COLUMNS = {
    "dim_date": ["full_date", "year", "quarter", "quarter_label"],
    "dim_geography": ["geography_name", "geo_level"],
    "dim_property_type": ["property_type"],
    "fact_rppi": ["date_key", "geo_key", "pt_key", "rppi_index_2015base"],
    "fact_rent": ["quarter_label", "geo_key", "property_type", "bedrooms",
                  "avg_monthly_rent_eur"],
}

# Fact -> (fact_fk_column, dim_table, dim_pk_column) for referential checks.
REFERENTIAL = [
    ("fact_rppi", "date_key", "dim_date", "date_key"),
    ("fact_rppi", "geo_key", "dim_geography", "geo_key"),
    ("fact_rppi", "pt_key", "dim_property_type", "pt_key"),
    ("fact_rent", "geo_key", "dim_geography", "geo_key"),
]


class Report:
    """Collects pass/fail results and prints a readable summary."""

    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append((name, passed, detail))

    def all_passed(self) -> bool:
        return all(p for _, p, _ in self.results)

    def render(self) -> str:
        lines = ["Data-quality report", "=" * 60]
        for name, passed, detail in self.results:
            tag = "PASS" if passed else "FAIL"
            line = f"[{tag}] {name}"
            if detail:
                line += f"  -- {detail}"
            lines.append(line)
        lines.append("=" * 60)
        n_fail = sum(1 for _, p, _ in self.results if not p)
        summary = "ALL CHECKS PASSED" if n_fail == 0 else f"{n_fail} CHECK(S) FAILED"
        lines.append(summary)
        return "\n".join(lines)


def check_row_counts(cur, rep: Report) -> None:
    for table in NOT_NULL_COLUMNS:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        rep.check(f"row count: {table}", n > 0, f"{n} rows")


def check_nulls(cur, rep: Report) -> None:
    for table, cols in NOT_NULL_COLUMNS.items():
        for col in cols:
            n_null = cur.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"
            ).fetchone()[0]
            total = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            rate = (n_null / total * 100) if total else 0.0
            rep.check(f"null rate: {table}.{col}", n_null == 0,
                      f"{n_null}/{total} null ({rate:.1f}%)")


def check_referential(cur, rep: Report) -> None:
    for fact, fk, dim, pk in REFERENTIAL:
        n_orphan = cur.execute(
            f"SELECT COUNT(*) FROM {fact} f "
            f"LEFT JOIN {dim} d ON f.{fk} = d.{pk} "
            f"WHERE d.{pk} IS NULL"
        ).fetchone()[0]
        rep.check(f"referential: {fact}.{fk} -> {dim}.{pk}",
                  n_orphan == 0, f"{n_orphan} orphan rows")


def check_measure_sanity(cur, rep: Report) -> None:
    n = cur.execute(
        "SELECT COUNT(*) FROM fact_rppi WHERE rppi_index_2015base <= 0"
    ).fetchone()[0]
    rep.check("measure sanity: fact_rppi index > 0", n == 0,
              f"{n} non-positive index values")
    n = cur.execute(
        "SELECT COUNT(*) FROM fact_rent WHERE avg_monthly_rent_eur <= 0"
    ).fetchone()[0]
    rep.check("measure sanity: fact_rent rent > 0", n == 0,
              f"{n} non-positive rent values")


def check_index_continuity(cur, rep: Report) -> None:
    """No month gaps within each (geography, property_type) RPPI series."""
    rows = cur.execute(
        "SELECT f.geo_key, f.pt_key, d.year, d.month "
        "FROM fact_rppi f JOIN dim_date d ON f.date_key = d.date_key "
        "WHERE d.month IS NOT NULL "
        "ORDER BY f.geo_key, f.pt_key, d.year, d.month"
    ).fetchall()

    series: dict[tuple[int, int], list[int]] = {}
    for geo_key, pt_key, year, month in rows:
        series.setdefault((geo_key, pt_key), []).append(year * 12 + (month - 1))

    gaps: list[str] = []
    for (geo_key, pt_key), months in series.items():
        for prev, cur_m in zip(months, months[1:]):
            if cur_m - prev != 1:
                missing = cur_m - prev - 1
                gaps.append(f"geo={geo_key} pt={pt_key} ({missing} month gap)")

    rep.check("index continuity: no month gaps in fact_rppi",
              not gaps,
              "; ".join(gaps) if gaps else f"{len(series)} contiguous series")


def check_duplicate_keys(cur, rep: Report) -> None:
    dup = cur.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT date_key, geo_key, pt_key FROM fact_rppi "
        "  GROUP BY date_key, geo_key, pt_key HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    rep.check("uniqueness: fact_rppi grain", dup == 0,
              f"{dup} duplicated (date, geo, pt) keys")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run data-quality checks on the DB.")
    ap.add_argument("--db", default=DEFAULT_DB, help="path to affordability.db")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"ERROR: database not found at {args.db}\n"
              f"Build it first with: python3 etl/load_sqlite.py", file=sys.stderr)
        return 2

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    rep = Report()

    check_row_counts(cur, rep)
    check_nulls(cur, rep)
    check_referential(cur, rep)
    check_measure_sanity(cur, rep)
    check_index_continuity(cur, rep)
    check_duplicate_keys(cur, rep)

    con.close()
    print(rep.render())
    return 0 if rep.all_passed() else 1


if __name__ == "__main__":
    raise SystemExit(main())
