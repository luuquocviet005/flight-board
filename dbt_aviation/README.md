# dbt project: `aviation`

Transforms the raw AirLabs data (loaded into PostgreSQL by [`../db_load.py`](../db_load.py)) into clean, tested tables.

```
AirLabs API ──► db_load.py ──► public.airports / public.airlines   (raw, 23,383 / 6,600 rows)
                                     │  source()
                                     ▼
                         staging.stg_airports / stg_airlines        (cleaned, de-duplicated)
                                     │  ref()
                                     ▼
                   marts.airports_by_country / marts.vn_airports    (report tables)
```

## Files and what each one does

### Project configuration

| File | Purpose |
|---|---|
| [dbt_project.yml](dbt_project.yml) | Project settings. Says models live in `models/`, and sets **materialization** per folder: `staging` → `view` (always reflects the raw tables, no storage), `marts` → `table` (precomputed for fast reporting). Also puts each folder in its own schema (`staging`, `marts`). |
| [profiles.yml](profiles.yml) | **Connection** to PostgreSQL (`localhost:5432`, database `aviation`, user `postgres`). The password is read with `env_var('PGPASSWORD')`, so no secret is stored in the file. |
| [macros/generate_schema_name.sql](macros/generate_schema_name.sql) | A **macro** (reusable Jinja function) that overrides dbt's default schema naming, so tables land in `staging` / `marts` instead of `public_staging` / `public_marts`. |
| [dbt.cmd](dbt.cmd) | Helper to run dbt: loads variables from `../.env`, points dbt at this folder's `profiles.yml`, and runs dbt from the project's `.venv`. Usage: `.\dbt.cmd build`. |

### Staging layer: clean the raw data (1 model per raw table)

| File | Purpose |
|---|---|
| [models/staging/_sources.yml](models/staging/_sources.yml) | Declares the **sources**: the raw tables `public.airports` and `public.airlines` written by `db_load.py`. Also holds **tests** for the staging models: `unique` + `not_null` on the IDs, `not_null` on names, and `unique` on `iata_code` with `severity: warn` (report, don't fail). |
| [models/staging/stg_airports.sql](models/staging/stg_airports.sql) | Cleans airports: `trim()` removes stray spaces, `upper()` normalises codes, `nullif(..., '')` turns blanks into `NULL`, and `name` is renamed to `airport_name`. Then `DISTINCT ON (iata_code, icao_code, airport_name)` **removes 92 exact duplicate rows** (e.g. THD Tho Xuan appeared twice). 23,383 → 23,291 rows. |
| [models/staging/stg_airlines.sql](models/staging/stg_airlines.sql) | Same cleaning for airlines (trim, upper-case codes, blanks → NULL, `name` → `airline_name`). No rows removed (6,600 → 6,600). |

### Marts layer: tables for reporting (built on staging with `ref()`)

| File | Purpose |
|---|---|
| [models/marts/airports_by_country.sql](models/marts/airports_by_country.sql) | One row per country: total airports, how many have IATA / ICAO codes, and % with IATA. 243 countries. |
| [models/marts/vn_airports.sql](models/marts/vn_airports.sql) | Commercial airports in Vietnam: `country_code = 'VN'`, has an IATA code **and** an ICAO code. 48 VN rows → 28 airports (SGN, HAN, DAD, CXR, PQC, ...). The ICAO filter drops 4 spam rows (`RKM "KM88 onl"`, `XAG` / `XHG` casino ads with coordinates in the ocean) and 8 small/closed airfields with no ICAO code. |
| [models/marts/_marts.yml](models/marts/_marts.yml) | Descriptions and **tests** for the marts: `country_code` unique + not null, `vn_airports.iata_code` unique + not null. This `unique` test is what first caught the THD duplicate and the XHG spam rows. |

### Generated (not committed)

| Path | Purpose |
|---|---|
| `target/` | Compiled SQL, run results, and the docs site files (`manifest.json`, `catalog.json`). |
| `logs/` | dbt run logs. |

## Commands

```powershell
cd dbt_aviation
.\dbt.cmd build                          # run all models + all tests (16 nodes)
.\dbt.cmd show --select vn_airports      # preview a model's rows
.\dbt.cmd docs generate                  # build the documentation site
.\dbt.cmd docs serve --port 8580         # open docs + lineage graph at http://127.0.0.1:8580
```

Latest `dbt build`: **PASS=15, WARN=1, ERROR=0**. The warning is intentional: 222 IATA codes are shared by more than one airport worldwide, which is a property of the data, not a bug.
