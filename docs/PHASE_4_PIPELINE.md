# Phase 4 — ELT Pipeline (Bronze → Silver)

## What this phase builds

A dbt-duckdb project that turns the messy Bronze data from Phase 3 into a clean,
tested Silver layer — solving the core problem quantified in the Phase 3 DQ
Findings Report: fan identity is fragmented across systems with no shared key.

## Pipeline

```
generate_synthetic_data.py  ─┐
generate_ticketmaster_       ├─▶  Bronze (raw CSVs loaded as-is into DuckDB)
customers.py                 │
                              ▼
                        dbt run (staging + intermediate models)
                              │
                              ▼
                        dbt test (17 tests)
```

Orchestrated by `dags/nba_pipeline_dag.py` — an Airflow DAG with 4 tasks:
`generate_synthetic_data → load_bronze_layer → dbt_run → dbt_test`, scheduled daily.

## Staging models (Silver layer) — one per Bronze source

| Model | What it fixes |
|---|---|
| `stg_fans` | Collapses the 750 duplicate fan registrations (3.0% of the base) found in Phase 3, using a stable-attribute match (last name + address + signup date), keeping the most complete record |
| `stg_ticketmaster_customers` | Normalizes name/email casing captured at checkout |
| `stg_ticketmaster_transactions` | Drops exact duplicate transactions, flags (doesn't drop) null prices and orphan game references |
| `stg_micros_transactions` | Flags refund/void-like negative amounts instead of letting them silently distort revenue averages |
| `stg_email_engagement` | Normalizes email casing (fixes the 14,817 ALL-CAPS rows from Phase 3) |
| `stg_games`, `stg_season_ticket_accounts`, `stg_nps_surveys` | Light passthrough/normalization |

## The centerpiece: fan identity resolution

`int_fan_identity_map` resolves every Ticketmaster customer record back to a
canonical `fan_id`, using normalized email as the primary match key and
normalized full name as a fallback when email isn't available.

**Result on the full synthetic season:**

| Metric | Value |
|---|---|
| Total Ticketmaster customer records | 25,750 |
| Resolved to a fan_id | 25,750 (100%) |
| — via email match | 23,885 |
| — via name fallback | 1,865 |
| Distinct true fans covered | 24,784 of 25,000 (99.1%) |

The 0.9% gap is real and worth naming honestly: it's rare same-name collisions
(e.g. two different fans both named "James Smith") landing on a fan record
whose email was also missing — the point at which the available match keys run
out. In a real system, a phone number or address match would close most of
this remainder; that's a documented next-iteration improvement, not a hidden gap.

## Data quality tests (17 total, all passing)

`dbt test` enforces: uniqueness and non-null constraints on every primary key,
referential integrity between `season_ticket_accounts.fan_id` and `stg_fans`,
and between the identity map's resolved `fan_id` and `stg_fans`.

## Running it locally

```powershell
cd C:\projects\nba-fan-revenue-engine\dbt_project
$env:DBT_PROFILES_DIR = "."
dbt run
dbt test
```

To run the full orchestrated pipeline via Airflow instead:
```powershell
cd C:\projects\nba-fan-revenue-engine
docker compose up -d airflow
```
Wait ~30 seconds for initialization, then open http://localhost:8080 (login:
`admin` / `admin`), find `nba_fan_engine_daily_pipeline`, and trigger it manually.

## Next: Phase 5 — Star Schema Data Modeling

Silver-layer models above are normalized and source-shaped. Phase 5 builds the
Gold-layer star schema (fact tables for ticket sales, concessions, and
engagement; dimension tables for fans, games, and time) that Phases 6–9 query
directly.
