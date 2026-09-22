"""Stream BACI HS22 into the existing market schema as compact aggregates."""

import argparse
import csv
import sqlite3
import zipfile
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.core.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    archive = args.archive
    cache = archive.with_suffix(".aggregate.sqlite")
    con = sqlite3.connect(cache)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("CREATE TABLE IF NOT EXISTS market (year INTEGER, importer INTEGER, hs TEXT, value REAL, PRIMARY KEY(year, importer, hs)) WITHOUT ROWID")
    con.execute("CREATE TABLE IF NOT EXISTS china (year INTEGER, importer INTEGER, hs TEXT, value REAL, PRIMARY KEY(year, importer, hs)) WITHOUT ROWID")
    with zipfile.ZipFile(archive) as bundle:
        names = [name for name in bundle.namelist() if name.startswith("BACI_HS22_Y")]
        for name in names:
            marker = f"done:{name}"
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='progress'").fetchone() is None:
                con.execute("CREATE TABLE progress (name TEXT PRIMARY KEY)")
            if con.execute("SELECT 1 FROM progress WHERE name=?", (marker,)).fetchone():
                continue
            with bundle.open(name, "r") as raw:
                reader = csv.DictReader(line.decode("utf-8") for line in raw)
                market_rows, china_rows = [], []
                for row in reader:
                    value = float(row["v"] or 0) * 1000
                    if value <= 0:
                        continue
                    market_rows.append((int(row["t"]), int(row["j"]), row["k"].zfill(6), value))
                    if row["i"] == "156":
                        china_rows.append((int(row["t"]), int(row["j"]), row["k"].zfill(6), value))
                    if len(market_rows) >= 20_000:
                        con.executemany("INSERT INTO market VALUES(?,?,?,?) ON CONFLICT(year,importer,hs) DO UPDATE SET value=value+excluded.value", market_rows)
                        con.executemany("INSERT INTO china VALUES(?,?,?,?) ON CONFLICT(year,importer,hs) DO UPDATE SET value=value+excluded.value", china_rows)
                        con.commit(); market_rows.clear(); china_rows.clear()
                con.executemany("INSERT INTO market VALUES(?,?,?,?) ON CONFLICT(year,importer,hs) DO UPDATE SET value=value+excluded.value", market_rows)
                con.executemany("INSERT INTO china VALUES(?,?,?,?) ON CONFLICT(year,importer,hs) DO UPDATE SET value=value+excluded.value", china_rows)
                con.execute("INSERT INTO progress VALUES(?)", (marker,)); con.commit()
    with SessionLocal() as db:
        db.execute(text("INSERT INTO data_sources (code, name, category, provider_type, reliability, enabled, update_frequency, status, terms_notes, created_at, updated_at) SELECT 'BACI', 'CEPII BACI', 'TRADE', 'BaciAggregateImporter', 'A', true, 'ANNUAL', 'READY', 'HS6 reconciled bilateral trade data', now(), now() WHERE NOT EXISTS (SELECT 1 FROM data_sources WHERE code='BACI')"))
        source_id = db.execute(text("SELECT id FROM data_sources WHERE code='BACI'")).scalar_one()
        snapshot_id = db.execute(text("SELECT id FROM source_snapshots WHERE source_identifier='baci:HS22:202601' ORDER BY id DESC LIMIT 1")).scalar()
        if snapshot_id is None:
            snapshot_id = db.execute(text("INSERT INTO source_snapshots (source_id, source_type, source_identifier, request_payload, response_payload, retrieved_at, status, checksum) VALUES (:source_id, 'TRADE', 'baci:HS22:202601', '{}'::jsonb, '{}'::jsonb, now(), 'SUCCESS', 'baci-hs22-202601') RETURNING id"), {"source_id": source_id}).scalar_one()
        codes = {156: "CHN"}
        # Load BACI's country mapping into PostgreSQL-independent Python map.
        with zipfile.ZipFile(archive) as bundle, bundle.open("country_codes_V202601.csv") as raw:
            codes.update({int(row["country_code"]): row["country_iso3"] for row in csv.DictReader(line.decode("utf-8") for line in raw)})
        for table, partner in (("market", "WLD"), ("china", "CHN")):
            rows = []
            for year, importer, hs, value in con.execute(f"SELECT year, importer, hs, value FROM {table}"):
                iso = codes.get(importer)
                if iso:
                    rows.append({"classification":"HS2022","hs_code":hs,"period_year":year,"period_start":date(year,1,1),"period_end":date(year,12,31),"reporter_iso3":iso,"partner_iso3":partner,"flow":"IMPORT","trade_value_usd":value,"source_snapshot_id":snapshot_id})
                if len(rows) >= 5000:
                    _insert(db, rows); rows.clear()
            _insert(db, rows)
        db.execute(text("REFRESH MATERIALIZED VIEW country_trade_yearly")); db.commit()


def _insert(db, rows):
    if rows:
        db.execute(text("""INSERT INTO trade_observations (classification,hs_code,period_year,period_type,period_start,period_end,reporter_iso3,partner_iso3,flow,trade_value_usd,source_snapshot_id,created_at) VALUES (:classification,:hs_code,:period_year,'YEAR',:period_start,:period_end,:reporter_iso3,:partner_iso3,:flow,:trade_value_usd,:source_snapshot_id,now()) ON CONFLICT ON CONSTRAINT uq_trade_observation_period DO NOTHING"""), rows)
        db.commit()


if __name__ == "__main__":
    main()
