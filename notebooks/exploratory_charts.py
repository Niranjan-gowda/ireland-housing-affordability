#!/usr/bin/env python3
"""
Exploratory charts — Irish housing affordability
================================================

A lightweight, script-style "notebook": each block below is a self-contained
cell you could paste into Jupyter, but kept as a plain .py so it is portable,
diff-friendly, and runs headless in CI.

It reads the star schema in ``data/processed/affordability.db`` (build it first
with ``python3 etl/load_sqlite.py``), applies the reusable views layer, and
exports PNG charts to ``docs/charts/``.

With only the shipped sample (RPPI 2005-2006 + one RTB rent seed for 2025Q3),
the price charts cover 2005-2006 and the rent chart is a single-quarter
snapshot. After ``make full`` the same script renders the entire history with
no changes — the queries are date-agnostic.

Dependencies: matplotlib (stdlib otherwise). Run:
    python3 notebooks/exploratory_charts.py
"""

import os
import sqlite3

import matplotlib

matplotlib.use("Agg")  # headless: never needs a display
import matplotlib.pyplot as plt  # noqa: E402

# ---------------------------------------------------------------------------
# Paths (resolved relative to the repo root, so it runs from anywhere)
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB_PATH = os.path.join(ROOT, "data", "processed", "affordability.db")
VIEWS_SQL = os.path.join(ROOT, "sql", "views", "01_create_views.sql")
OUT_DIR = os.path.join(ROOT, "docs", "charts")


def connect():
    if not os.path.exists(DB_PATH):
        raise SystemExit(
            f"Database not found at {DB_PATH}.\n"
            "Build it first:  python3 etl/load_sqlite.py"
        )
    conn = sqlite3.connect(DB_PATH)
    # Apply the views layer (idempotent) so the script is self-contained.
    if os.path.exists(VIEWS_SQL):
        with open(VIEWS_SQL) as fh:
            conn.executescript(fh.read())
    return conn


def save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(path, ROOT)}")
    return path


# ---------------------------------------------------------------------------
# Cell 1 — National RPPI index over time, by property type
# ---------------------------------------------------------------------------
def chart_rppi_by_type(conn):
    rows = conn.execute(
        """
        SELECT full_date, property_type, rppi_index_2015base
        FROM v_rppi
        WHERE geography_name = 'National'
        ORDER BY property_type, date_key
        """
    ).fetchall()
    if not rows:
        print("  [skip] no RPPI rows")
        return None

    series = {}
    for full_date, ptype, idx in rows:
        series.setdefault(ptype, ([], []))
        series[ptype][0].append(full_date)
        series[ptype][1].append(idx)

    fig, ax = plt.subplots(figsize=(9, 5))
    for ptype, (dates, vals) in sorted(series.items()):
        ax.plot(dates, vals, marker="o", markersize=3, linewidth=1.5, label=ptype)
    ax.set_title("National Residential Property Price Index (2015 = 100)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Index (2015 base)")
    ax.legend(title="Property type")
    ax.grid(True, alpha=0.3)
    _thin_xticks(ax)
    return save(fig, "chart_01_rppi_national_by_type.png")


# ---------------------------------------------------------------------------
# Cell 2 — Year-on-year RPPI growth, National vs Dublin vs rest
# ---------------------------------------------------------------------------
def chart_rppi_yoy_by_region(conn):
    rows = conn.execute(
        """
        SELECT full_date, geography_name, yoy_pct
        FROM v_rppi_yoy
        WHERE property_type = 'All residential properties'
          AND yoy_pct IS NOT NULL
        ORDER BY geography_name, full_date
        """
    ).fetchall()
    if not rows:
        print("  [skip] no YoY rows yet (needs 13+ months of history)")
        return None

    series = {}
    for full_date, geo, yoy in rows:
        series.setdefault(geo, ([], []))
        series[geo][0].append(full_date)
        series[geo][1].append(yoy)

    fig, ax = plt.subplots(figsize=(9, 5))
    for geo, (dates, vals) in sorted(series.items()):
        ax.plot(dates, vals, marker="o", markersize=3, linewidth=1.5, label=geo)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("RPPI year-on-year growth — all residential properties")
    ax.set_xlabel("Month")
    ax.set_ylabel("YoY change (%)")
    ax.legend(title="Geography")
    ax.grid(True, alpha=0.3)
    _thin_xticks(ax)
    return save(fig, "chart_02_rppi_yoy_by_region.png")


# ---------------------------------------------------------------------------
# Cell 3 — Average monthly rent by county (latest quarter)
# ---------------------------------------------------------------------------
def chart_rent_by_county(conn):
    latest = conn.execute("SELECT MAX(quarter_label) FROM v_rent").fetchone()[0]
    if not latest:
        print("  [skip] no rent rows")
        return None
    rows = conn.execute(
        """
        SELECT geography_name, avg_monthly_rent_eur
        FROM v_rent
        WHERE quarter_label = ?
          AND geo_level = 'County'
          AND bedrooms = 'All bedrooms'
        ORDER BY avg_monthly_rent_eur
        """,
        (latest,),
    ).fetchall()
    if not rows:
        print("  [skip] no county rent rows")
        return None

    national = conn.execute(
        """
        SELECT avg_monthly_rent_eur FROM v_rent
        WHERE quarter_label = ? AND geo_level = 'National'
          AND bedrooms = 'All bedrooms'
        LIMIT 1
        """,
        (latest,),
    ).fetchone()

    names = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(names, vals, color="#4C72B0")
    if national:
        ax.axvline(
            national[0],
            color="#C44E52",
            linestyle="--",
            linewidth=1.2,
            label=f"National avg €{national[0]:,.0f}",
        )
        ax.legend()
    for y, v in enumerate(vals):
        ax.text(v + 15, y, f"€{v:,.0f}", va="center", fontsize=8)
    ax.set_title(f"Average monthly rent by county — {latest} (RTB)")
    ax.set_xlabel("Average monthly rent (€)")
    ax.grid(True, axis="x", alpha=0.3)
    return save(fig, "chart_03_rent_by_county.png")


def _thin_xticks(ax, keep=6):
    """Show at most `keep` evenly spaced x labels, rotated for readability."""
    ticks = ax.get_xticks()
    labels = [t.get_text() for t in ax.get_xticklabels()]
    n = len(ax.lines[0].get_xdata()) if ax.lines else 0
    if n > keep:
        step = max(1, n // keep)
        xdata = list(ax.lines[0].get_xdata())
        sel = xdata[::step]
        ax.set_xticks(sel)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)


def main():
    print("Rendering exploratory charts ...")
    conn = connect()
    try:
        chart_rppi_by_type(conn)
        chart_rppi_yoy_by_region(conn)
        chart_rent_by_county(conn)
    finally:
        conn.close()
    print(f"Done. Charts in {os.path.relpath(OUT_DIR, ROOT)}/")


if __name__ == "__main__":
    main()
