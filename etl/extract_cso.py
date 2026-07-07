#!/usr/bin/env python3
"""
extract_cso.py
--------------
Extract Irish housing affordability data from the CSO PxStat open-data API
and the RTB/ESRI Rent Index, then write tidy (long-format) CSVs ready for
loading into SQL and Power BI.

Datasets:
  * HPM09 - Residential Property Price Index (RPPI), monthly, by region &
            property type (base 2015 = 100).  Source: Central Statistics Office.
  * RIQ02 - RTB Average Monthly Rent Report, quarterly, standardised average
            rent by location, property type & number of bedrooms.

Why JSON-stat and not CSV?
  The CSO CSV endpoint works for HPM09 but returns an empty body for the RTB
  rent matrices, so we read the JSON-stat 2.0 representation for everything and
  parse it with a single generic function. JSON-stat stores one flat `value`
  array whose position is decoded against the size of each dimension.

Usage:
  python etl/extract_cso.py                # pull both datasets -> data/processed/
  python etl/extract_cso.py --only rppi    # just the price index
  python etl/extract_cso.py --only rents   # just the rents

Notes:
  Run this on a normal internet connection. The API has no key. Full pulls are
  a few MB. Output files are written to data/processed/.
"""

from __future__ import annotations
import argparse
import csv
import itertools
import json
import os
import sys
import urllib.request

API = ("https://ws.cso.ie/public/api.restful/"
       "PxStat.Data.Cube_API.ReadDataset/{matrix}/JSON-stat/2.0/en")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "processed")

# Locations in RIQ02 that correspond to whole counties (+ the national total).
# The raw matrix also contains ~420 sub-county areas which we drop here so the
# rent fact table lines up with the county grain used on the price side.
COUNTIES = {
    "State", "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin",
    "Galway", "Kerry", "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick",
    "Longford", "Louth", "Mayo", "Meath", "Monaghan", "Offaly", "Roscommon",
    "Sligo", "Tipperary", "Waterford", "Westmeath", "Wexford", "Wicklow",
}


def fetch_jsonstat(matrix: str) -> dict:
    """GET a PxStat matrix in JSON-stat 2.0 format."""
    url = API.format(matrix=matrix)
    req = urllib.request.Request(url, headers={"User-Agent": "affordability-etl/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def jsonstat_to_rows(ds: dict):
    """Yield one dict per cell of a JSON-stat 2.0 dataset.

    Decodes the flat `value` array into labelled rows using each dimension's
    category index/label maps. Missing cells (None) are skipped.
    """
    dim_ids = ds["id"]
    sizes = ds["size"]
    values = ds["value"]

    # Build an ordered list of (dimension label, [category labels in index order])
    axes = []
    for dim_id in dim_ids:
        dim = ds["dimension"][dim_id]
        dim_label = dim.get("label", dim_id)
        cats = dim["category"]
        index = cats["index"]
        labels = cats.get("label", {})
        # index may be a dict {code: pos} or a list [code, ...]
        if isinstance(index, dict):
            ordered = sorted(index, key=index.get)
        else:
            ordered = list(index)
        axis = [(labels.get(code, code)) for code in ordered]
        axes.append((dim_label, axis))

    # Cartesian product of category positions matches the value array order.
    for flat_pos, combo in enumerate(itertools.product(*[a for _, a in axes])):
        v = values[flat_pos] if flat_pos < len(values) else None
        # JSON-stat may store value as list or dict; handle the common list form
        if isinstance(values, dict):
            v = values.get(str(flat_pos))
        if v is None or v == "":
            continue
        row = {label: combo[i] for i, (label, _) in enumerate(axes)}
        row["VALUE"] = v
        yield row


def extract_rppi() -> str:
    """Write tidy monthly RPPI to data/processed/rppi_monthly.csv."""
    ds = fetch_jsonstat("HPM09")
    path = os.path.join(OUT, "rppi_monthly.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["period", "geography_property", "rppi_index_2015base"])
        n = 0
        for r in jsonstat_to_rows(ds):
            period = r.get("Month") or r.get("Quarter")
            geo = r.get("Type of Residential Property")
            w.writerow([period, geo, r["VALUE"]])
            n += 1
    print(f"[rppi]  wrote {n:,} rows -> {os.path.relpath(path)}")
    return path


def extract_rents() -> str:
    """Write tidy quarterly county rents to data/processed/rents_quarterly.csv."""
    ds = fetch_jsonstat("RIQ02")
    path = os.path.join(OUT, "rents_quarterly.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quarter", "location", "property_type", "bedrooms",
                    "standardised_avg_monthly_rent_eur"])
        n = 0
        for r in jsonstat_to_rows(ds):
            loc = r.get("Location", "")
            if loc not in COUNTIES:      # keep county + national grain only
                continue
            w.writerow([r.get("Quarter"), loc, r.get("Property Type"),
                        r.get("Number of Bedrooms"), r["VALUE"]])
            n += 1
    print(f"[rents] wrote {n:,} rows -> {os.path.relpath(path)}")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract CSO/RTB housing data.")
    ap.add_argument("--only", choices=["rppi", "rents"], help="extract just one dataset")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    try:
        if args.only in (None, "rppi"):
            extract_rppi()
        if args.only in (None, "rents"):
            extract_rents()
    except urllib.error.URLError as e:
        print(f"Network error reaching the CSO API: {e}", file=sys.stderr)
        print("Run this from a machine with normal internet access.", file=sys.stderr)
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
