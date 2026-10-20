"""Fetch Airports and Airlines from AirLabs and store them in PostgreSQL.

Run (PowerShell):
    $env:AIRLABS_KEY="..."; $env:PGPASSWORD="<postgres password>"; python db_load.py

Then open pgAdmin 4 -> Servers -> PostgreSQL 17 -> Databases -> aviation -> Schemas -> public -> Tables.
"""
import os

import psycopg

from flights import get  # same HTTP helper as the flight board

DB = "aviation"
CONN = "host=localhost port=5432 user=postgres dbname={}"  # password comes from PGPASSWORD

SCHEMA = """
CREATE TABLE IF NOT EXISTS airports (
    airport_id   SERIAL PRIMARY KEY,
    iata_code    CHAR(3),
    icao_code    CHAR(4),
    name         TEXT NOT NULL,
    country_code CHAR(2),
    latitude     NUMERIC(9,6),
    longitude    NUMERIC(9,6)
);
CREATE TABLE IF NOT EXISTS airlines (
    airline_id SERIAL PRIMARY KEY,
    iata_code  VARCHAR(3),
    icao_code  VARCHAR(4),
    name       TEXT NOT NULL
);
"""


def connect():
    with psycopg.connect(CONN.format("postgres"), autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB,)).fetchone():
            c.execute(f"CREATE DATABASE {DB}")
    conn = psycopg.connect(CONN.format(DB))
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def load(conn, airports, airlines):
    # ponytail: full reload each run (truncate + insert in one transaction). Codes in AirLabs
    # aren't unique (IATA airline codes get reused), so there is no safe natural key to upsert on.
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("TRUNCATE airports, airlines RESTART IDENTITY")
        with cur.copy("COPY airports (iata_code, icao_code, name, country_code, latitude, longitude) FROM STDIN") as cp:
            for a in airports:
                if a.get("name"):
                    cp.write_row((a.get("iata_code"), a.get("icao_code"), a["name"], a.get("country_code"), a.get("lat"), a.get("lng")))
        with cur.copy("COPY airlines (iata_code, icao_code, name) FROM STDIN") as cp:
            for a in airlines:
                if a.get("name"):
                    cp.write_row((a.get("iata_code"), a.get("icao_code"), a["name"]))


def fetch(endpoint, key):
    r = get(f"https://airlabs.co/api/v9/{endpoint}?api_key={key}")
    if "error" in r:
        raise SystemExit(f"AirLabs {endpoint}: {r['error'].get('message', r['error'])}")
    return r["response"]


def main():
    key = os.environ.get("AIRLABS_KEY") or exit("Set AIRLABS_KEY first")
    os.environ.get("PGPASSWORD") or exit("Set PGPASSWORD (the postgres password you chose at install)")
    airports, airlines = fetch("airports", key), fetch("airlines", key)  # 2 API calls total
    with connect() as conn:
        load(conn, airports, airlines)
        for t in ("airports", "airlines"):
            print(t, conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], "rows")


if __name__ == "__main__":
    main()
